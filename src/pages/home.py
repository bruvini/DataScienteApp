import streamlit as st
import pandas as pd

def show():
    # Banner e Títulos
    st.title("📊 Data Science Hospitalar")
    st.subheader("Transformando indicadores de saúde em eficiência operacional.")
    
    st.markdown("---")
    
    st.info("💡 **Dica:** O arquivo deve conter colunas de movimentação (Internações, Altas, Óbitos) por Setor.")
    
    uploaded_file = st.file_uploader("Upload do arquivo CSV de movimentação setorial", type=["csv"])
    
    if uploaded_file is not None:
        try:
            # Lendo com separador de vírgula conforme sua amostra
            df = pd.read_csv(uploaded_file, sep=',')
            
            # Conversão da coluna Data (ajuste o formato se necessário)
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
            
            # Armazenando no session_state
            st.session_state.df = df
            
            st.success(f"Sucesso! {len(df)} registros carregados.")
            st.write("### Prévia dos Dados")
            st.dataframe(df.head(), use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")