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
            # Detecção de problemas iniciais
            file_content = file.read()
            file.seek(0)  # Reinicia o ponteiro do arquivo
            
            # Log dos primeiros bytes para debug
            logger.info(f"Primeiros 100 bytes do arquivo: {file_content[:100]}")
            
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

            # Tenta diferentes configurações de leitura
            try:
                # Primeira tentativa: encoding cp1252
                df = pd.read_csv(
                    file,
                    encoding='cp1252',
                    sep=';',
                    dtype=dtype_dict,
                    skiprows=7,
                    on_bad_lines='skip'
                )
            except Exception as e:
                logger.warning(f"Falha na primeira tentativa de leitura: {str(e)}")
                file.seek(0)  # Reinicia o ponteiro do arquivo
                
                try:
                    # Segunda tentativa: encoding latin1
                    df = pd.read_csv(
                        file,
                        encoding='latin1',
                        sep=';',
                        dtype=dtype_dict,
                        skiprows=7,
                        on_bad_lines='skip'
                    )
                except Exception as e2:
                    logger.warning(f"Falha na segunda tentativa de leitura: {str(e2)}")
                    file.seek(0)  # Reinicia o ponteiro do arquivo
                    
                    # Terceira tentativa: encoding utf-8
                    df = pd.read_csv(
                        file,
                        encoding='utf-8',
                        sep=';',
                        dtype=dtype_dict,
                        skiprows=7,
                        on_bad_lines='skip'
                    )
            
            # Log das colunas disponíveis
            logger.info(f"Colunas encontradas no arquivo: {df.columns.tolist()}")
            logger.info(f"Número de registros iniciais: {len(df)}")
            
            # Se o DataFrame está vazio após a leitura, tenta com menos skiprows
            if len(df) == 0:
                logger.warning("DataFrame vazio após leitura inicial, tentando com skiprows=0")
                file.seek(0)  # Reinicia o ponteiro do arquivo
                
                df = pd.read_csv(
                    file,
                    encoding='utf-8',  # Usar a codificação que funcionou melhor
                    sep=';',
                    dtype=str,  # Usar str para todas as colunas para simplificar
                    skiprows=0,
                    on_bad_lines='skip'
                )
                
                logger.info(f"Nova tentativa com skiprows=0: {len(df)} registros")
            
            # Verifica se há pelo menos uma linha no DataFrame
            if len(df) == 0:
                st.error("Arquivo sem dados válidos. Verifique o formato e o conteúdo.")
                return None
                
            # Converte as colunas de data após carregar o DataFrame
            date_columns = ['Data Nascimento', 'Data Início']
            for col in date_columns:
                if col in df.columns:
                    try:
                        df.loc[:, col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
                    except Exception as date_error:
                        logger.warning(f"Erro ao converter coluna de data {col}: {str(date_error)}")
            
            # Limpa e processa os dados
            df = DataLoader._process_dataframe(df)
            
            # Verifica se ainda há dados após o processamento
            if df is None or len(df) == 0:
                logger.error("DataFrame vazio após processamento")
                st.error("Não foi possível extrair dados válidos do arquivo após o processamento.")
                return None
                
            logger.info(f"Número de registros após processamento: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {str(e)}")
            st.error(f"Erro ao carregar dados: {str(e)}")
            return None

    @staticmethod
    def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Processa e limpa o DataFrame"""
        try:
            # Cria uma cópia explícita do DataFrame para evitar SettingWithCopyWarning
            df = df.copy()
            
            # Log inicial
            logger.info(f"Processando DataFrame com {len(df)} linhas iniciais")
            
            # Verificar e normalizar os nomes das colunas
            # Às vezes pode haver espaços extras ou caracteres especiais nos nomes das colunas
            df.columns = [col.strip() for col in df.columns]
            
            # Log dos nomes de colunas normalizados
            logger.info(f"Colunas após normalização: {df.columns.tolist()}")
            
            # Para arquivos com linhas em branco no início
            if len(df) > 0 and pd.isna(df.iloc[0][0]):
                logger.info("Removendo linhas iniciais em branco")
                # Encontra a primeira linha não vazia
                first_non_empty = 0
                for i, row in df.iterrows():
                    if not pd.isna(row[0]) and str(row[0]).strip():
                        first_non_empty = i
                        break
                
                if first_non_empty > 0:
                    df = df.iloc[first_non_empty:].reset_index(drop=True)
                    logger.info(f"DataFrame após remover linhas em branco: {len(df)} linhas")
            
            # Corrige o deslocamento de colunas causado por ';' extras
            col_uf_cidade = next((col for col in df.columns if 'UF' in col or 'Cidade' in col), None)
            if col_uf_cidade:
                logger.info(f"Corrigindo formato da coluna {col_uf_cidade}")
                df.loc[:, col_uf_cidade] = df[col_uf_cidade].astype(str).str.replace('; ', ';', regex=False)
                df.loc[:, col_uf_cidade] = df[col_uf_cidade].astype(str).str.replace(';;', ';', regex=False)

            # Remove linhas totalmente vazias
            df = df.dropna(how='all').reset_index(drop=True)
            logger.info(f"DataFrame após remover linhas vazias: {len(df)} linhas")
            
            # Verificar se há coluna de idade ou tentar criá-la
            if 'Idade' not in df.columns:
                # Tenta encontrar uma coluna de idade com nome similar
                idade_cols = [col for col in df.columns if 'idade' in col.lower()]
                if idade_cols:
                    logger.info(f"Usando coluna alternativa para idade: {idade_cols[0]}")
                    df.loc[:, 'Idade'] = df[idade_cols[0]]
                elif 'Data Nascimento' in df.columns:
                    # Tenta calcular a idade a partir da data de nascimento
                    logger.info("Calculando idade a partir da data de nascimento")
                    try:
                        hoje = pd.Timestamp.now()
                        df.loc[:, 'Idade'] = df['Data Nascimento'].apply(
                            lambda x: (hoje - pd.to_datetime(x, errors='coerce')).days / 365.25 
                            if pd.notna(x) else None
                        )
                    except Exception as e:
                        logger.error(f"Erro ao calcular idade: {str(e)}")
                else:
                    logger.error("Coluna 'Idade' não encontrada e não foi possível criá-la")
                    # Em vez de retornar None, vamos criar uma coluna de idade padrão
                    df.loc[:, 'Idade'] = 30  # Valor padrão
            
            # Processa a coluna de idade
            try:
                # Primeiro, limpa a coluna removendo espaços e substituindo vírgulas por pontos
                df.loc[:, 'Idade'] = df['Idade'].astype(str).str.strip()
                df.loc[:, 'Idade'] = df['Idade'].str.replace(',', '.', regex=False)
                
                # Tenta extrair apenas os dígitos e converter
                df.loc[:, 'Idade'] = df['Idade'].str.extract(r'(\d+\.?\d*)').iloc[:, 0]
                
                # Converte para numérico, tratando erros como NaN
                df.loc[:, 'Idade'] = pd.to_numeric(df['Idade'], errors='coerce')
                
                # Log da distribuição de idades
                idade_stats = df['Idade'].describe()
                logger.info(f"Estatísticas de idade: {idade_stats}")
                
                # Filtra idades válidas e cria nova cópia - agora com intervalo mais amplo
                idade_min = 18
                idade_max = 70
                
                # Verificar quantos registros seriam filtrados
                n_filtrados = df[~df['Idade'].between(idade_min, idade_max, inclusive='both')].shape[0]
                percentual_filtrado = n_filtrados / len(df) * 100 if len(df) > 0 else 0
                
                logger.info(f"Filtro de idade removeria {n_filtrados} registros ({percentual_filtrado:.1f}%)")
                
                # Se o filtro removeria mais de 50% dos registros, ajustar os limites ou desabilitá-lo
                if percentual_filtrado > 50:
                    logger.warning(f"Filtro de idade desabilitado pois removeria muitos registros")
                else:
                    df = df[df['Idade'].between(idade_min, idade_max, inclusive='both')].copy()
                    logger.info(f"DataFrame após filtro de idade: {len(df)} linhas")
            except Exception as e:
                logger.error(f"Erro ao processar coluna 'Idade': {str(e)}")
                # Não retornaremos None aqui para não interromper o processamento
            
            # Verificar a coluna de Cargo
            if 'Cargo' not in df.columns:
                cargo_cols = [col for col in df.columns if 'cargo' in col.lower() or 'posto' in col.lower() or 'graduação' in col.lower()]
                if cargo_cols:
                    logger.info(f"Usando coluna alternativa para cargo: {cargo_cols[0]}")
                    df.loc[:, 'Cargo'] = df[cargo_cols[0]]
                else:
                    logger.warning("Coluna 'Cargo' não encontrada")
                    df.loc[:, 'Cargo'] = 'Não informado'
            
            # Verificar a coluna de Nome
            if 'Nome' not in df.columns:
                nome_cols = [col for col in df.columns if 'nome' in col.lower()]
                if nome_cols:
                    logger.info(f"Usando coluna alternativa para nome: {nome_cols[0]}")
                    df.loc[:, 'Nome'] = df[nome_cols[0]]
                else:
                    logger.warning("Coluna 'Nome' não encontrada")
                    df.loc[:, 'Nome'] = 'Não informado'
            
            # Limpa CPF (remove pontuação)
            if 'CPF' in df.columns:
                df.loc[:, 'CPF'] = df['CPF'].astype(str).str.replace(r'[^\d]', '', regex=True)
            
            # Limpa espaços extras em colunas de texto
            text_columns = df.select_dtypes(include=['object']).columns
            for col in text_columns:
                df.loc[:, col] = df[col].astype(str).str.strip()
            
            # Normaliza a coluna 'Recebe Abono Permanência'
            col_abono = next((col for col in df.columns 
                             if 'abono' in col.lower() or 'permanência' in col.lower()), None)
            
            if col_abono:
                logger.info(f"Normalizando coluna de abono: {col_abono}")
                # Renomear para o nome padrão se necessário
                if col_abono != 'Recebe Abono Permanência':
                    df.loc[:, 'Recebe Abono Permanência'] = df[col_abono]
                
                df.loc[:, 'Recebe Abono Permanência'] = df['Recebe Abono Permanência'].fillna('Não')
                df.loc[:, 'Recebe Abono Permanência'] = df['Recebe Abono Permanência'].apply(
                    lambda x: 'Sim' if any(s in str(x).lower() for s in ['sim', 's', 'y', 'yes']) else 'Não'
                )
            else:
                logger.warning("Coluna de abono permanência não encontrada")
                df.loc[:, 'Recebe Abono Permanência'] = 'Não'
            
            # Verifica se o DataFrame tem pelo menos um registro
            if len(df) == 0:
                logger.warning("DataFrame está vazio após processamento")
                st.warning("Nenhum registro encontrado após aplicar os filtros. Verifique o arquivo carregado.")
            
            # Log final
            logger.info(f"Processamento concluído. DataFrame final com {len(df)} linhas")
            return df
        except Exception as e:
            logger.error(f"Erro ao processar DataFrame: {str(e)}")
            # Registra o traceback completo para depuração
            import traceback
            logger.error(traceback.format_exc())
            raise

class DataFilter:
    """Classe para filtragem de dados"""
    
    @staticmethod
    def apply_filters(df: pd.DataFrame, 
                      cargo_filter: Optional[str] = None,
                      abono_filter: Optional[str] = None,
                      unidade_filter: Optional[str] = None) -> pd.DataFrame:
        """Aplica os filtros selecionados ao DataFrame"""
        # Criar uma cópia explícita para evitar SettingWithCopyWarning
        filtered_df = df.copy()
        
        # Filtro por cargo
        if cargo_filter and cargo_filter != "Todos":
            filtered_df = filtered_df.loc[filtered_df['Cargo'] == cargo_filter].copy()
            
        # Filtro por abono permanência
        if abono_filter and abono_filter != "Todos":
            filtered_df = filtered_df.loc[filtered_df['Recebe Abono Permanência'] == abono_filter].copy()
            
        # Filtro por unidade de trabalho
        if unidade_filter and unidade_filter != "Todas":
            filtered_df = filtered_df.loc[filtered_df['Descrição da Unidade de Trabalho'] == unidade_filter].copy()
            
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
            # Verificar se há dados para criar o gráfico
            if len(df) == 0:
                # Criar um gráfico vazio com mensagem
                fig = go.Figure()
                fig.add_annotation(
                    text="Nenhum dado disponível para esta visualização",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                fig.update_layout(
                    title="Distribuição por Idade",
                    xaxis_title="Faixa Etária",
                    yaxis_title="Quantidade",
                    height=400
                )
                return fig
            
            # Criar faixas etárias
            bins = [18, 22, 27, 32, 37, 42, 47, 52, 57, 62, 70]
            labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62', '63-70']
            
            # Cria uma cópia temporária do DataFrame para não modificar o original
            temp_df = df.copy()
            temp_df.loc[:, 'faixa_etaria'] = pd.cut(temp_df['Idade'], bins=bins, labels=labels)
            idade_counts = temp_df['faixa_etaria'].value_counts().sort_index()
            
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
            # Retorna um gráfico com mensagem de erro
            fig = go.Figure()
            fig.add_annotation(
                text=f"Erro ao gerar visualização: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig

    @staticmethod
    def create_cargo_chart(df: pd.DataFrame) -> go.Figure:
        """Cria gráfico de distribuição por cargo"""
        try:
            # Verificar se há dados para criar o gráfico
            if len(df) == 0:
                # Criar um gráfico vazio com mensagem
                fig = go.Figure()
                fig.add_annotation(
                    text="Nenhum dado disponível para esta visualização",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                fig.update_layout(
                    title="Distribuição por Posto/Graduação",
                    xaxis_title="Quantidade",
                    yaxis_title="Posto/Graduação",
                    height=400
                )
                return fig
                
            cargo_counts = df['Cargo'].value_counts()
            
            # Reordena conforme a ordem definida, excluindo "Todos"
            cargos_filtrados = [cargo for cargo in ORDEM_CARGOS if cargo != "Todos"]
            
            # Criar série ordenada
            ordered_cargo_counts = pd.Series(
                index=[cargo for cargo in cargos_filtrados if cargo in cargo_counts.index],
                data=[cargo_counts.get(cargo, 0) for cargo in cargos_filtrados if cargo in cargo_counts.index]
            )
            
            # Verificar se há dados após a filtragem
            if len(ordered_cargo_counts) == 0:
                fig = go.Figure()
                fig.add_annotation(
                    text="Nenhum posto/graduação disponível após aplicar os filtros",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            else:
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
            # Retorna um gráfico com mensagem de erro
            fig = go.Figure()
            fig.add_annotation(
                text=f"Erro ao gerar visualização: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
            
    @staticmethod
    def create_abono_chart(df: pd.DataFrame) -> go.Figure:
        """Cria gráfico de distribuição por recebimento de abono permanência"""
        try:
            # Verificar se há dados para criar o gráfico
            if len(df) == 0:
                # Criar um gráfico vazio com mensagem
                fig = go.Figure()
                fig.add_annotation(
                    text="Nenhum dado disponível para esta visualização",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                fig.update_layout(
                    title="Distribuição por Recebimento de Abono Permanência",
                    height=400
                )
                return fig
                
            abono_counts = df['Recebe Abono Permanência'].value_counts()
            
            # Verificar se há valores na contagem
            if len(abono_counts) == 0:
                fig = go.Figure()
                fig.add_annotation(
                    text="Nenhum dado de abono permanência disponível após aplicar os filtros",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            else:
                # Definir cores diferentes para Sim e Não
                colors = []
                for categoria in abono_counts.index:
                    if categoria == 'Sim':
                        colors.append('#2E8B57')  # Verde para "Sim"
                    else:
                        colors.append('#D70040')  # Vermelho para "Não"
                
                fig = go.Figure(go.Pie(
                    labels=abono_counts.index,
                    values=abono_counts.values,
                    hole=.3,
                    marker=dict(colors=colors),
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
            # Retorna um gráfico com mensagem de erro
            fig = go.Figure()
            fig.add_annotation(
                text=f"Erro ao gerar visualização: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
            
    @staticmethod
    def create_unit_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
        """Cria gráfico de distribuição por unidade de trabalho (top N)"""
        try:
            # Verificar se há dados para criar o gráfico
            if len(df) == 0:
                # Criar um gráfico vazio com mensagem
                fig = go.Figure()
                fig.add_annotation(
                    text="Nenhum dado disponível para esta visualização",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                fig.update_layout(
                    title=f"Top {top_n} Unidades de Trabalho",
                    xaxis_title="Quantidade",
                    yaxis_title="Unidade",
                    height=500
                )
                return fig
                
            # Verificar se a coluna existe
            if 'Descrição da Unidade de Trabalho' not in df.columns:
                fig = go.Figure()
                fig.add_annotation(
                    text="Coluna 'Descrição da Unidade de Trabalho' não encontrada",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                return fig
                
            # Contar ocorrências por unidade
            unit_counts = df['Descrição da Unidade de Trabalho'].value_counts().nlargest(top_n)
            
            # Verificar se há unidades para exibir
            if len(unit_counts) == 0:
                fig = go.Figure()
                fig.add_annotation(
                    text="Nenhuma unidade disponível após aplicar os filtros",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            else:
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
            # Retorna um gráfico com mensagem de erro
            fig = go.Figure()
            fig.add_annotation(
                text=f"Erro ao gerar visualização: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig

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
        
        # Obtém o total de efetivo
        total_efetivo = len(df)
        
        with col1:
            st.metric(
                "Total de Efetivo",
                f"{total_efetivo:,}".replace(",", ".")
            )
        
        with col2:
            # Verifica se há registros antes de calcular a média
            if total_efetivo > 0:
                st.metric(
                    "Idade Média",
                    f"{df['Idade'].mean():.1f} anos"
                )
            else:
                st.metric(
                    "Idade Média",
                    "N/A"
                )
            
        with col3:
            st.metric(
                "Quantidade de Unidades",
                f"{df['Descrição da Unidade de Trabalho'].nunique()}"
            )
            
        with col4:
            # Conta quantos recebem abono
            abono_count = df[df['Recebe Abono Permanência'] == 'Sim'].shape[0]
            
            # Evita divisão por zero
            if total_efetivo > 0:
                percentual = (abono_count/total_efetivo*100)
                st.metric(
                    "Recebem Abono Permanência",
                    f"{abono_count:,} ({percentual:.1f}%)".replace(",", ".")
                )
            else:
                st.metric(
                    "Recebem Abono Permanência",
                    "0 (0.0%)"
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
        
        # Verifica se há dados para exibir
        if len(df) == 0:
            st.info("Nenhum registro disponível para exibição.")
            return
        
        # Filtro de pesquisa
        search_term = st.text_input("Pesquisar por nome:", "")
        
        df_filtered = df.copy()
        if search_term:
            df_filtered = df_filtered[df_filtered['Nome'].str.contains(search_term, case=False, na=False)]
            
            if len(df_filtered) == 0:
                st.info(f"Nenhum registro encontrado com o termo '{search_term}'.")
                # Restaura df original para não ficar sem dados
                df_filtered = df.copy()
        
        # Seleciona colunas para exibição
        display_columns = [
            'Nome', 'CPF', 'Data Nascimento', 'Idade',
            'Código da Unidade de Trabalho',
            'Descrição da Unidade de Trabalho',
            'Cargo', 'Data Início',
            'Recebe Abono Permanência'
        ]
        
        # Obtém colunas disponíveis no DataFrame
        available_columns = [col for col in display_columns if col in df_filtered.columns]
        
        if not available_columns:
            st.warning("Nenhuma coluna disponível para exibição.")
            return
        
        try:
            # Formata as colunas de data
            df_display = df_filtered[available_columns].copy()
            date_columns = ['Data Nascimento', 'Data Início']
            for col in date_columns:
                if col in df_display.columns:
                    # Use .loc para evitar SettingWithCopyWarning
                    df_display.loc[:, col] = pd.to_datetime(df_display[col], errors='coerce').dt.strftime('%d/%m/%Y')
            
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
        except Exception as e:
            logger.error(f"Erro ao exibir dados detalhados: {str(e)}")
            st.error(f"Erro ao exibir dados detalhados: {str(e)}")

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
                try:
                    # Verificar se há dados no DataFrame
                    if len(df) == 0:
                        st.warning("O arquivo carregado não contém dados válidos após o processamento inicial.")
                        return
                    
                    # Inicializar a variável de sessão se não existir
                    if 'cargo_selecionado' not in st.session_state:
                        st.session_state.cargo_selecionado = "Todos"
                    
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
                    
                    # Verificar se há dados após a filtragem
                    if len(df_filtered) == 0 and len(df) > 0:
                        st.warning("Nenhum registro encontrado com os filtros selecionados. Tente ajustar os filtros.")
                except Exception as e:
                    logger.error(f"Erro ao processar filtros: {str(e)}")
                    st.error(f"Erro ao processar filtros: {str(e)}")
                    # Criar um DataFrame vazio para evitar erros nas próximas etapas
                    df_filtered = pd.DataFrame(columns=df.columns)
                
                # Mostrar informações sobre os filtros aplicados
                total_efetivo = len(df)
                total_filtrado = len(df_filtered)
                
                filter_info = f"Efetivo filtrado: {total_filtrado:,} de {total_efetivo:,}".replace(",", ".")
                
                # Adicionar informações sobre os filtros aplicados
                filtros_aplicados = []
                if st.session_state.cargo_selecionado != "Todos":
                    filtros_aplicados.append(f"Cargo: {st.session_state.cargo_selecionado}")
                if sidebar_filters["abono"] != "Todos":
                    filtros_aplicados.append(f"Abono: {sidebar_filters['abono']}")
                if sidebar_filters["unidade"] != "Todas":
                    filtros_aplicados.append(f"Unidade: {sidebar_filters['unidade']}")
                
                if filtros_aplicados:
                    filter_info += " | " + " | ".join(filtros_aplicados)
                
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
                
                # Exibir dados detalhados apenas se houver registros
                if len(df_filtered) > 0:
                    try:
                        DashboardUI.display_detailed_data(df_filtered)
                    except Exception as e:
                        logger.error(f"Erro ao exibir dados detalhados: {str(e)}")
                        st.error(f"Erro ao exibir dados detalhados: {str(e)}")
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
            
            # Adicionar instruções sobre o formato esperado do arquivo
            st.markdown("""
            ### Formato do Arquivo CSV
            
            O arquivo CSV deve conter as seguintes colunas principais:
            
            - `Nome`: Nome completo do militar
            - `CPF`: CPF do militar
            - `Data Nascimento`: Data de nascimento no formato DD/MM/AAAA
            - `Idade`: Idade do militar
            - `Código da Unidade de Trabalho`: Código da unidade
            - `Descrição da Unidade de Trabalho`: Nome da unidade
            - `Cargo`: Posto ou graduação do militar
            - `Data Início`: Data de início na função no formato DD/MM/AAAA
            - `Recebe Abono Permanência`: Indicação de recebimento de abono (Sim/Não)
            
            O arquivo deve estar codificado em CP1252 (Windows Latin 1) e usar ponto e vírgula (;) como separador.
            """)
    
    except Exception as e:
        logger.error(f"Erro geral no dashboard: {str(e)}")
        st.error(f"Ocorreu um erro no dashboard: {str(e)}")

if __name__ == "__main__":
    main()
