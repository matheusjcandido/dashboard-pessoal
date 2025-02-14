import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_plotly_events import plotly_events

# Configuração da página
st.set_page_config(page_title="Dashboard Bombeiros PR", page_icon="🚒", layout="wide")

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
    df = pd.read_csv(file, encoding='cp1252', skiprows=7, header=0, skip_blank_lines=True)
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()
    return df

def create_age_chart(df, cargo_filter=None):
    # Aplicar filtro de cargo se existir
    if cargo_filter:
        df = df[df[cargo_column] == cargo_filter]
        
    bins = [17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
    labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62']
    df['faixa_etaria'] = pd.cut(df[idade_column], bins=bins, labels=labels, right=True)
    idade_counts = df['faixa_etaria'].value_counts().sort_index()
    
    fig = px.bar(
        x=idade_counts.index,
        y=idade_counts.values,
        labels={'x': 'Faixa Etária', 'y': 'Quantidade'},
        title=f"Distribuição por Idade{' - ' + cargo_filter if cargo_filter else ''}"
    )
    fig.update_traces(marker_color='red')
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=0,
        plot_bgcolor='white',
        yaxis_gridcolor='lightgray'
    )
    return fig

def create_cargo_chart(df, cargo_filter=None):
    if cargo_filter:
        df = df[df[cargo_column] == cargo_filter]
        
    cargo_counts = df[cargo_column].value_counts()
    
    fig = px.bar(
        x=cargo_counts.values,
        y=cargo_counts.index,
        orientation='h',
        labels={'x': 'Quantidade', 'y': 'Posto/Graduação'},
        title="Distribuição por Posto/Graduação"
    )
    fig.update_traces(marker_color='gold')
    fig.update_layout(
        showlegend=False,
        plot_bgcolor='white',
        xaxis_gridcolor='lightgray'
    )
    return fig

def main():
    st.title("Dashboard - Corpo de Bombeiros Militar do Paraná")

    uploaded_file = st.file_uploader("Upload de Dados", type="csv")

    if uploaded_file is not None:
        df = load_data(uploaded_file)
        
        global idade_column, cargo_column, nome_column
        idade_column = [col for col in df.columns if 'IDADE' in col.upper()][0]
        cargo_column = [col for col in df.columns if 'CARGO' in col.upper()][0]
        nome_column = [col for col in df.columns if 'NOME' in col.upper()][0]
        
        df[idade_column] = pd.to_numeric(df[idade_column], errors='coerce')

       st.write("Filtrar por Posto/Graduação:")

# Criar duas linhas de botões (10 na primeira, 9 na segunda)
row1 = st.columns(10)  # Primeira linha com 10 botões
row2 = st.columns(10)  # Segunda linha com 9 botões (um espaço vazio no final)

# Inicializar estado
if 'cargo_selecionado' not in st.session_state:
    st.session_state.cargo_selecionado = None

# Primeira linha de botões (0-9)
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

# Segunda linha de botões (10-18)
for i in range(9):
    idx = i + 10
    cargo = ORDEM_CARGOS[idx]
    if cargo in df[cargo_column].unique():
        if row2[i].button(cargo, key=f"btn_{idx}", use_container_width=True):
            if st.session_state.cargo_selecionado == cargo:
                st.session_state.cargo_selecionado = None
            else:
                st.session_state.cargo_selecionado = cargo

# Modificar a exibição do efetivo total para usar separador de milhar
if st.session_state.cargo_selecionado:
    df_filtered = df[df[cargo_column] == st.session_state.cargo_selecionado]
    st.header(f"Efetivo Filtrado: {len(df_filtered):,.0f} de {len(df):,.0f}".replace(",", "."))
else:
    df_filtered = df
    st.header(f"Efetivo Total: {len(df):,.0f}".replace(",", "."))

        # Filtrar DataFrame
        if st.session_state.cargo_selecionado:
            df_filtered = df[df[cargo_column] == st.session_state.cargo_selecionado]
            st.header(f"Efetivo Filtrado: {len(df_filtered):,} de {len(df):,}")
        else:
            df_filtered = df
            st.header(f"Efetivo Total: {len(df):,}")

        col1, col2 = st.columns(2)

        with col1:
            fig_idade = create_age_chart(df_filtered)
            st.plotly_chart(fig_idade, use_container_width=True)

        with col2:
            fig_cargo = create_cargo_chart(df_filtered)
            st.plotly_chart(fig_cargo, use_container_width=True)

        # Dados Detalhados
        st.subheader("Dados Detalhados")
        
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
