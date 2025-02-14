import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_plotly_events import plotly_events

# Configuração da página
st.set_page_config(
    page_title="Dashboard Bombeiros PR",
    page_icon="🚒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ordem específica dos postos/graduações
ORDEM_CARGOS = [
    "Todos",
    "Soldado 2ª Classe",
    "Soldado 1ª Classe",
    "Cabo",
    "3º Sargento",
    "2º Sargento",
    "1º Sargento",
    "Subtenente",
    "Aluno de 1º Ano",
    "Aluno de 2º Ano",
    "Aluno de 3º Ano",
    "Aspirante a Oficial",
    "2º Tenente",
    "2º Tenente 6",
    "1º Tenente",
    "Capitão",
    "Major",
    "Tenente Coronel",
    "Coronel"
]

@st.cache_data
def load_data(file):
    try:
        # Lê o arquivo pulando as linhas de cabeçalho desnecessárias
        df = pd.read_csv(file, encoding='cp1252', skiprows=7, header=0)
        
        # Remove linhas totalmente vazias
        df = df.dropna(how='all')
        
        # Remove colunas totalmente vazias
        df = df.dropna(axis=1, how='all')
        
        # Limpa os nomes das colunas
        df.columns = df.columns.str.strip()
        
        # Identifica a coluna de idade
        idade_col = [col for col in df.columns if 'Idade' in col.upper()][0]
        
        # Converte a coluna de idade para numérico, tratando erros
        df[idade_col] = pd.to_numeric(df[idade_col], errors='coerce')
        
        # Remove linhas com idades inválidas ou fora do intervalo esperado
        df = df[df[idade_col].between(18, 62)]
        
        # Garante que não há valores nulos na coluna de idade
        df = df.dropna(subset=[idade_col])
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {str(e)}")
        return None

def create_age_chart(df, idade_column, cargo_filter=None, cargo_column=None):
    try:
        # Aplicar filtro de cargo se existir
        if cargo_filter and cargo_column:
            df = df[df[cargo_column] == cargo_filter]
        
        # Remover valores nulos ou inválidos e converter para numérico
        df = df[pd.to_numeric(df[idade_column], errors='coerce').notna()]
        df[idade_column] = pd.to_numeric(df[idade_column])
        
        # Criar faixas etárias com intervalos corretos
        bins = [17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
        labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62']
        
        # Garantir que a idade está dentro dos limites
        df = df[df[idade_column].between(18, 62)]
        
        # Criar faixas etárias e contar
        df['faixa_etaria'] = pd.cut(df[idade_column], bins=bins, labels=labels)
        idade_counts = df['faixa_etaria'].value_counts().sort_index()
        
        fig = px.bar(
            x=idade_counts.index,
            y=idade_counts.values,
            labels={'x': 'Faixa Etária', 'y': 'Quantidade'},
            title=f"Distribuição por Idade{' - ' + cargo_filter if cargo_filter else ''}"
        )
        
        fig.update_traces(
            marker_color='red',
            hovertemplate="Faixa: %{x}<br>Quantidade: %{y}<extra></extra>"
        )
        
        fig.update_layout(
            showlegend=False,
            xaxis_tickangle=45,
            plot_bgcolor='white',
            yaxis_gridcolor='lightgray',
            height=400,
            margin=dict(t=50, b=50)
        )
        
        return fig
    except Exception as e:
        st.error(f"Erro ao criar gráfico de idade: {str(e)}")
        return None

def create_cargo_chart(df, cargo_column, cargo_filter=None):
    try:
        if cargo_filter:
            df = df[df[cargo_column] == cargo_filter]
        
        # Ordenar os cargos conforme a ordem especificada
        cargo_counts = df[cargo_column].value_counts()
        cargo_counts = cargo_counts.reindex(
            [cargo for cargo in ORDEM_CARGOS if cargo in cargo_counts.index]
        )
        
        fig = px.bar(
            x=cargo_counts.values,
            y=cargo_counts.index,
            orientation='h',
            labels={'x': 'Quantidade', 'y': 'Posto/Graduação'},
            title="Distribuição por Posto/Graduação"
        )
        
        fig.update_traces(
            marker_color='gold',
            hovertemplate="Quantidade: %{x}<br>%{y}<extra></extra>"
        )
        
        fig.update_layout(
            showlegend=False,
            plot_bgcolor='white',
            xaxis_gridcolor='lightgray',
            height=400,
            margin=dict(t=50, b=50)
        )
        
        return fig
    except Exception as e:
        st.error(f"Erro ao criar gráfico de cargos: {str(e)}")
        return None

def create_summary_metrics(df, cargo_column, idade_column):
    try:
        total_efetivo = len(df)
        idade_media = df[idade_column].mean()
        total_cargos = df[cargo_column].nunique()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Efetivo", f"{total_efetivo:,}".replace(",", "."))
        with col2:
            st.metric("Idade Média", f"{idade_media:.1f} anos")
        with col3:
            st.metric("Total de Postos/Graduações", total_cargos)
            
    except Exception as e:
        st.error(f"Erro ao criar métricas resumidas: {str(e)}")

def main():
    # Configuração do estilo da página
    st.markdown("""
        <style>
        .main {
            padding: 1rem;
        }
        .stButton > button {
            width: 100%;
            font-size: 0.8rem;
            padding: 0.3rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Dashboard - Corpo de Bombeiros Militar do Paraná")
    
    uploaded_file = st.file_uploader("Upload de Dados", type="csv")
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)
        
        if df is not None:
            # Identificar colunas importantes
            idade_column = [col for col in df.columns if 'Idade' in col.upper()][0]
            cargo_column = [col for col in df.columns if 'CARGO' in col.upper()][0]
            nome_column = [col for col in df.columns if 'NOME' in col.upper()][0]
            
            # Criar métricas resumidas
            create_summary_metrics(df, cargo_column, idade_column)
            
            # Filtros de cargo
            st.write("Filtrar por Posto/Graduação:")
            
            # Criar duas linhas de botões
            row1 = st.columns(10)
            row2 = st.columns(10)
            
            # Inicializar estado
            if 'cargo_selecionado' not in st.session_state:
                st.session_state.cargo_selecionado = None
            
            # Primeira linha de botões
            for i in range(10):
                cargo = ORDEM_CARGOS[i]
                if cargo == "Todos":
                    if row1[i].button("Todos", key="btn_todos", use_container_width=True):
                        st.session_state.cargo_selecionado = None
                elif cargo in df[cargo_column].unique():
                    if row1[i].button(cargo, key=f"btn_{i}", use_container_width=True):
                        if st.session_state.cargo_selecionado == cargo:
                            st.session_state.cargo_selecionado = None
                        else:
                            st.session_state.cargo_selecionado = cargo
            
            # Segunda linha de botões
            for i in range(9):
                idx = i + 10
                cargo = ORDEM_CARGOS[idx]
                if cargo in df[cargo_column].unique():
                    if row2[i].button(cargo, key=f"btn_{idx}", use_container_width=True):
                        if st.session_state.cargo_selecionado == cargo:
                            st.session_state.cargo_selecionado = None
                        else:
                            st.session_state.cargo_selecionado = cargo
            
            # Aplicar filtros
            if st.session_state.cargo_selecionado:
                df_filtered = df[df[cargo_column] == st.session_state.cargo_selecionado]
                st.header(f"Efetivo Filtrado: {len(df_filtered):,.0f} de {len(df):,.0f}".replace(",", "."))
            else:
                df_filtered = df
                st.header(f"Efetivo Total: {len(df):,.0f}".replace(",", "."))
            
            # Criar gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                fig_idade = create_age_chart(
                    df_filtered,
                    idade_column,
                    st.session_state.cargo_selecionado,
                    cargo_column
                )
                if fig_idade:
                    selected_idade = plotly_events(fig_idade, click_event=True)
                    if selected_idade:
                        clicked_age = selected_idade[0]['x']
                        if 'idade_filter' not in st.session_state:
                            st.session_state.idade_filter = []
                        if clicked_age in st.session_state.idade_filter:
                            st.session_state.idade_filter.remove(clicked_age)
                        else:
                            st.session_state.idade_filter.append(clicked_age)
                        st.experimental_rerun()
            
            with col2:
                fig_cargo = create_cargo_chart(df_filtered, cargo_column)
                if fig_cargo:
                    st.plotly_chart(fig_cargo, use_container_width=True)
            
            # Dados Detalhados
            st.subheader("Dados Detalhados")
            
            # Adicionar filtros de pesquisa
            search_term = st.text_input("Pesquisar por nome:", "")
            
            if search_term:
                df_filtered = df_filtered[
                    df_filtered[nome_column].str.contains(search_term, case=False, na=False)
                ]
            
            df_filtered = df_filtered.sort_values(nome_column)
            
            st.dataframe(
                df_filtered,
                use_container_width=True,
                height=400
            )
            
            # Botão de download
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download dos dados filtrados",
                data=csv,
                file_name=f"dados_bombeiros_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
