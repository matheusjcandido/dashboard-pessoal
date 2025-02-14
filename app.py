import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from streamlit_plotly_events import plotly_events

# Configuração da página
st.set_page_config(page_title="Dashboard Bombeiros PR", page_icon="🚒", layout="wide")

@st.cache_data
def load_data(file):
    df = pd.read_csv(file, encoding='cp1252', skiprows=7, header=0, skip_blank_lines=True)
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()
    return df

def create_age_chart(df, cargo_filter=None):
    # Aplicar filtro de cargo se existir
    if cargo_filter:
        df = df[df[cargo_column].isin(cargo_filter)]
        
    # Criar faixas etárias
    bins = [17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
    labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62']
    df['faixa_etaria'] = pd.cut(df[idade_column], bins=bins, labels=labels, right=True)
    idade_counts = df['faixa_etaria'].value_counts().sort_index()
    
    fig = px.bar(
        x=idade_counts.index,
        y=idade_counts.values,
        labels={'x': 'Faixa Etária', 'y': 'Quantidade'},
        title=f"Distribuição por Idade{' - ' + ', '.join(cargo_filter) if cargo_filter else ''}"
    )
    fig.update_traces(marker_color='red')
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=0,
        plot_bgcolor='white',
        yaxis_gridcolor='lightgray'
    )
    return fig

def create_cargo_chart(df, idade_filter=None):
    # Aplicar filtro de idade se existir
    if idade_filter:
        df = df[df['faixa_etaria'].isin(idade_filter)]
        
    cargo_counts = df[cargo_column].value_counts()
    
    fig = px.bar(
        x=cargo_counts.values,
        y=cargo_counts.index,
        orientation='h',
        labels={'x': 'Quantidade', 'y': 'Posto/Graduação'},
        title=f"Distribuição por Posto/Graduação{' - ' + ', '.join(idade_filter) if idade_filter else ''}"
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
        # Carregar dados
        df = load_data(uploaded_file)
        
        # Encontrar colunas necessárias
        global idade_column, cargo_column, nome_column
        idade_column = [col for col in df.columns if 'IDADE' in col.upper()][0]
        cargo_column = [col for col in df.columns if 'CARGO' in col.upper()][0]
        nome_column = [col for col in df.columns if 'NOME' in col.upper()][0]
        
        # Converter idade para numérico
        df[idade_column] = pd.to_numeric(df[idade_column], errors='coerce')

        # Inicializar filtros na session state
        if 'cargo_filter' not in st.session_state:
            st.session_state.cargo_filter = []
        if 'idade_filter' not in st.session_state:
            st.session_state.idade_filter = []

        # Mostrar efetivo total
        total_registros = len(df)
        st.header(f"Efetivo Total: {total_registros:,}")

        # Criar colunas para os gráficos
        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de idade
            fig_idade = create_age_chart(df, st.session_state.cargo_filter)
            selected_idade = st.plotly_chart(fig_idade, use_container_width=True)
            
            # Adicionar multiselect para faixas etárias
            if not st.session_state.idade_filter:
                st.caption("Clique nas barras do gráfico acima para filtrar por faixa etária")
            else:
                st.caption(f"Filtros ativos: {', '.join(st.session_state.idade_filter)}")
                if st.button("Limpar filtros de idade"):
                    st.session_state.idade_filter = []
                    st.experimental_rerun()

        with col2:
            # Gráfico de cargo
            fig_cargo = create_cargo_chart(df, st.session_state.idade_filter)
            selected_cargo = st.plotly_chart(fig_cargo, use_container_width=True)
            
            # Adicionar multiselect para cargos
            if not st.session_state.cargo_filter:
                st.caption("Clique nas barras do gráfico acima para filtrar por cargo")
            else:
                st.caption(f"Filtros ativos: {', '.join(st.session_state.cargo_filter)}")
                if st.button("Limpar filtros de cargo"):
                    st.session_state.cargo_filter = []
                    st.experimental_rerun()

        # Dados Detalhados
        st.subheader("Dados Detalhados")
        
        # Aplicar filtros
        df_filtered = df.copy()
        if st.session_state.cargo_filter:
            df_filtered = df_filtered[df_filtered[cargo_column].isin(st.session_state.cargo_filter)]
        if st.session_state.idade_filter:
            df_filtered = df_filtered[df_filtered['faixa_etaria'].isin(st.session_state.idade_filter)]

        # Ordenar por nome
        df_filtered = df_filtered.sort_values(nome_column)
        
        # Mostrar quantidade de registros filtrados
        registros_filtrados = len(df_filtered)
        if registros_filtrados != total_registros:
            st.write(f"Mostrando {registros_filtrados:,} de {total_registros:,} registros")

        # Mostrar dados com paginação
        st.dataframe(
            df_filtered,
            use_container_width=True,
            height=400
        )

        # Botão de download dos dados filtrados
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download dos dados filtrados",
            data=csv,
            file_name=f"dados_bombeiros_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
