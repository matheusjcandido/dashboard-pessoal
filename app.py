import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(
    page_title="Dashboard Bombeiros PR",
    page_icon="🚒",
    layout="wide"
)

# Função para carregar e processar dados
@st.cache_data
def load_data(file):
    # Pular as 7 primeiras linhas, usar a 8ª como cabeçalho e ignorar a 9ª linha vazia
    df = pd.read_csv(file, encoding='cp1252', skiprows=7, header=0, skip_blank_lines=True)
    # Remover linhas vazias
    df = df.dropna(how='all')
    # Mostrar as colunas disponíveis para debug
    print("Colunas disponíveis:", df.columns.tolist())
    return df

def main():
    st.title("Dashboard - Corpo de Bombeiros Militar do Paraná")

    uploaded_file = st.file_uploader("Upload de Dados", type="csv")

    if uploaded_file is not None:
        # Carregar dados
        df = load_data(uploaded_file)
        
        # Mostrar colunas disponíveis para debug
        st.write("Colunas disponíveis:", df.columns.tolist())

        # Mostrar efetivo total
        st.header(f"Efetivo Total: {len(df):,}")

        # Criar colunas para os gráficos
        col1, col2 = st.columns(2)

        with col1:
            # Distribuição por Idade
            st.subheader("Distribuição por Idade")
            
            # Verificar o nome correto da coluna de idade
            idade_column = next((col for col in df.columns if 'IDADE' in col.upper()), None)
            
            if idade_column:
                # Criar faixas etárias
                bins = [17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
                labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62']
                
                try:
                    df['faixa_etaria'] = pd.cut(df[idade_column], bins=bins, labels=labels, right=True)
                    
                    # Contar frequência por faixa etária
                    idade_counts = df['faixa_etaria'].value_counts().sort_index()
                    
                    # Criar gráfico de barras
                    fig_idade = px.bar(
                        x=idade_counts.index,
                        y=idade_counts.values,
                        labels={'x': 'Faixa Etária', 'y': 'Quantidade'},
                        title="Distribuição por Idade"
                    )
                    fig_idade.update_traces(marker_color='red')
                    fig_idade.update_layout(
                        showlegend=False,
                        xaxis_tickangle=0,
                        plot_bgcolor='white',
                        yaxis_gridcolor='lightgray'
                    )
                    st.plotly_chart(fig_idade, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao processar dados de idade: {str(e)}")
            else:
                st.error("Coluna de idade não encontrada no arquivo")

        with col2:
            # Distribuição por Posto/Graduação
            st.subheader("Distribuição por Posto/Graduação")
            
            # Verificar o nome correto da coluna de cargo
            cargo_column = next((col for col in df.columns if 'CARGO' in col.upper()), None)
            
            if cargo_column:
                cargo_counts = df[cargo_column].value_counts()
                
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
                st.plotly_chart(fig_cargo, use_container_width=True)
            else:
                st.error("Coluna de cargo não encontrada no arquivo")

        # Dados Detalhados
        st.subheader("Dados Detalhados")
        # Mostrar as primeiras linhas do DataFrame para debug
        st.dataframe(df.head(), use_container_width=True)

if __name__ == "__main__":
    main()
