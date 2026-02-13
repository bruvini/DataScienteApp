import streamlit as st
import pandas as pd
from src.pages import (home, ocupacao_geral, ocupacao_uti, mortalidade, 
                      permanencia_cirurgica, permanencia_clinica, permanencia_ps)

st.set_page_config(page_title="Data Science Hospitalar", layout="wide")

# Inicialização do session_state para o dataframe
if 'df' not in st.session_state:
    st.session_state.df = None

# --- SIDEBAR NAVEGAÇÃO ---
st.sidebar.title("🏥 Hospital Analytics")
page = st.sidebar.radio(
    "Selecione o Indicador:",
    ["Página Inicial", "Taxa de Ocupação Hospitalar", "Taxa de Ocupação da UTI", 
     "Taxa de Mortalidade", "Tempo de Permanência em leitos Cirurgicos", 
     "Tempo de Permanência em leitos de Clínica Médica", "Tempo de Permanência no Pronto Socorro"]
)

# --- LÓGICA DE ROTEAMENTO ---
if page == "Página Inicial":
    home.show()
else:
    if st.session_state.df is not None:
        if page == "Taxa de Ocupação Hospitalar":
            ocupacao_geral.show()
        elif page == "Taxa de Ocupação da UTI":
            ocupacao_uti.show()
        elif page == "Taxa de Mortalidade":
            mortalidade.show()
        elif page == "Tempo de Permanência em leitos Cirurgicos":
            permanencia_cirurgica.show()
        elif page == "Tempo de Permanência em leitos de Clínica Médica":
            permanencia_clinica.show()
        elif page == "Tempo de Permanência no Pronto Socorro":
            permanencia_ps.show()
    else:
        st.warning("⚠️ Por favor, faça o upload do arquivo CSV na Página Inicial para prosseguir.")