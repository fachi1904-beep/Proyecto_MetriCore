import streamlit as st

def aplicar_estilos():
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #0b2c40 !important;
    }
    [data-testid="stSidebar"] * {
        color: #E0F0ED !important;
    }
    [data-testid="stSidebarNav"] a {
        border-radius: 8px;
        padding: 6px 12px;
        margin: 2px 0;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: #0a453c !important;
    }
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #238d93 !important;
    }
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #2dc197;
        border-left: 5px solid #1469aa;
        border-radius: 8px;
        padding: 16px 20px;
    }
    [data-testid="stMetricLabel"] {
        color: #0a453c !important;
        font-size: 18px !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricValue"] {
        color: #0b2c40 !important;
        font-size: 36px !important;
        font-weight: 700 !important;
    }
    [data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #2dc197 !important;
    }
    [data-testid="stDataFrame"] iframe {
        background-color: #FFFFFF !important;
    }
    .stDataFrame {
        background-color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)