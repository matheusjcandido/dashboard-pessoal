import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Optional, List, Dict, Any
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
            
            # Log das colunas disponíveis apenas no logger
            logger.info(f"Colunas encontradas no arquivo: {df.columns.tolist()}")
            
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
                    df = df[df['Idade'].between(18, 70, inclusive='both')]
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
            
            # Normaliza a coluna 'Recebe Abono Permanência'
            if 'Recebe Abono Permanência' in df.columns:
                df['Recebe Abono Permanência'] = df['Recebe Abono Permanência'].fillna('Não')
                df['Recebe Abono Permanência'] = df['Recebe Abono Permanência'].apply(
                    lambda x: 'Sim' if 'Sim' in str(x) or 'sim' in str(x) or 'S' in str(x) else 'Não'
                )
            
            # Garante ordem das colunas conforme esperado
            expected_cols = [col for col in DataLoader.EXPECTED_COLUMNS if col in df.columns]
            df = df[expected_cols]
            
            return df
        except Exception as e:
            logger.error(f"Erro ao processar DataFrame: {str(e)}")
            raise

class DataFilter:
    """Classe para filtragem de dados"""
    
    @staticmethod
    def apply_filters(df: pd.DataFrame, 
                      cargo_filter: Optional[str] = None,
                      abono_filter: Optional[str] = None,
                      unidade_filter: Optional[str] = None) -> pd.DataFrame:
        """Aplica os filtros selecionados ao DataFrame"""
        filtered_df = df.copy()
        
        # Filtro por cargo
        if cargo_filter and cargo_filter != "Todos":
            filtered_df = filtered_df[filtered_df['Cargo'] == cargo_filter]
            
        # Filtro por abono permanência
        if abono_filter and abono_filter != "Todos":
            filtered_df = filtered_df[filtered_df['Recebe Abono Permanência'] == abono_filter]
            
        # Filtro por unidade de trabalho
        if unidade_filter and unidade_filter != "Todas":
            filtered_df = filtered_df[filtered_df['Descrição da Unidade de Trabalho'] == unidade_filter]
            
        return filtered_df
    
    @staticmethod
    def get_unique_values(df: pd.DataFrame, column: str) -> List[str]:
        """Obtém valores únicos de uma coluna"""
        if column in df.columns:
            unique_values = df[column].dropna().unique().tolist()
            return sorted(unique_values)
        return []

