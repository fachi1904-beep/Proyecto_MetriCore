import streamlit as st
from utils import aplicar_estilos
aplicar_estilos()

st.set_page_config(page_title="Calculadora Rápida — MetriCore", layout="wide")
st.title("⚡ Calculadora rápida (Regla de Decisión)")

if "premium_activo" not in st.session_state or not st.session_state.premium_activo:
    with st.container(border=True):
        st.warning("🔒 Este módulo requiere el Plan Premium.")
        st.caption("Ve a **Acceso a Plan Premium** en el menú lateral para activarlo.")
else:
    with st.container(border=True):
        st.info("🚧 Módulo en construcción. Próximamente disponible.")