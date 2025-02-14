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
        df = df[df[cargo_column] == cargo_filter]
        
    # Criar faixas etárias
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
    cargo_counts = df[cargo_column].value_counts()
    
    # Se houver filtro, destacar a barra selecionada
    colors = ['gold'] * len(cargo_counts)
    if cargo_filter:
        colors = ['gold' if cargo != cargo_filter else 'darkgold' 
                 for cargo in cargo_counts.index]
    
    fig = px.bar(
        x=cargo_counts.values,
        y=cargo_counts.index,
        orientation='h',
        labels={'x': 'Quantidade', 'y': 'Posto/Graduação'},
        title="Distribuição por Posto/Graduação"
    )
    fig.update_traces(marker_color=colors)
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

        # Criar botões para cada posto/graduação
        st.write("Filtrar por Posto/Graduação:")
        col_buttons = st.columns(4)  # Ajuste o número de colunas conforme necessário
        
        # Adicionar botão "Todos"
        if col_buttons[0].button("Todos", use_container_width=True):
            st.session_state.cargo_selecionado = None
        
        # Obter lista única de cargos ordenada
        cargos = sorted(df[cargo_column].astype(str).unique())
        
        # Inicializar estado do cargo selecionado se não existir
        if 'cargo_selecionado' not in st.session_state:
            st.session_state.cargo_selecionado = None
            
        # Criar botões para cada cargo
        for i, cargo in enumerate(cargos, 1):  # começar do 1 pois 0 é o botão "Todos"
            col_index = i % 4  # para distribuir em 4 colunas
            if col_buttons[col_index].button(cargo, use_container_width=True):
                if st.session_state.cargo_selecionado == cargo:
                    st.session_state.cargo_selecionado = None
                else:
                    st.session_state.cargo_selecionado = cargo

        # Mostrar efetivo total e filtrado
        total_registros = len(df)
        if st.session_state.cargo_selecionado:
            df_filtered = df[df[cargo_column] == st.session_state.cargo_selecionado]
            st.header(f"Efetivo Filtrado: {len(df_filtered):,} de {total_registros:,}")
        else:
            df_filtered = df
            st.header(f"Efetivo Total: {total_registros:,}")

        # Criar colunas para os gráficos
        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de idade
            fig_idade = create_age_chart(df, st.session_state.cargo_selecionado)
            st.plotly_chart(fig_idade, use_container_width=True)

        with col2:
            # Gráfico de cargo
            fig_cargo = create_cargo_chart(df, st.session_state.cargo_selecionado)
            st.plotly_chart(fig_cargo, use_container_width=True)

        # Dados Detalhados
        st.subheader("Dados Detalhados")
        
        # Ordenar por nome
        df_filtered = df_filtered.sort_values(nome_column)
        
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