class ChartManager:
    """Gerenciador de gráficos do dashboard"""
    
    @staticmethod
    def create_age_chart(df: pd.DataFrame) -> go.Figure:
        """Cria gráfico de distribuição de idade"""
        try:
            # Criar faixas etárias
            bins = [18, 22, 27, 32, 37, 42, 47, 52, 57, 62, 70]
            labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62', '63-70']
            
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
                title="Distribuição por Idade",
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
            
            # Reordena conforme a ordem definida
            ordered_cargo_counts = pd.Series(
                index=[cargo for cargo in ORDEM_CARGOS if cargo in cargo_counts.index and cargo != "Todos"],
                data=[cargo_counts.get(cargo, 0) for cargo in ORDEM_CARGOS if cargo in cargo_counts.index and cargo != "Todos"]
            )
            
            fig = go.Figure(go.Bar(
                x=ordered_cargo_counts.values,
                y=ordered_cargo_counts.index,
                orientation='h',
                marker_color='gold',
                text=ordered_cargo_counts.values,
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
            
    @staticmethod
    def create_abono_chart(df: pd.DataFrame) -> go.Figure:
        """Cria gráfico de distribuição por recebimento de abono permanência"""
        try:
            abono_counts = df['Recebe Abono Permanência'].value_counts()
            
            fig = go.Figure(go.Pie(
                labels=abono_counts.index,
                values=abono_counts.values,
                hole=.3,
                marker=dict(colors=['#2E8B57', '#D70040']),
                textinfo='value+percent',
                insidetextorientation='radial'
            ))
            
            fig.update_layout(
                title="Distribuição por Recebimento de Abono Permanência",
                showlegend=True,
                height=400,
                margin=dict(t=50, b=50)
            )
            
            return fig
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de abono: {str(e)}")
            return None
            
    @staticmethod
    def create_unit_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
        """Cria gráfico de distribuição por unidade de trabalho (top N)"""
        try:
            unit_counts = df['Descrição da Unidade de Trabalho'].value_counts().nlargest(top_n)
            
            fig = go.Figure(go.Bar(
                x=unit_counts.values,
                y=unit_counts.index,
                orientation='h',
                marker_color='skyblue',
                text=unit_counts.values,
                textposition='auto',
            ))
            
            fig.update_layout(
                title=f"Top {top_n} Unidades de Trabalho",
                xaxis_title="Quantidade",
                yaxis_title="Unidade",
                showlegend=False,
                plot_bgcolor='white',
                height=500,
                margin=dict(t=50, b=50, l=250)  # Aumentar margem esquerda para nomes longos
            )
            
            return fig
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de unidades: {str(e)}")
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
        col1, col2, col3, col4 = st.columns(4)
        
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
            
        with col4:
            abono_count = df[df['Recebe Abono Permanência'] == 'Sim'].shape[0]
            st.metric(
                "Recebem Abono Permanência",
                f"{abono_count:,} ({abono_count/len(df)*100:.1f}%)".replace(",", ".")
            )

    @staticmethod
    def create_sidebar_filters(df: pd.DataFrame) -> Dict[str, Any]:
        """Cria filtros na barra lateral e retorna os valores selecionados"""
        st.sidebar.title("Filtros")
        
        # Filtro por Abono Permanência
        abono_options = ["Todos", "Sim", "Não"]
        abono_filter = st.sidebar.selectbox(
            "Recebe Abono Permanência:", 
            abono_options,
            index=0
        )
         
        # Filtro por Unidade de Trabalho
        unidades = ["Todas"] + DataFilter.get_unique_values(df, 'Descrição da Unidade de Trabalho')
        unidade_filter = st.sidebar.selectbox(
            "Unidade de Trabalho:", 
            unidades,
            index=0
        )
        
        # Botão para limpar filtros
        if st.sidebar.button("Limpar Filtros"):
            return {
                "abono": "Todos",
                "unidade": "Todas"
            }
        
        return {
            "abono": abono_filter,
            "unidade": unidade_filter
        }
    
    @staticmethod
    def create_cargo_filters():
        """Cria filtros de cargo"""
        if 'cargo_selecionado' not in st.session_state:
            st.session_state.cargo_selecionado = "Todos"
            
        # Cria duas linhas com botões divididos igualmente
        cols_per_row = 5
        row1 = st.columns(cols_per_row)
        row2 = st.columns(cols_per_row)
        row3 = st.columns(cols_per_row)
        row4 = st.columns(cols_per_row)
        
        # Distribui os botões nas linhas
        for i, cargo in enumerate(ORDEM_CARGOS):
            row_idx = i // cols_per_row
            col_idx = i % cols_per_row
            
            if row_idx == 0:
                if row1[col_idx].button(cargo, key=f"btn_{i}", use_container_width=True):
                    st.session_state.cargo_selecionado = "Todos" if st.session_state.cargo_selecionado == cargo else cargo
            elif row_idx == 1:
                if row2[col_idx].button(cargo, key=f"btn_{i}", use_container_width=True):
                    st.session_state.cargo_selecionado = "Todos" if st.session_state.cargo_selecionado == cargo else cargo
            elif row_idx == 2:
                if row3[col_idx].button(cargo, key=f"btn_{i}", use_container_width=True):
                    st.session_state.cargo_selecionado = "Todos" if st.session_state.cargo_selecionado == cargo else cargo
            elif row_idx == 3:
                if row4[col_idx].button(cargo, key=f"btn_{i}", use_container_width=True):
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
        
        # Obtém colunas disponíveis no DataFrame
        available_columns = [col for col in display_columns if col in df.columns]
        
        # Formata as colunas de data
        df_display = df[available_columns].copy()
        date_columns = ['Data Nascimento', 'Data Início']
        for col in date_columns:
            if col in df_display.columns:
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
            
            if df is not None:
                # Criar filtros na barra lateral
                sidebar_filters = DashboardUI.create_sidebar_filters(df)
                
                # Criar filtros de cargo
                st.write("Filtrar por Posto/Graduação:")
                DashboardUI.create_cargo_filters()
                
                # Exibir o cargo selecionado
                st.write(f"Cargo selecionado: **{st.session_state.cargo_selecionado}**")
                
                # Aplicar todos os filtros
                df_filtered = DataFilter.apply_filters(
                    df,
                    cargo_filter=st.session_state.cargo_selecionado,
                    abono_filter=sidebar_filters["abono"],
                    unidade_filter=sidebar_filters["unidade"]
                )
                
                # Mostrar informações sobre os filtros aplicados
                filter_info = f"Efetivo filtrado: {len(df_filtered):,} de {len(df):,}".replace(",", ".")
                if sidebar_filters["abono"] != "Todos":
                    filter_info += f" | Abono: {sidebar_filters['abono']}"
                if sidebar_filters["unidade"] != "Todas":
                    filter_info += f" | Unidade: {sidebar_filters['unidade']}"
                st.header(filter_info)
                
                # Criar métricas resumidas
                DashboardUI.create_summary_metrics(df_filtered)
                
                # Criar gráficos em duas linhas de duas colunas
                row1_col1, row1_col2 = st.columns(2)
                row2_col1, row2_col2 = st.columns(2)
                
                with row1_col1:
                    fig_idade = ChartManager.create_age_chart(df_filtered)
                    if fig_idade:
                        st.plotly_chart(fig_idade, use_container_width=True)
                
                with row1_col2:
                    fig_cargo = ChartManager.create_cargo_chart(df_filtered)
                    if fig_cargo:
                        st.plotly_chart(fig_cargo, use_container_width=True)
                
                with row2_col1:
                    fig_abono = ChartManager.create_abono_chart(df_filtered)
                    if fig_abono:
                        st.plotly_chart(fig_abono, use_container_width=True)
                
                with row2_col2:
                    fig_unit = ChartManager.create_unit_chart(df_filtered)
                    if fig_unit:
                        st.plotly_chart(fig_unit, use_container_width=True)
                
                # Exibir dados detalhados
                DashboardUI.display_detailed_data(df_filtered)
        else:
            st.info("👆 Carregue um arquivo CSV com os dados do efetivo para começar.")
            st.markdown("""
            ### Sobre o Dashboard
            
            Este dashboard foi desenvolvido para facilitar a visualização de dados relacionados ao 
            efetivo do Corpo de Bombeiros Militar do Paraná. Ele permite:
            
            - Visualizar o efetivo total
            - Analisar a distribuição por idade
            - Filtrar por posto/graduação
            - Filtrar por recebimento de abono permanência
            - Filtrar por unidade de trabalho
            - Exportar dados filtrados
            
            Carregue um arquivo CSV no formato adequado para começar a utilizar.
            """)
    
    except Exception as e:
        logger.error(f"Erro geral no dashboard: {str(e)}")
        st.error(f"Ocorreu um erro no dashboard: {str(e)}")

if __name__ == "__main__":
    main()
