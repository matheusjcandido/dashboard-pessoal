import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
import io
 
# Configuração da página
st.set_page_config(
    page_title="Dashboard CBMPR",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cores do CBMPR
VERMELHO = "#B22222"  # Vermelho bombeiro
DOURADO = "#FFD700"   # Dourado/Amarelo para destaques
PRETO = "#000000"     # Preto para texto
CINZA_CLARO = "#F0F2F6"  # Cor de fundo clara

# Função para aplicar CSS customizado
def aplicar_css():
    st.markdown("""
    <style>
    .main {
        background-color: #F0F2F6;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .titulo-dashboard {
        color: #B22222;
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .card {
        background-color: white;
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        padding: 20px;
        margin-bottom: 20px;
    }
    .card-titulo {
        color: #B22222;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .metrica {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #B22222;
    }
    .metrica-label {
        font-size: 1rem;
        text-align: center;
        color: #000000;
    }
    .footer {
        text-align: center;
        margin-top: 30px;
        color: #777777;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Função para carregar os dados
@st.cache_data
def carregar_dados(arquivo):
    try:
        # Lê o arquivo CSV, pulando as 7 primeiras linhas de metadados
        df = pd.read_csv(arquivo, encoding='cp1252', skiprows=7)
        
        # Remover a linha vazia (linha 8 do arquivo original) se existir
        df = df.dropna(how='all')
        
        # Remover colunas que não interessam
        colunas_excluir = ['Órgão', 'Função', 'Espec. Função', 'Tipo Empregado', 
                           'Tipo Provimento', 'Categoria do Trabalhador', 
                           'Regime Trabalhista', 'Regime Previdenciário', 
                           'Plano de Segregação da Massa', 'Sujeito ao Teto do RGPS', 
                           'UF-Cidade']
        
        # Adicionar colunas sem cabeçalho para serem excluídas
        colunas_sem_cabecalho = [col for col in df.columns if 'Unnamed' in col or col.strip() == '']
        colunas_excluir.extend(colunas_sem_cabecalho)
        
        # Excluir colunas
        df = df.drop(columns=[col for col in colunas_excluir if col in df.columns])
        
        # Converter coluna de idade para numérico
        df['Idade'] = pd.to_numeric(df['Idade'], errors='coerce')
        
        # Ordenar hierarquia militar corretamente
        hierarquia = {
            "Coronel": 1, 
            "Tenente Coronel": 2, 
            "Major": 3, 
            "Capitão": 4, 
            "1º Tenente": 5, 
            "2º Tenente": 6,
            "2º Tenente 6": 6.5,  # Para tratar o cargo adicional
            "Aspirante a Oficial": 7,
            "Subtenente": 8,
            "1º Sargento": 9,
            "2º Sargento": 10, 
            "3º Sargento": 11, 
            "Cabo": 12, 
            "Soldado 1ª Classe": 13,
            "Soldado 2ª Classe": 14,
            "Aluno de 3º Ano": 15,
            "Aluno de 2º Ano": 16,
            "Aluno de 1º Ano": 17
        }
        
        # Adicionar coluna de ordem hierárquica
        df['Ordem_Hierarquica'] = df['Cargo'].map(hierarquia)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Função para gerar estatísticas
def gerar_estatisticas(df):
    total_efetivo = len(df)
    media_idade = df['Idade'].mean()
    
    return {
        'total_efetivo': total_efetivo,
        'media_idade': media_idade
    }

# Função para criar gráfico de distribuição por idade
def grafico_distribuicao_idade(df):
    # Criar faixas etárias
    bins = [18, 25, 30, 35, 40, 45, 50, 55, 100]
    labels = ['18-25', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '56+']
    
    df['Faixa_Etaria'] = pd.cut(df['Idade'], bins=bins, labels=labels, right=False)
    
    # Contar por faixa etária
    contagem_idade = df['Faixa_Etaria'].value_counts().sort_index()
    
    # Criar gráfico
    fig = px.bar(
        x=contagem_idade.index, 
        y=contagem_idade.values,
        labels={'x': 'Faixa Etária', 'y': 'Quantidade'},
        title='Distribuição por Faixa Etária'
    )
    
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font={'color': PRETO},
        title={'font': {'color': VERMELHO}},
        xaxis={'title': {'font': {'color': PRETO}}},
        yaxis={'title': {'font': {'color': PRETO}}},
        hovermode='closest'
    )
    
    fig.update_traces(marker_color=VERMELHO, hovertemplate='Faixa: %{x}<br>Quantidade: %{y}')
    
    return fig

# Função para criar gráfico de distribuição por cargo
def grafico_distribuicao_cargo(df):
    # Contar por cargo e ordenar pela hierarquia
    contagem_cargo = df.groupby(['Cargo', 'Ordem_Hierarquica']).size().reset_index(name='Quantidade')
    contagem_cargo = contagem_cargo.sort_values('Ordem_Hierarquica')
    
    # Criar gráfico
    fig = px.bar(
        contagem_cargo,
        x='Cargo',
        y='Quantidade',
        labels={'Cargo': 'Posto/Graduação', 'Quantidade': 'Quantidade'},
        title='Distribuição por Posto/Graduação'
    )
    
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font={'color': PRETO},
        title={'font': {'color': VERMELHO}},
        xaxis={'title': {'font': {'color': PRETO}}},
        yaxis={'title': {'font': {'color': PRETO}}},
        hovermode='closest'
    )
    
    fig.update_traces(marker_color=VERMELHO, hovertemplate='Cargo: %{x}<br>Quantidade: %{y}')
    
    # Ajustar layout para acomodar nomes longos
    fig.update_layout(xaxis_tickangle=-45)
    
    return fig

# Função para download de dados em CSV
def criar_link_download(df, nome_arquivo):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{nome_arquivo}.csv" class="btn-download">Baixar CSV</a>'
    return href

# Layout principal do dashboard
def main():
    # Aplicar CSS
    aplicar_css()
    
    # Cabeçalho
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<div class="titulo-dashboard">Dashboard do Efetivo - CBMPR</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align: center; margin-bottom: 30px;">Corpo de Bombeiros Militar do Paraná</div>', unsafe_allow_html=True)
    
    # Carregar dados
    st.sidebar.header("Opções")
    uploaded_file = st.sidebar.file_uploader("Carregar arquivo CSV", type=["csv"])
    
    if uploaded_file is not None:
        df = carregar_dados(uploaded_file)
        
        if not df.empty:
            # Sidebar - Filtros
            st.sidebar.subheader("Filtros")
            
            # Filtro de cargo
            todos_cargos = ["Todos"] + sorted(df['Cargo'].unique().tolist())
            cargo_selecionado = st.sidebar.selectbox("Posto/Graduação", todos_cargos)
            
            # Filtro de unidade de trabalho
            todas_unidades = ["Todas"] + sorted(df['Descrição da Unidade de Trabalho'].unique().tolist())
            unidade_selecionada = st.sidebar.selectbox("Unidade de Trabalho", todas_unidades)
            
            # Filtro de abono permanência
            opcoes_abono = ["Todos", "Sim", "Não"]
            abono_selecionado = st.sidebar.selectbox("Recebe Abono Permanência", opcoes_abono)
            
            # Aplicar filtros
            df_filtrado = df.copy()
            
            if cargo_selecionado != "Todos":
                df_filtrado = df_filtrado[df_filtrado['Cargo'] == cargo_selecionado]
                
            if unidade_selecionada != "Todas":
                df_filtrado = df_filtrado[df_filtrado['Descrição da Unidade de Trabalho'] == unidade_selecionada]
                
            if abono_selecionado != "Todos":
                abono_valor = "S" if abono_selecionado == "Sim" else "N"
                df_filtrado = df_filtrado[df_filtrado['Recebe Abono Permanência'] == abono_valor]
            
            # Gerar estatísticas
            estatisticas = gerar_estatisticas(df_filtrado)
            
            # Primeira linha - Cards com métricas
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-titulo">Total de Efetivo</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metrica">{estatisticas["total_efetivo"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with col2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="card-titulo">Média de Idade</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metrica">{estatisticas["media_idade"]:.1f}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Segunda linha - Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(grafico_distribuicao_idade(df_filtrado), use_container_width=True)
                
            with col2:
                st.plotly_chart(grafico_distribuicao_cargo(df_filtrado), use_container_width=True)
            
            # Tabela de dados
            st.subheader("Tabela de Dados")
            
            # Colunas para exibir
            colunas_exibir = ['Nome', 'Cargo', 'Idade', 'Descrição da Unidade de Trabalho', 'Recebe Abono Permanência']
            
            # Ordenar por nome
            df_exibir = df_filtrado[colunas_exibir].sort_values('Nome')
            
            # Exibir tabela
            st.dataframe(df_exibir, height=300)
            
            # Botão de download
            st.markdown(criar_link_download(df_exibir, "dados_cbmpr"), unsafe_allow_html=True)
            
            # Rodapé com informações
            st.markdown('<div class="footer">Dashboard desenvolvido para o Corpo de Bombeiros Militar do Paraná. Dados atualizados em: ' + 
                      datetime.now().strftime("%d/%m/%Y") + '</div>', unsafe_allow_html=True)
        else:
            st.error("Não foi possível processar o arquivo. Verifique se o formato está correto.")
    else:
        # Mensagem inicial
        st.info("👆 Faça o upload do arquivo CSV para visualizar o dashboard.")
        st.markdown("""
        Este dashboard foi desenvolvido para visualização dos dados de pessoal do Corpo de Bombeiros Militar do Paraná.
        
        **Funcionalidades:**
        - Visualização do total de efetivo
        - Média de idade
        - Distribuição por idade
        - Distribuição por posto/graduação
        - Filtros por cargo, unidade de trabalho e abono permanência
        - Tabela de dados com opção de download
        
        Para começar, faça o upload do arquivo CSV usando o botão no menu lateral.
        """)

if __name__ == "__main__":
    main()
