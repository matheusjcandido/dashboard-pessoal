import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Dashboard Bombeiros PR",
    page_icon="🚒",
    layout="wide"
)

# Função para carregar e processar dados
@st.cache_data
def load_data(file):
    df = pd.read_csv(file, encoding='cp1252', skiprows=7, header=0, skip_blank_lines=True)
    df = df.dropna(how='all')
    # Renomear colunas se necessário
    column_mapping = {
        col: col.strip() for col in df.columns
    }
    df = df.rename(columns=column_mapping)
    return df

def create_age_chart(df, selected_cargo=None):
    # Verificar o nome correto da coluna de idade
    idade_column = [col for col in df.columns if 'IDADE' in col.upper()][0]
    
    # Filtrar por cargo se selecionado
    if selected_cargo:
        df = df[df['CARGO'].isin(selected_cargo)]
    
    # Criar faixas etárias
    bins = [17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
    labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62']
    
    # Converter valores de idade para numérico
    df[idade_column] = pd.to_numeric(df[idade_column], errors='coerce')
    
    df['faixa_etaria'] = pd.cut(df[idade_column], bins=bins, labels=labels, right=True)
    
    # Contar frequência por faixa etária
    idade_counts = df['faixa_etaria'].value_counts().sort_index()
    
    # Criar gráfico de barras
    fig_idade = px.bar(
        x=idade_counts.index,
        y=idade_counts.values,
        labels={'x': 'Faixa Etária', 'y': 'Quantidade'},
        title=f"Distribuição por Idade {' - ' + ', '.join(selected_cargo) if selected_cargo else ''}"
    )
    fig_idade.update_traces(marker_color='red')
    fig_idade.update_layout(
        showlegend=False,
        xaxis_tickangle=0,
        plot_bgcolor='white',
        yaxis_gridcolor='lightgray'
    )
    return fig_idade

def create_cargo_chart(df):
    cargo_counts = df['CARGO'].value_counts()
    
    fig_cargo = px.bar(
        x=cargo_counts.values,
        y=cargo_counts.index,
        orientation='h',
        labels={'x': 'Quantidade', 'y': 'Posto/Graduação'},
        title="Distribuição por Posto/Graduação"
    )
    fig_cargo.update_traces(marker_color='gold')
    fig_cargo.update_layout(
        showlegend=False,
        plot_bgcolor='white',
        xaxis_gridcolor='lightgray'
    )
    return fig_cargo

def main():
    st.title("Dashboard - Corpo de Bombeiros Militar do Paraná")

    uploaded_file = st.file_uploader("Upload de Dados", type="csv")

    if uploaded_file is not None:
        # Carregar dados
        df = load_data(uploaded_file)
        
        # Debug: mostrar nomes das colunas
        st.write("Colunas disponíveis:", df.columns.tolist())
        
        # Mostrar efetivo total
        st.header(f"Efetivo Total: {len(df):,}")

        # Criar colunas para os gráficos
        col1, col2 = st.columns(2)

        with col1:
            try:
                fig_idade = create_age_chart(df)
                st.plotly_chart(fig_idade, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao criar gráfico de idade: {str(e)}")

        with col2:
            try:
                fig_cargo = create_cargo_chart(df)
                st.plotly_chart(fig_cargo, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao criar gráfico de cargo: {str(e)}")

        # Dados Detalhados
        st.subheader("Dados Detalhados")
        
        # Ordenar por nome
        df_sorted = df.sort_values('NOME')
        
        # Mostrar dados com paginação
        st.dataframe(
            df_sorted,
            use_container_width=True,
            height=400  # Altura fixa para permitir rolagem
        )

        # Botão de download
        csv = df_sorted.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download dos dados",
            data=csv,
            file_name=f"dados_bombeiros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
