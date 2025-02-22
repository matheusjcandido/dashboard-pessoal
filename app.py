import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Optional
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações e constantes
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

class DataLoader:
    """Classe responsável por carregar e processar os dados do CSV"""
    
    EXPECTED_COLUMNS = [
        'ID', 'Nome', 'RG', 'CPF', 'Data Nascimento', 'Idade', 'Órgão',
        'Código da Unidade de Trabalho', 'Descrição da Unidade de Trabalho',
        'Cargo', 'Função', 'Espec. Função', 'Data Início', 'Tipo Empregado',
        'Tipo Provimento', 'Recebe Abono Permanência', 'Categoria do Trabalhador',
        'Regime Trabalhista', 'Regime Previdenciário', 'Plano de Segregação da Massa',
        'Sujeito ao Teto do RGPS', 'UF-Cidade'
    ]

    @staticmethod
    @st.cache_data(ttl=3600)
    def load_data(file) -> pd.DataFrame:
        """Carrega e processa o arquivo CSV"""
        try:
            # Define tipos de dados para todas as colunas
            dtype_dict = {
                'ID': str,
                'Nome': str,
                'RG': str,
                'CPF': str,
                'Data Nascimento': str,
                'Idade': str,  # Será convertido depois
                'Órgão': str,
                'Código da Unidade de Trabalho': str,
                'Descrição da Unidade de Trabalho': str,
                'Cargo': str,
                'Função': str,
                'Espec. Função': str,
                'Data Início': str,
                'Tipo Empregado': str,
                'Tipo Provimento': str,
                'Recebe Abono Permanência': str,
                'Categoria do Trabalhador': str,
                'Regime Trabalhista': str,
                'Regime Previdenciário': str,
                'Plano de Segregação da Massa': str,
                'Sujeito ao Teto do RGPS': str,
                'UF-Cidade': str
            }

            # Carrega o CSV pulando linhas de metadados
            df = pd.read_csv(
                file,
                encoding='cp1252',
                sep=';',
                dtype=dtype_dict,
                skiprows=7,
                on_bad_lines='skip'
            )
            
            # Log das colunas disponíveis
            logger.info(f"Colunas encontradas no arquivo: {df.columns.tolist()}")
            st.write("Colunas encontradas no arquivo:", df.columns.tolist())
            
            # Converte as colunas de data após carregar o DataFrame
            date_columns = ['Data Nascimento', 'Data Início']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
            
            # Limpa e processa os dados
            df = DataLoader._process_dataframe(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {str(e)}")
            st.error(f"Erro ao carregar dados: {str(e)}")
            return None

    @staticmethod
    def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Processa e limpa o DataFrame"""
        try:
            # Corrige o deslocamento de colunas causado por ';' extras
            if 'UF-Cidade' in df.columns:
                df['UF-Cidade'] = df['UF-Cidade'].str.replace('; ', ';', regex=False)
                df['UF-Cidade'] = df['UF-Cidade'].str.replace(';;', ';', regex=False)

            # Remove linhas totalmente vazias
            df = df.dropna(how='all')
            
            # Processa a coluna de idade
            try:
                if 'Idade' in df.columns:
                    # Primeiro, limpa a coluna removendo espaços e substituindo vírgulas por pontos
                    df['Idade'] = df['Idade'].astype(str).str.strip()
                    df['Idade'] = df['Idade'].str.replace(',', '.')
                    # Converte para numérico, tratando erros como NaN
                    df['Idade'] = pd.to_numeric(df['Idade'], errors='coerce')
                    # Filtra idades válidas
                    df = df[df['Idade'].between(18, 62, inclusive='both')]
                else:
                    logger.error("Coluna 'Idade' não encontrada no DataFrame")
                    st.error("Coluna 'Idade' não encontrada nos dados")
                    return None
            except Exception as e:
                logger.error(f"Erro ao processar coluna 'Idade': {str(e)}")
                st.error(f"Erro ao processar coluna 'Idade': {str(e)}")
                return None
            
            # Limpa CPF (remove pontuação)
            df['CPF'] = df['CPF'].str.replace(r'[^\d]', '', regex=True)
            
            # Limpa espaços extras em colunas de texto
            text_columns = df.select_dtypes(include=['object']).columns
            for col in text_columns:
                df[col] = df[col].str.strip()
            
            # Garante ordem das colunas conforme esperado
            expected_cols = [col for col in DataLoader.EXPECTED_COLUMNS if col in df.columns]
            df = df[expected_cols]
            
            return df
        except Exception as e:
            logger.error(f"Erro ao processar DataFrame: {str(e)}")
            raise

class DataValidator:
    """Classe para validação dos dados"""
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> bool:
        """Valida o DataFrame carregado"""
        if df is None:
            st.error("DataFrame não foi carregado corretamente")
            return False
            
        # Verifica colunas obrigatórias
        required_columns = ['Nome', 'CPF', 'Idade', 'Cargo']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Colunas obrigatórias faltando: {missing_columns}")
            return False
            
        # Verifica valores únicos em colunas chave
        if df['CPF'].duplicated().any():
            st.warning("Existem CPFs duplicados nos dados")
            
        # Verifica distribuição de idades
        idade_stats = df['Idade'].describe()
        if idade_stats['min'] < 18 or idade_stats['max'] > 62:
            st.warning("Existem idades fora do intervalo esperado (18-62)")
            
        return True

class ChartManager:
    """Gerenciador de gráficos do dashboard"""
    
    @staticmethod
    def create_age_chart(df: pd.DataFrame, cargo_filter: Optional[str] = None) -> go.Figure:
        """Cria gráfico de distribuição de idade"""
        try:
            if cargo_filter and cargo_filter != "Todos":
                df = df[df['Cargo'] == cargo_filter]
            
            # Criar faixas etárias
            bins = [18, 22, 27, 32, 37, 42, 47, 52, 57, 62]
            labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62']
            
            df['faixa_etaria'] = pd.cut(df['Idade'], bins=bins, labels=labels)
            idade_counts = df['faixa_etaria'].value_counts().sort_index()
            
            fig = go.Figure(go.Bar(
                x=list(idade_counts.index),
                y=idade_counts.values,
                marker_color='red',
                text=idade_counts.values,
                textposition='auto',
            ))
            
            fig.update_layout(
                title=f"Distribuição por Idade{' - ' + cargo_filter if cargo_filter and cargo_filter != 'Todos' else ''}",
                xaxis_title="Faixa Etária",
                yaxis_title="Quantidade",
                showlegend=False,
                plot_bgcolor='white',
                height=400,
                margin=dict(t=50, b=50)
            )
            
            return fig
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de idade: {str(e)}")
            return None

    @staticmethod
    def create_cargo_chart(df: pd.DataFrame) -> go.Figure:
        """Cria gráfico de distribuição por cargo"""
        try:
            cargo_counts = df['Cargo'].value_counts()
            cargo_counts = cargo_counts.reindex(
                [cargo for cargo in ORDEM_CARGOS if cargo in cargo_counts.index]
            )
            
            fig = go.Figure(go.Bar(
                x=cargo_counts.values,
                y=cargo_counts.index,
                orientation='h',
                marker_color='gold',
                text=cargo_counts.values,
                textposition='auto',
            ))
            
            fig.update_layout(
                title="Distribuição por Posto/Graduação",
                xaxis_title="Quantidade",
                yaxis_title="Posto/Graduação",
                showlegend=False,
                plot_bgcolor='white',
                height=400,
                margin=dict(t=50, b=50)
            )
            
            return fig
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de cargos: {str(e)}")
            return None

class DashboardUI:
    """Gerenciador da interface do usuário"""
    
    @staticmethod
    def setup_page():
        """Configura a página do Streamlit"""
        st.set_page_config(
            page_title="Dashboard CBMPR",
            page_icon="🚒",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.markdown("""
            <style>
            .main {
                padding: 1rem;
            }
            .stButton > button {
                width: 100%;
                padding: 0.3rem;
            }
            .metric-container {
                background-color: #f0f2f6;
                padding: 1rem;
                border-radius: 0.5rem;
                margin: 0.5rem 0;
            }
            </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def create_summary_metrics(df: pd.DataFrame):
        """Cria métricas resumidas"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total de Efetivo",
                f"{len(df):,}".replace(",", ".")
            )
        
        with col2:
            st.metric(
                "Idade Média",
                f"{df['Idade'].mean():.1f} anos"
            )
            
        with col3:
            st.metric(
                "Quantidade de Unidades",
                f"{df['Descrição da Unidade de Trabalho'].nunique()}"
            )

    @staticmethod
    def create_cargo_filters():
        """Cria filtros de cargo"""
        if 'cargo_selecionado' not in st.session_state:
            st.session_state.cargo_selecionado = "Todos"
            
        # Cria duas linhas com 10 colunas cada
        row1 = st.columns(10)
        row2 = st.columns(10)
        
        # Primeira linha de botões (0-9)
        for i in range(10):
            cargo = ORDEM_CARGOS[i]
            if row1[i].button(cargo, key=f"btn_{i}", use_container_width=True):
                st.session_state.cargo_selecionado = "Todos" if st.session_state.cargo_selecionado == cargo else cargo
        
        # Segunda linha de botões (10-18)
        remaining_cargos = len(ORDEM_CARGOS) - 10
        for i in range(remaining_cargos):
            idx = i + 10
            cargo = ORDEM_CARGOS[idx]
            if row2[i].button(cargo, key=f"btn_{idx}", use_container_width=True):
                st.session_state.cargo_selecionado = "Todos" if st.session_state.cargo_selecionado == cargo else cargo

    @staticmethod
    def display_detailed_data(df: pd.DataFrame):
        """Exibe dados detalhados com filtros"""
        st.subheader("Dados Detalhados")
        
        # Filtro de pesquisa
        search_term = st.text_input("Pesquisar por nome:", "")
        
        if search_term:
            df = df[df['Nome'].str.contains(search_term, case=False, na=False)]
        
        # Seleciona colunas para exibição
        display_columns = [
            'Nome', 'CPF', 'Data Nascimento', 'Idade',
            'Código da Unidade de Trabalho',
            'Descrição da Unidade de Trabalho',
            'Cargo', 'Data Início',
            'Recebe Abono Permanência'
        ]
        
        # Formata as colunas de data
        df_display = df[display_columns].copy()
        date_columns = ['Data Nascimento', 'Data Início']
        for col in date_columns:
            df_display[col] = pd.to_datetime(df_display[col]).dt.strftime('%d/%m/%Y')
        
        # Exibe o DataFrame
        st.dataframe(df_display, use_container_width=True, height=400)
        
        # Botão de download
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download dos dados filtrados",
            data=csv,
            file_name=f"dados_bombeiros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def main():
    """Função principal do dashboard"""
    try:
        DashboardUI.setup_page()
        
        st.title("Dashboard - Corpo de Bombeiros Militar do Paraná")
        
        uploaded_file = st.file_uploader("Upload de Dados", type="csv")
        
        if uploaded_file is not None:
            # Carrega os dados
            df = DataLoader.load_data(uploaded_file)
            
            if df is not None and DataValidator.validate_dataframe(df):
                # Criar métricas resumidas
                DashboardUI.create_summary_metrics(df)
                
                # Criar filtros de cargo
                st.write("Filtrar por Posto/Graduação:")
                DashboardUI.create_cargo_filters()
                
                try:
                    # Aplicar filtro selecionado
                    if st.session_state.cargo_selecionado and st.session_state.cargo_selecionado != "Todos":
                        df_filtered = df[df['Cargo'] == st.session_state.cargo_selecionado]
                        st.header(f"Efetivo Filtrado: {len(df_filtered):,.0f} de {len(df):,.0f}".replace(",", "."))
                    else:
                        df_filtered = df
                        st.header(f"Efetivo Total: {len(df):,.0f}".replace(",", "."))
                    
                    # Criar gráficos
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_idade = ChartManager.create_age_chart(
                            df_filtered,
                            st.session_state.cargo_selecionado
                        )
                        if fig_idade:
                            st.plotly_chart(fig_idade, use_container_width=True)
                    
                    with col2:
                        fig_cargo = ChartManager.create_cargo_chart(df_filtered)
                        if fig_cargo:
                            st.plotly_chart(fig_cargo, use_container_width=True)
                    
                    # Exibir dados detalhados
                    DashboardUI.display_detailed_data(df_filtered)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar dados filtrados: {str(e)}")
                    st.error("Erro ao processar dados filtrados")
    
    except Exception as e:
        logger.error(f"Erro geral no dashboard: {str(e)}")
        st.error("Ocorreu um erro no dashboard")

if __name__ == "__main__":
    main()
