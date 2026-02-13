import streamlit as st

def filtrar_dados(df):
    """
    Cria a interface de filtros na sidebar ou no topo da página
    e retorna o dataframe filtrado.
    """
    st.sidebar.subheader("Filtros Globais")
    
    # Filtro de Data
    min_date = df['Data'].min().to_pydatetime()
    max_date = df['Data'].max().to_pydatetime()
    
    data_range = st.sidebar.date_input(
        "Período",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Filtro de Origem/Setor
    origens = df['Origem'].unique().tolist()
    selecao_origem = st.sidebar.multiselect("Origem/Tipo de Setor", origens, default=origens)
    
    # Aplicação dos filtros
    mask = (df['Origem'].isin(selecao_origem))
    
    if len(data_range) == 2:
        mask &= (df['Data'] >= pd.Timestamp(data_range[0])) & (df['Data'] <= pd.Timestamp(data_range[1]))
    
    return df[mask]