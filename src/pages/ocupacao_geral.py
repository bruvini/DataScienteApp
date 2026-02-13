import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import calendar
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Modelos de ML
from prophet import Prophet

def render_analise_descritiva(df_filtrado, df_anterior, df_internacao_completo, mes_aberto):
    """
    Organiza os gráficos com explicações de Data Literacy e layout adaptável.
    """
    st.write("Analise o comportamento histórico. Se o mês estiver em aberto, o sistema incluirá a tendência para os próximos 7 dias.")
    
    # --- GRÁFICO 1: EVOLUÇÃO + PREVISÃO ---
    with st.container(border=True):
        st.subheader("Evolução e Tendência da Ocupação", 
                     help="""**O QUE ESTE GRÁFICO MOSTRA?**
Acompanha a utilização dos leitos ao longo do mês. 

**COMO ANALISAR?**
1. **Pontos Azuis:** Representam a ocupação real de cada dia. 
2. **Linha Tracejada Cinza:** É o espelho do mesmo mês no ano anterior.
3. **Linha Pontilhada Roxa (IA):** Nossa inteligência artificial prevê os próximos 7 dias baseado no ritmo atual.

**CORRELAÇÃO:**
Se a linha estiver subindo e o gráfico de 'Balanço de Movimentação' mostrar mais Entradas do que Saídas, o hospital atingirá o limite crítico em breve.

**AÇÃO SUGERIDA:**
Se a tendência apontar para cima de 98%, acione o NIR para acelerar altas administrativas e otimizar fluxos clínicos.""")
        
        df_diario = df_filtrado.groupby('Data').agg({'Paciente/Dia': 'sum', 'Leitos-dia': 'sum'}).reset_index()
        df_diario['Taxa %'] = (df_diario['Paciente/Dia'] / df_diario['Leitos-dia'] * 100)
        
        df_ant_diario = df_anterior.groupby('Data').agg({'Paciente/Dia': 'sum', 'Leitos-dia': 'sum'}).reset_index()
        if not df_ant_diario.empty:
            df_ant_diario['Taxa % Ant'] = (df_ant_diario['Paciente/Dia'] / df_ant_diario['Leitos-dia'] * 100)
            df_ant_diario['Data_Comp'] = df_ant_diario['Data'].apply(lambda x: x.replace(year=df_diario['Data'].dt.year.iloc[0]))

        fig = go.Figure()

        if mes_aberto:
            try:
                df_train = df_internacao_completo.groupby('Data').agg({'Paciente/Dia': 'sum', 'Leitos-dia': 'sum'}).reset_index()
                df_train['y'] = (df_train['Paciente/Dia'] / df_train['Leitos-dia'] * 100)
                df_train = df_train.rename(columns={'Data': 'ds'})[['ds', 'y']]
                df_train['ds'] = df_train['ds'].dt.tz_localize(None)

                m = Prophet(yearly_seasonality=True, daily_seasonality=False, interval_width=0.8)
                m.fit(df_train)
                future = m.make_future_dataframe(periods=7)
                forecast = m.predict(future)
                df_pred = forecast[forecast['ds'] > df_train['ds'].max()]

                fig.add_trace(go.Scatter(x=pd.concat([df_pred['ds'], df_pred['ds'][::-1]]),
                                         y=pd.concat([df_pred['yhat_upper'], df_pred['yhat_lower'][::-1]]),
                                         fill='toself', fillcolor='rgba(148, 103, 189, 0.2)',
                                         line_color='rgba(255,255,255,0)', name='Incerteza AI', showlegend=False))
                
                fig.add_trace(go.Scatter(x=df_pred['ds'], y=df_pred['yhat'],
                                         name='Tendência (IA)', line=dict(color='#9467bd', width=3, dash='dot')))
            except:
                st.warning("Dados insuficientes para gerar previsão AI.")

        if not df_ant_diario.empty:
            fig.add_trace(go.Scatter(x=df_ant_diario['Data_Comp'], y=df_ant_diario['Taxa % Ant'],
                                     name='Ano Anterior', line=dict(color='gray', dash='dash'), opacity=0.4))

        fig.add_trace(go.Scatter(x=df_diario['Data'], y=df_diario['Taxa %'],
                                 name='Ocupação Atual', mode='lines+markers', line=dict(color='#1f77b4', width=3)))
        
        fig.add_hline(y=98, line_dash="solid", line_color="red", annotation_text="98%")
        fig.add_hline(y=85, line_dash="dash", line_color="orange", annotation_text="85%")

        fig.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_xaxes(tickformat="%d/%m", tickangle=0)
        st.plotly_chart(fig, use_container_width=True)

    # --- LÓGICA DE LAYOUT DINÂMICO PARA OS GRÁFICOS INFERIORES ---
    # Pegamos os setores selecionados do session_state ou via parâmetro (ajuste conforme sua chamada)
    # Aqui vamos usar o dataframe filtrado para contar os setores únicos
    qtd_setores = df_filtrado['Setor'].nunique()

    if qtd_setores > 1:
        col_graf1, col_graf2 = st.columns(2)
    else:
        col_graf1, col_graf2 = st.empty(), st.container() # Ocupa a tela toda

    # Gráfico Carga por Unidade (Só aparece se > 1 setor)
    if qtd_setores > 1:
        with col_graf1:
            with st.container(border=True):
                st.subheader("Carga por Unidade", 
                             help="""**O QUE ESTE GRÁFICO MOSTRA?** A proporção de ocupação entre os setores selecionados.""")
                fig_tree = px.treemap(df_filtrado, path=['Setor'], values='Paciente/Dia', color_discrete_sequence=px.colors.qualitative.Safe)
                fig_tree.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_tree, use_container_width=True)

    # Gráfico Balanço de Movimentação (Sempre aparece)
    with col_graf2:
        with st.container(border=True):
            st.subheader("Balanço de Movimentação", 
                         help="""**O QUE ESTE GRÁFICO MOSTRA?** O fluxo de 'Entradas' (Internações) e 'Saídas' (Altas/Óbitos).""")
            
            # Garantindo a soma correta da coluna 'Intern.'
            df_mov = df_filtrado.groupby('Data').agg({
                'Intern.': 'sum', 
                'Saídas': 'sum',
                'Paciente/Dia': 'sum',
                'Leitos-dia': 'sum'
            }).reset_index()
            df_mov['Taxa %'] = (df_mov['Paciente/Dia'] / df_mov['Leitos-dia'] * 100)
            
            fig_mov = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Barras de Entradas (Internações)
            fig_mov.add_trace(go.Bar(
                x=df_mov['Data'], 
                y=df_mov['Intern.'], 
                name='Entradas (Internações)', 
                marker_color='#2ca02c'
            ), secondary_y=False)
            
            # Barras de Saídas
            fig_mov.add_trace(go.Bar(
                x=df_mov['Data'], 
                y=df_mov['Saídas'], 
                name='Saídas (Altas/Óbitos)', 
                marker_color='#d62728'
            ), secondary_y=False)
            
            # Linha de Taxa
            fig_mov.add_trace(go.Scatter(
                x=df_mov['Data'], 
                y=df_mov['Taxa %'], 
                name='Taxa Ocupação (%)',
                line=dict(color='#FFD700', width=4), 
                mode='lines+markers'
            ), secondary_y=True)
            
            fig_mov.update_layout(barmode='group', margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"))
            fig_mov.update_yaxes(title_text="Volume de Pacientes", secondary_y=False)
            fig_mov.update_yaxes(title_text="Taxa %", secondary_y=True, range=[0, 110])
            st.plotly_chart(fig_mov, use_container_width=True)

    # --- GRÁFICO 4: VARIABILIDADE ---
    with st.container(border=True):
        st.subheader("Variabilidade por Dia da Semana", 
                     help="""**O QUE ESTE GRÁFICO MOSTRA?** A oscilação de volume de pacientes por dia da semana.""")
        dias_pt = {'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira', 
                   'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
        df_filtrado['Dia Semana'] = df_filtrado['Data'].dt.day_name().map(dias_pt)
        ordem_pt = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        
        fig_box = px.box(df_filtrado, x='Dia Semana', y='Paciente/Dia', 
                         category_orders={'Dia Semana': ordem_pt}, color_discrete_sequence=['#1f77b4'])
        fig_box.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_box, use_container_width=True)

def render_analise_prescritiva(df_atual):
    """Implementa o Simulador Dinâmico e Conceitos Prescritivos."""
    st.write("A análise prescritiva utiliza IA e simulações para recomendar ações que otimizam a gestão de leitos e recursos.")
    
    # --- SIMULADOR DINÂMICO ---
    st.subheader("🛠️ Simulador de Impacto na Ocupação Hospitalar", 
                help="""**COMO FUNCIONA O CÁLCULO?**
                    Este simulador utiliza uma regra de três dinâmica baseada nos dados atuais:
                    1. **Base:** O sistema soma o total de 'Altas' do período filtrado.
                    2. **Incremento:** O slider aplica a porcentagem escolhida sobre esse volume de altas.
                    3. **Redução de Carga:** O número de 'Novas Altas' é subtraído do total de 'Paciente-Dia'.
                    4. **Resultado:** A nova Taxa de Ocupação é recalculada dividindo esse novo volume de Paciente-Dia pelo total de Leitos-Dia disponíveis no período.
                    \n**POR QUE USAR?** Permite que o NIR visualize matematicamente quanto esforço de desospitalização é necessário para trazer o hospital de volta para a meta de segurança (abaixo de 98%).""")
    
    with st.container(border=True):
        st.write("Simule o impacto de um aumento na eficiência de altas sobre a ocupação atual.")
        
        perc_aumento = st.slider("Aumento no volume de altas diárias (%)", 0, 50, 10, step=5)
        
        # Cálculos do Simulador
        altas_atuais = df_atual['Altas'].sum()
        novas_altas = int(altas_atuais * (1 + perc_aumento/100))
        diferenca_altas = novas_altas - altas_atuais
        
        # Nova Ocupação Estimada
        novos_pacientes_dia = df_atual['Paciente/Dia'].sum() - diferenca_altas
        nova_taxa = (novos_pacientes_dia / df_atual['Leitos-dia'].sum()) * 100
        taxa_atual = (df_atual['Paciente/Dia'].sum() / df_atual['Leitos-dia'].sum()) * 100
        
        col_sim1, col_sim2, col_sim3 = st.columns(3)
        col_sim1.metric("Novas Altas Estimadas", f"{novas_altas} pac.", f"+{diferenca_altas}")
        col_sim2.metric("Ocupação Simulada", f"{nova_taxa:.1f}%", f"{nova_taxa - taxa_atual:.1f}%", delta_color="inverse")
        col_sim3.write(f"**Insight:** Aumentar as altas em {perc_aumento}% liberaria espaço para aproximadamente {diferenca_altas} novas internações no período.")

    # --- CONCEITOS E APLICAÇÕES ---
    st.markdown("---")
    col_presc1, col_presc2 = st.columns(2)
    
    with col_presc1:
        st.markdown("""
        #### 🚀 Aplicações Práticas
        - **Otimização de Alta:** Identifica pacientes com alta probabilidade de liberação para focar esforços clínicos.
        - **Gestão de Gargalos:** Sugere adiamento de eletivas ou abertura de alas preventivamente ao prever picos críticos.
        - **Logística:** Instrui a equipe de higienização sobre leitos prioritários para novos pacientes.
        - **Staffing:** Prescreve o número ideal de profissionais com base na complexidade (paciente-dia).
        """)

    with col_presc2:
        st.markdown("""
        #### 💎 Benefícios Diretos
        - **Redução de Espera:** Diminui o tempo no PS ao liberar leitos com antecedência.
        - **Gestão Proativa:** Muda o modelo de 'apagar incêndios' para planejamento estratégico.
        - **Eficiência Financeira:** Otimiza custos de leitos e pessoal, evitando sobrecarga.
        - **Qualidade do Cuidado:** Reduz riscos de infecção e superlotação em corredores.
        """)

    st.info("💡 **O Papel do NIR:** A análise prescritiva fornece dados automatizados para que o NIR gerencie a trajetória do paciente com precisão e rapidez.")

def show():
    st.title("🏥 Taxa de Ocupação Hospitalar")
    if 'df' not in st.session_state or st.session_state.df is None:
        st.error("Por favor, carregue os dados na Página Inicial.")
        return
    
    df = st.session_state.df
    df_internacao = df[df['Origem'] == 'Internação'].copy()
    
    with st.sidebar:
        st.header("⚙️ Filtros")
        anos = sorted(df_internacao['Data'].dt.year.unique(), reverse=True)
        ano_sel = st.selectbox("Ano de Análise", anos)
        meses_disp = sorted(df_internacao[df_internacao['Data'].dt.year == ano_sel]['Data'].dt.month.unique())
        meses_nomes_pt = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
        mes_sel = st.selectbox("Mês de Análise", meses_disp, format_func=lambda x: meses_nomes_pt[x])
        setores_disp = sorted(df_internacao[df_internacao['Data'].dt.year == ano_sel]['Setor'].unique())
        setores_sel = st.multiselect("Setores", setores_disp, default=setores_disp)

    hoje = date.today()
    is_mes_aberto = (hoje.year == ano_sel and hoje.month == mes_sel)
    df_atual = df_internacao[(df_internacao['Data'].dt.year == ano_sel) & (df_internacao['Data'].dt.month == mes_sel) & (df_internacao['Setor'].isin(setores_sel))]
    df_anterior = df_internacao[(df_internacao['Data'].dt.year == ano_sel - 1) & (df_internacao['Data'].dt.month == mes_sel) & (df_internacao['Setor'].isin(setores_sel))]

    if df_atual.empty:
        st.warning("Não há dados para os filtros selecionados.")
        return

    # --- CÁLCULOS DOS KPIs E PROJEÇÃO AI ---
    def calc_metrics(data):
        if data.empty: return 0, 0, 0
        p, l, s = data['Paciente/Dia'].sum(), data['Leitos-dia'].sum(), data['Saídas'].sum()
        taxa = (p/l*100 if l>0 else 0)
        perm = (p/s if s>0 else 0)
        giro = (s/data['Leitos Ativos'].mean() if data['Leitos Ativos'].mean()>0 else 0)
        return taxa, perm, giro

    t_at, p_at, g_at = calc_metrics(df_atual)
    t_an, p_an, g_an = calc_metrics(df_anterior)

    # Lógica de Projeção Final Real com ML (Prophet)
    proj_fechamento = t_at
    if is_mes_aberto:
        try:
            # Treina com o histórico completo para entender a tendência do mês
            df_proj = df_internacao[(df_internacao['Setor'].isin(setores_sel))].groupby('Data').agg({
                'Paciente/Dia': 'sum', 'Leitos-dia': 'sum'
            }).reset_index()
            df_proj['y'] = (df_proj['Paciente/Dia'] / df_proj['Leitos-dia'] * 100)
            df_proj = df_proj.rename(columns={'Data': 'ds'})[['ds', 'y']]
            df_proj['ds'] = df_proj['ds'].dt.tz_localize(None)

            m_proj = Prophet(yearly_seasonality=True, daily_seasonality=False)
            m_proj.fit(df_proj)
            
            # Gera datas até o último dia do mês selecionado
            ultimo_dia_mes = calendar.monthrange(ano_sel, mes_sel)[1]
            data_fim_mes = datetime(ano_sel, mes_sel, ultimo_dia_mes)
            dias_para_prever = (data_fim_mes - df_proj['ds'].max()).days
            
            if dias_para_prever > 0:
                future_proj = m_proj.make_future_dataframe(periods=dias_para_prever)
                forecast_proj = m_proj.predict(future_proj)
                # A projeção final é a média esperada de todo o mês (real + previsto)
                proj_fechamento = forecast_proj[forecast_proj['ds'].dt.month == mes_sel]['yhat'].mean()
        except:
            proj_fechamento = t_at # Fallback para média atual se a IA falhar

    # --- EXIBIÇÃO DOS SCORECARDS COM TOOLTIPS ---
    st.header("📈 Scorecards de Performance")
    cols_n = 6 if is_mes_aberto else 5
    k_cols = st.columns(cols_n)
    
    k_cols[0].metric("Ocupação Atual", f"{t_at:.1f}%", f"{t_at-t_an:.1f}% vs ant.",
                     help="Soma de Paciente-Dia dividida pela soma de Leitos-Dia. Indica o uso da capacidade instalada.")
    
    k_cols[1].metric("Permanência", f"{p_at:.1f} d", f"{p_at-p_an:.1f} d", delta_color="inverse",
                     help="Média de dias que um paciente ocupa um leito. Calculado como Total Paciente-Dia / Total de Saídas.")
    
    k_cols[2].metric("Giro Leito", f"{g_at:.2f}", f"{g_at-g_an:.2f}",
                     help="Produtividade do leito: quantos pacientes utilizaram cada leito operacional no período.")
    
    meta_status = "Na Meta" if 85 <= t_at <= 98 else ("Acima" if t_at > 98 else "Abaixo")
    k_cols[3].metric("Status Meta", meta_status, delta="Alvo: 85-98%", 
                     delta_color="normal" if meta_status == "Na Meta" else "inverse",
                     help="Verifica se a ocupação está no intervalo de segurança (85% a 98%).")
    
    ultimo_dia = calendar.monthrange(ano_sel, mes_sel)[1]
    restante = (date(ano_sel, mes_sel, ultimo_dia) - hoje).days if is_mes_aberto else 0
    k_cols[4].metric("Dias p/ Fechar", f"{max(0, restante)} d",
                     help="Contagem regressiva de dias corridos para o encerramento do mês atual.")

    if is_mes_aberto:
        k_cols[5].metric("Projeção Final (AI)", f"{proj_fechamento:.1f}%", 
                         help="""**PROJEÇÃO COM INTELIGÊNCIA ARTIFICIAL: ** Utiliza o modelo Prophet para analisar a tendência dos dias que já passaram e prever o comportamento até o último dia do mês. Indica com qual Taxa de Ocupação o hospital provavelmente fechará o mês se o padrão atual e a sazonalidade se mantiverem.""")

    with st.expander("📊 Análise Descritiva & Tendências", expanded=True):
        render_analise_descritiva(df_atual, df_anterior, df_internacao, is_mes_aberto)

    with st.expander("💡 Análise Prescritiva", expanded=False):
        render_analise_prescritiva(df_atual)