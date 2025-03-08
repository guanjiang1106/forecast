import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import pyodbc
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置页面配置
st.set_page_config(
    page_title="预测性维护系统",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS样式，采用Vue风格的设计
st.markdown("""
<style>
    /* 全局样式 */
    .main {
        padding: 2rem;
        background-color: #f8f9fa;
    }
    
    /* 标题样式 */
    h1 {
        color: #2c3e50;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 600;
        text-align: center;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 3px solid #42b883;
    }
    
    /* 按钮样式 */
    .stButton>button {
        background-color: #42b883 !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        border: none !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 4px rgba(66, 184, 131, 0.2) !important;
    }
    
    .stButton>button:hover {
        background-color: #3aa876 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(66, 184, 131, 0.3) !important;
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* 卡片样式 */
    div[data-testid="stMetric"] {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
    }
    
    /* 图表容器样式 */
    div[data-testid="stPlotlyChart"] {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
        margin-top: 1rem;
    }
    
    /* 数据表格样式 */
    div[data-testid="stDataFrame"] {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* 子标题样式 */
    h2, h3 {
        color: #2c3e50;
        font-family: 'Helvetica Neue', sans-serif;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    /* 状态指示器样式 */
    .status-indicator {
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 500;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 数据库连接函数
def get_db_connection():
    import sqlite3
    return sqlite3.connect('device_data.db')

# 生成随机数据
def generate_random_data():
    end_date = datetime(2025, 3, 7)
    timestamps = [end_date - timedelta(hours=i) for i in range(1000)]
    
    temperatures = [max(20, min(80, np.random.normal(50, 10))) for _ in range(1000)]
    vibrations = [max(0.1, min(5.0, np.random.normal(2.0, 0.5))) for _ in range(1000)]
    pressures = [max(50, min(150, np.random.normal(100, 20))) for _ in range(1000)]
    running_hours = list(range(1000))
    
    return pd.DataFrame({
        '时间戳': timestamps,
        '温度': temperatures,
        '振动': vibrations,
        '压力': pressures,
        '运行小时数': running_hours
    })

# 计算剩余使用寿命（RUL）
def calculate_rul(row):
    total_life = 10000
    temp_anomaly = max(0, row['温度'] - 60)
    vib_anomaly = max(0, row['振动'] - 3.0)
    press_anomaly = max(0, row['压力'] - 120)
    
    health_decay = 0.3 * temp_anomaly + 0.4 * vib_anomaly + 0.3 * press_anomaly
    rul = total_life - row['运行小时数'] - health_decay
    return max(0, rul * random.uniform(0.95, 1.05))

# 获取维护建议
def get_maintenance_advice(rul):
    if rul < 1000:
        return "⚠️ 紧急：需要立即进行维护！", "#dc3545"
    elif rul < 3000:
        return "⚡ 警告：需要在近期安排维护。", "#ffc107"
    else:
        return "✅ 正常：继续监测设备状态。", "#28a745"

# 主界面
st.title('预测性维护系统')

# 创建固定在顶部的按钮区域
with st.container():
    st.markdown('''
    <div style="position: sticky; top: 0; z-index: 999; background: #f8f9fa; padding: 1rem 0; margin-bottom: 2rem;">
    ''', unsafe_allow_html=True)
    
    buttons_col1, buttons_col2 = st.columns(2)
    with buttons_col1:
        generate_button = st.button('生成随机数据', use_container_width=True, key='generate')
    with buttons_col2:
        predict_button = st.button('开始预测', use_container_width=True, key='predict')

# 创建主要内容区域的响应式布局
col1, col2 = st.columns([1, 1])

# 获取或生成数据
def get_or_generate_data():
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM 设备数据", conn)
        conn.close()
        return df
    except:
        return None

# 显示数据表格
def display_data_table(df):
    if df is not None and not df.empty:
        with col1:
            st.subheader('📊 数据概览')
            st.dataframe(
                df.style
                .background_gradient(cmap='YlOrRd', subset=['温度', '振动', '压力'])
                .format({
                    '温度': '{:.1f}°C',
                    '振动': '{:.2f} mm/s',
                    '压力': '{:.1f} kPa',
                    '运行小时数': '{:,.0f}'
                }),
                use_container_width=True,
                height=400
            )

# 处理数据生成
if generate_button:
    with st.spinner('正在生成数据...'):
        try:
            df = generate_random_data()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS 设备数据 (
                时间戳 TIMESTAMP NOT NULL,
                温度 REAL NOT NULL,
                振动 REAL NOT NULL,
                压力 REAL NOT NULL,
                运行小时数 INTEGER NOT NULL
            )
            """)
            
            cursor.execute("DELETE FROM 设备数据")
            
            df.to_sql('设备数据', conn, if_exists='append', index=False)
            
            conn.commit()
            conn.close()
            
            st.success('✨ 数据生成成功！')
                
        except Exception as e:
            st.error(f'❌ 数据生成失败：{str(e)}')

# 获取当前数据并显示
df = get_or_generate_data()
display_data_table(df)

# 处理预测
if predict_button:
    with st.spinner('正在进行预测分析...'):
        try:
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT * FROM 设备数据", conn)
            conn.close()
            
            if len(df) == 0:
                st.error('❌ 没有可用的数据，请先生成随机数据！')
            else:
                df['RUL'] = df.apply(calculate_rul, axis=1)
                latest_data = df.iloc[-1]
                # 确保时间戳是datetime类型
                if isinstance(latest_data['时间戳'], str):
                    latest_timestamp = pd.to_datetime(latest_data['时间戳'])
                else:
                    latest_timestamp = latest_data['时间戳']
                expiry_date = latest_timestamp + timedelta(hours=int(latest_data['RUL']))
                advice, color = get_maintenance_advice(latest_data['RUL'])
                
                with col2:
                    # 当前状态卡片
                    st.subheader('📊 当前设备状态')
                    status_cols = st.columns(4)
                    metrics = [
                        ("温度", f"{latest_data['温度']:.1f}°C", "🌡️"),
                        ("振动", f"{latest_data['振动']:.2f} mm/s", "📳"),
                        ("压力", f"{latest_data['压力']:.1f} kPa", "⚖️"),
                        ("运行时间", str(latest_data['运行小时数']) + " 小时", "⏱️")
                    ]
                    
                    for col, (label, value, icon) in zip(status_cols, metrics):
                        with col:
                            st.metric(f"{icon} {label}", value)
                    
                    # 预测结果卡片
                    st.subheader('🔮 预测结果')
                    st.markdown(f"""
                    <div style="background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,0.1);">
                        <p style='color: {color}; font-size: 24px; margin-bottom: 1rem;'>
                            <strong>剩余使用寿命：</strong> {str(int(latest_data['RUL']))} 小时
                        </p>
                        <p style='font-size: 18px; margin-bottom: 1rem;'>
                            <strong>预计到期日期：</strong> {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                        <div class='status-indicator' style='background-color: {color}20; color: {color};'>
                            <strong>维护建议：</strong> {advice}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 异常值分析
                    st.subheader('🚨 异常值分析')
                    anomaly_cols = st.columns(3)
                    anomalies = [
                        ("温度异常", max(0, latest_data['温度'] - 60), "°C"),
                        ("振动异常", max(0, latest_data['振动'] - 3.0), "mm/s"),
                        ("压力异常", max(0, latest_data['压力'] - 120), "kPa")
                    ]
                    
                    for col, (label, value, unit) in zip(anomaly_cols, anomalies):
                        with col:
                            st.metric(label, f"{value:.2f} {unit}",
                                     delta_color="inverse")
                    
                    # 参数趋势图
                    st.subheader('📈 参数趋势图')
                    fig = go.Figure()
                    
                    parameters = [
                        ('温度', '温度', '#ff7f0e', 60),
                        ('振动', '振动', '#2ca02c', 3.0),
                        ('压力', '压力', '#9467bd', 120)
                    ]
                    
                    for param, name, color, threshold in parameters:
                        fig.add_trace(go.Scatter(
                            x=df['时间戳'],
                            y=df[param],
                            name=name,
                            line=dict(color=color, width=2)
                        ))
                        fig.add_hline(
                            y=threshold,
                            line_dash="dash",
                            line_color="rgba(255,0,0,0.5)",
                            annotation_text=f"{name}阈值 ({threshold})"
                        )
                    
                    fig.update_layout(
                        title='设备参数趋势',
                        xaxis_title='时间',
                        yaxis_title='参数值',
                        height=400,
                        template='plotly_white',
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # RUL趋势图
                    st.subheader('⏳ RUL趋势图')
                    fig_rul = go.Figure()
                    
                    fig_rul.add_trace(go.Scatter(
                        x=df['运行小时数'],
                        y=df['RUL'],
                        mode='lines+markers',
                        name='RUL趋势',
                        line=dict(color='#1f77b4', width=2)
                    ))
                    
                    fig_rul.add_hline(
                        y=1000,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="紧急维护阈值"
                    )
                    
                    fig_rul.add_hline(
                        y=3000,
                        line_dash="dash",
                        line_color="orange",
                        annotation_text="警告阈值"
                    )
                    
                    fig_rul.update_layout(
                        title='剩余使用寿命趋势',
                        xaxis_title='运行小时数',
                        yaxis_title='剩余使用寿命（小时）',
                        height=400,
                        template='plotly_white',
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_rul, use_container_width=True)
                    
        except Exception as e:
            st.error(f'❌ 预测分析失败：{str(e)}')