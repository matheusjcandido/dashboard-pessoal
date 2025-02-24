import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Union, Any
import logging
import re
import numpy as np
from streamlit_plotly_events import plotly_events
import time
import os
import base64
from io import BytesIO
import traceback

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dashboard_cbmpr")

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

CORES_PADRAO = {
    "primaria": "#F44336",     # Vermelho bombeiro
    "secundaria": "#FFD700",   # Dourado
    "terciaria": "#4682B4",    # Azul aço
    "fundo": "#FFFFFF",        # Branco
    "texto": "#212121",        # Cinza escuro
    "destaque": "#FF5722"      # Laranja escuro
}

# Constantes para faixas etárias
FAIXAS_ETARIAS = {
    'bins': [18, 22, 27, 32, 37, 42, 47, 52, 57, 62],
    'labels': ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62']
}

# Colunas obrigatórias
COLUNAS_OBRIGATORIAS = [
    'Nome', 'CPF', 'Idade', 'Cargo', 
    'Descrição da Unidade de Trabalho', 'Data Nascimento'
]

# Colunas para exibição na tabela detalhada
COLUNAS_EXIBICAO = [
    'Nome', 'CPF', 'Data Nascimento', 'Idade',
    'Código da Unidade de Trabalho',
    'Descrição da Unidade de Trabalho',
    'Cargo', 'Data Início',
    'Recebe Abono Permanência'
]


class DataLoader:
    """Classe aprimorada para carregar e processar os dados do CSV"""
    
    EXPECTED_COLUMNS = [
        'ID', 'Nome', 'RG', 'CPF', 'Data Nascimento', 'Idade', 'Órgão',
        'Código da Unidade de Trabalho', 'Descrição da Unidade de Trabalho',
        'Cargo', 'Função', 'Espec. Função', 'Data Início', 'Tipo Empregado',
        'Tipo Provimento', 'Recebe Abono Permanência', 'Categoria do Trabalhador',
        'Regime Trabalhista', 'Regime Previdenciário', 'Plano de Segregação da Massa',
        'Sujeito ao Teto do RGPS', 'UF-Cidade'
    ]

    @staticmethod
    @st.cache_data(ttl=3600, show_spinner=False)
    def load_data(file) -> pd.DataFrame:
        """
        Carrega e processa o arquivo CSV com tratamento de erros aprimorado
        
        Args:
            file: Arquivo CSV carregado
            
        Returns:
            DataFrame processado ou None em caso de erro
        """
        try:
            with st.spinner("Carregando e processando dados..."):
                # Detecta o encoding automaticamente
                encodings = ['cp1252', 'utf-8', 'latin1']
                
                # Tenta diferentes encodings
                for encoding in encodings:
                    try:
                        # Define tipos de dados para todas as colunas
                        dtype_dict = {col: str for col in DataLoader.EXPECTED_COLUMNS}
                        
                        # Carrega o CSV pulando linhas de metadados
                        df = pd.read_csv(
                            file,
                            encoding=encoding,
                            sep=';',
                            dtype=dtype_dict,
                            skiprows=7,
                            on_bad_lines='skip'
                        )
                        
                        logger.info(f"Arquivo CSV carregado com sucesso usando encoding {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Não foi possível decodificar o arquivo CSV com os encodings disponíveis")
                
                # Log das colunas disponíveis
                logger.info(f"Colunas encontradas no arquivo: {df.columns.tolist()}")
                
                # Verifica colunas mínimas
                colunas_faltantes = [col for col in COLUNAS_OBRIGATORIAS if col not in df.columns]
                if colunas_faltantes:
                    raise ValueError(f"Colunas obrigatórias faltando: {colunas_faltantes}")
                
                # Converte as colunas de data após carregar o DataFrame
                date_columns = ['Data Nascimento', 'Data Início']
                for col in date_columns:
                    if col in df.columns:
                        try:
                            # Primeiro, tenta verificar o formato analisando a primeira célula não nula
                            sample_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
                            
                            # Detecta o formato da data
                            if isinstance(sample_value, str) and '/' in sample_value and sample_value.count('/') == 2:
                                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
                            else:
                                # Tenta outros formatos comuns
                                date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']
                                for fmt in date_formats:
                                    try:
                                        df[col] = pd.to_datetime(df[col], format=fmt, errors='coerce')
                                        # Verifica se a conversão foi bem-sucedida
                                        if not pd.isna(df[col]).all():
                                            logger.info(f"Coluna {col} convertida com formato {fmt}")
                                            break
                                    except:
                                        continue
                        except Exception as e:
                            logger.warning(f"Não foi possível converter coluna {col} para datetime: {str(e)}")
                            # Garante que a coluna existe mas como objeto string, não como datetime
                            df[col] = df[col].astype(str)
                
                # Limpa e processa os dados
                df = DataLoader._process_dataframe(df)
                
                # Tempo de serviço - calcula usando a data atual e Data Início
                if 'Data Início' in df.columns:
                    try:
                        # Verifica se a coluna Data Início é realmente do tipo datetime
                        if pd.api.types.is_datetime64_any_dtype(df['Data Início']):
                            # Calcula diferença em dias e converte para anos
                            hoje = pd.Timestamp(datetime.now())
                            df['Tempo de Serviço (Anos)'] = df['Data Início'].apply(
                                lambda x: (hoje - x).days / 365.25 if pd.notnull(x) else None
                            ).round(1)
                        else:
                            # Se não for do tipo datetime, tenta converter novamente
                            df['Data Início'] = pd.to_datetime(df['Data Início'], errors='coerce')
                            
                            # Verifica se a conversão foi bem-sucedida
                            if not pd.isna(df['Data Início']).all():
                                hoje = pd.Timestamp(datetime.now())
                                df['Tempo de Serviço (Anos)'] = df['Data Início'].apply(
                                    lambda x: (hoje - x).days / 365.25 if pd.notnull(x) else None
                                ).round(1)
                            else:
                                logger.warning("Não foi possível converter 'Data Início' para calcular tempo de serviço")
                                df['Tempo de Serviço (Anos)'] = np.nan
                                
                        # Limita os valores e preenche os NaN
                        df['Tempo de Serviço (Anos)'] = df['Tempo de Serviço (Anos)'].fillna(0).clip(0, 40)
                        
                    except Exception as e:
                        logger.error(f"Erro ao calcular tempo de serviço: {str(e)}")
                        df['Tempo de Serviço (Anos)'] = np.nan
                
                return df
                
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {str(e)}", exc_info=True)
            st.error(f"Erro ao carregar dados: {str(e)}")
            return None

    @staticmethod
    def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Processa e limpa o DataFrame com melhorias
        
        Args:
            df: DataFrame a ser processado
            
        Returns:
            DataFrame processado
        """
        try:
            # Corrige deslocamento de colunas e formatos
            for col in df.columns:
                if isinstance(df[col].iloc[0], str):
                    df[col] = df[col].str.replace('; ', ';', regex=False)
                    df[col] = df[col].str.replace(';;', ';', regex=False)

            # Remove linhas totalmente vazias
            df = df.dropna(how='all')
            
            # Processa a coluna de idade
            try:
                if 'Idade' in df.columns:
                    # Limpa a coluna removendo espaços e substituindo vírgulas por pontos
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
            
            # Adiciona formato visual para CPF
            df['CPF_formatado'] = df['CPF'].apply(
                lambda x: f"{x[:3]}.{x[3:6]}.{x[6:9]}-{x[9:]}" if len(x) == 11 else x
            )
            
            # Limpa espaços extras em colunas de texto
            text_columns = df.select_dtypes(include=['object']).columns
            for col in text_columns:
                df[col] = df[col].str.strip()
            
            # Extrai cidade da coluna UF-Cidade
            if 'UF-Cidade' in df.columns:
                try:
                    # Padrão esperado: "PR-CURITIBA"
                    df[['UF', 'Cidade']] = df['UF-Cidade'].str.split('-', n=1, expand=True)
                except:
                    # Fallback caso o padrão não seja consistente
                    df['UF'] = 'PR'  # Assume PR como padrão
                    df['Cidade'] = df['UF-Cidade'].copy()
            
            # Garante ordem das colunas conforme esperado
            expected_cols = [col for col in DataLoader.EXPECTED_COLUMNS if col in df.columns]
            additional_cols = [col for col in df.columns if col not in expected_cols]
            df = df[expected_cols + additional_cols]
            
            return df
        except Exception as e:
            logger.error(f"Erro ao processar DataFrame: {str(e)}")
            raise


class DataProcessor:
    """Classe para processamento avançado e transformação de dados"""
    
    @staticmethod
    def create_age_groups(df: pd.DataFrame) -> pd.DataFrame:
        """
        Cria faixas etárias no DataFrame
        
        Args:
            df: DataFrame com coluna 'Idade'
            
        Returns:
            DataFrame com coluna 'faixa_etaria' adicionada
        """
        df_copy = df.copy()
        df_copy['faixa_etaria'] = pd.cut(
            df_copy['Idade'], 
            bins=FAIXAS_ETARIAS['bins'], 
            labels=FAIXAS_ETARIAS['labels']
        )
        return df_copy
    
    @staticmethod
    def aggregate_by_unit(df: pd.DataFrame) -> pd.DataFrame:
        """
        Agrega dados por unidade
        
        Args:
            df: DataFrame com dados de bombeiros
            
        Returns:
            DataFrame agregado por unidade
        """
        if 'Descrição da Unidade de Trabalho' not in df.columns:
            logger.error("Coluna 'Descrição da Unidade de Trabalho' não encontrada")
            return pd.DataFrame()
            
        # Agrega contagem por unidade
        unit_agg = df.groupby('Descrição da Unidade de Trabalho').agg(
            contagem=('Nome', 'count'),
            idade_media=('Idade', 'mean'),
            idade_min=('Idade', 'min'),
            idade_max=('Idade', 'max')
        ).reset_index()
        
        # Adiciona porcentagem do total
        unit_agg['porcentagem'] = (unit_agg['contagem'] / unit_agg['contagem'].sum() * 100).round(1)
        
        # Arredonda idade média
        unit_agg['idade_media'] = unit_agg['idade_media'].round(1)
        
        return unit_agg.sort_values('contagem', ascending=False)
    
    @staticmethod
    def create_retirement_candidates(df: pd.DataFrame) -> pd.DataFrame:
        """
        Identifica candidatos à aposentadoria (idade > 50 ou recebe abono)
        
        Args:
            df: DataFrame com dados de bombeiros
            
        Returns:
            DataFrame com candidatos à aposentadoria
        """
        cond_idade = df['Idade'] > 50
        cond_abono = df.get('Recebe Abono Permanência', 'NÃO').str.upper() == 'SIM'
        
        candidates = df[cond_idade | cond_abono].copy()
        candidates['Motivo'] = 'Idade > 50'
        candidates.loc[cond_abono, 'Motivo'] = 'Recebe Abono'
        candidates.loc[cond_idade & cond_abono, 'Motivo'] = 'Ambos'
        
        return candidates


class DataValidator:
    """Classe aprimorada para validação dos dados"""
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> bool:
        """
        Valida o DataFrame carregado com verificações aprimoradas
        
        Args:
            df: DataFrame a ser validado
            
        Returns:
            bool: Resultado da validação
        """
        if df is None or df.empty:
            st.error("DataFrame vazio ou não carregado corretamente")
            return False
            
        # Verifica colunas obrigatórias
        missing_columns = [col for col in COLUNAS_OBRIGATORIAS if col not in df.columns]
        if missing_columns:
            st.error(f"Colunas obrigatórias faltando: {missing_columns}")
            return False
        
        # Verifica se há dados suficientes
        if len(df) < 10:
            st.warning("O conjunto de dados contém poucos registros. Os resultados podem não ser representativos.")
        
        # Verifica valores únicos em colunas chave
        if df['CPF'].duplicated().any():
            duplicated_cpfs = df[df['CPF'].duplicated(keep=False)]
            st.warning(f"Existem {len(duplicated_cpfs)} CPFs duplicados nos dados")
            
        # Verifica distribuição de idades
        idade_stats = df['Idade'].describe()
        # Já filtramos idades fora do intervalo no processamento, isso é só uma verificação adicional
        if idade_stats['min'] < 18 or idade_stats['max'] > 62:
            st.warning(f"Existem idades fora do intervalo esperado (18-62): Min={idade_stats['min']}, Max={idade_stats['max']}")
        
        # Verifica valores nulos em colunas importantes
        for col in COLUNAS_OBRIGATORIAS:
            null_count = df[col].isna().sum()
            if null_count > 0:
                st.warning(f"Coluna '{col}' contém {null_count} valores nulos")
                
        # Verificações específicas de qualidade
        if 'Data Nascimento' in df.columns and df['Data Nascimento'].isna().sum() > 0:
            st.warning(f"{df['Data Nascimento'].isna().sum()} registros sem data de nascimento")
        
        # Verificação de datas de início
        if 'Data Início' in df.columns:
            future_dates = df[df['Data Início'] > datetime.now()]
            if not future_dates.empty:
                st.warning(f"Encontrados {len(future_dates)} registros com data de início no futuro")
        
        return True
        

class ChartManager:
    """Gerenciador aprimorado de gráficos do dashboard"""
    
    @staticmethod
    def create_age_chart(df: pd.DataFrame, cargo_filter: Optional[str] = None) -> go.Figure:
        """
        Cria gráfico de distribuição de idade com melhorias visuais
        
        Args:
            df: DataFrame com dados
            cargo_filter: Filtro opcional por cargo
            
        Returns:
            Figura Plotly
        """
        try:
            if cargo_filter and cargo_filter != "Todos":
                df = df[df['Cargo'] == cargo_filter]
            
            # Cria faixas etárias
            df_with_age_groups = DataProcessor.create_age_groups(df)
            
            # Contagem por faixa etária
            idade_counts = df_with_age_groups['faixa_etaria'].value_counts().sort_index()
            
            # Cria figura interativa com cores personalizadas
            fig = go.Figure(go.Bar(
                x=list(idade_counts.index),
                y=idade_counts.values,
                marker=dict(
                    color=idade_counts.values,
                    colorscale=[[0, CORES_PADRAO['terciaria']], [1, CORES_PADRAO['primaria']]],
                    colorbar=dict(title="Contagem")
                ),
                text=idade_counts.values,
                textposition='auto',
                hovertemplate='Faixa etária: %{x}<br>Quantidade: %{y}<extra></extra>',
            ))
            
            fig.update_layout(
                title={
                    'text': f"Distribuição por Idade{' - ' + cargo_filter if cargo_filter and cargo_filter != 'Todos' else ''}",
                    'font': {'size': 20}
                },
                xaxis_title="Faixa Etária",
                yaxis_title="Quantidade",
                showlegend=False,
                plot_bgcolor=CORES_PADRAO['fundo'],
                paper_bgcolor=CORES_PADRAO['fundo'],
                font=dict(color=CORES_PADRAO['texto']),
                height=400,
                margin=dict(t=50, b=50, l=50, r=20),
                hovermode='closest'
            )
            
            # Adiciona estatísticas no gráfico
            stats_text = f"<b>Média: {df['Idade'].mean():.1f} anos</b><br>"
            stats_text += f"<b>Mediana: {df['Idade'].median():.1f} anos</b><br>"
            stats_text += f"<b>Mín: {df['Idade'].min():.0f} | Máx: {df['Idade'].max():.0f} anos</b>"
            
            fig.add_annotation(
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                text=stats_text,
                showarrow=False,
                font=dict(size=12),
                align="left",
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#CCCCCC",
                borderwidth=1,
                borderpad=4
            )
            
            return fig
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de idade: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def create_cargo_chart(df: pd.DataFrame) -> go.Figure:
        """
        Cria gráfico de distribuição por cargo com melhorias visuais
        
        Args:
            df: DataFrame com dados
            
        Returns:
            Figura Plotly
        """
        try:
            cargo_counts = df['Cargo'].value_counts()
            
            # Reordena conforme a ordem definida
            ordered_cargos = [cargo for cargo in ORDEM_CARGOS if cargo in cargo_counts.index and cargo != "Todos"]
            cargo_counts = cargo_counts.reindex(ordered_cargos)
            
            # Define cores dinâmicas baseadas na contagem
            max_count = cargo_counts.max()
            colors = [CORES_PADRAO['secundaria'] if c < max_count*0.5 else CORES_PADRAO['destaque'] for c in cargo_counts.values]
            
            fig = go.Figure(go.Bar(
                x=cargo_counts.values,
                y=cargo_counts.index,
                orientation='h',
                marker_color=colors,
                text=cargo_counts.values,
                textposition='auto',
                hovertemplate='Cargo: %{y}<br>Quantidade: %{x}<extra></extra>',
            ))
            
            fig.update_layout(
                title={
                    'text': "Distribuição por Posto/Graduação",
                    'font': {'size': 20}
                },
                xaxis_title="Quantidade",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor=CORES_PADRAO['fundo'],
                paper_bgcolor=CORES_PADRAO['fundo'],
                font=dict(color=CORES_PADRAO['texto']),
                height=500,
                margin=dict(t=50, b=50, l=180, r=20),
                hovermode='closest'
            )
            
            # Adiciona linha de média
            media = cargo_counts.mean()
            fig.add_shape(
                type="line",
                x0=media,
                y0=-0.5,
                x1=media,
                y1=len(cargo_counts)-0.5,
                line=dict(
                    color="rgba(0,0,0,0.5)",
                    width=2,
                    dash="dash",
                )
            )
            
            fig.add_annotation(
                x=media+max_count*0.02,
                y=len(cargo_counts)-1,
                text=f"Média: {media:.1f}",
                showarrow=False,
                font=dict(size=10),
            )
            
            return fig
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de cargos: {str(e)}", exc_info=True)
            return None
            
    @staticmethod
    def create_unit_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
        """
        Cria gráfico das principais unidades
        
        Args:
            df: DataFrame com dados
            top_n: Número de principais unidades a exibir
            
        Returns:
            Figura Plotly
        """
        try:
            unit_counts = df['Descrição da Unidade de Trabalho'].value_counts().head(top_n)
            
            # Cores com gradiente
            colors = px.colors.sequential.Reds_r[:top_n]
            
            fig = go.Figure(go.Bar(
                x=unit_counts.values,
                y=unit_counts.index,
                orientation='h',
                marker_color=colors,
                text=unit_counts.values,
                textposition='outside',
                hovertemplate='Unidade: %{y}<br>Efetivo: %{x}<extra></extra>',
            ))
            
            fig.update_layout(
                title={
                    'text': f"Top {top_n} Unidades por Efetivo",
                    'font': {'size': 20}
                },
                xaxis_title="Quantidade",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor=CORES_PADRAO['fundo'],
                paper_bgcolor=CORES_PADRAO['fundo'],
                font=dict(color=CORES_PADRAO['texto']),
                height=500,
                margin=dict(t=50, b=50, l=180, r=20),
                hovermode='closest'
            )
            
            return fig
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de unidades: {str(e)}", exc_info=True)
            return None
            
    @staticmethod
    def create_service_time_chart(df: pd.DataFrame) -> go.Figure:
        """
        Cria gráfico de distribuição de tempo de serviço
        
        Args:
            df: DataFrame com coluna 'Tempo de Serviço (Anos)'
            
        Returns:
            Figura Plotly
        """
        try:
            if 'Tempo de Serviço (Anos)' not in df.columns:
                logger.error("Coluna 'Tempo de Serviço (Anos)' não encontrada")
                return None
                
            # Cria bins para tempo de serviço
            bins = [0, 5, 10, 15, 20, 25, 30, 35, 40]
            labels = ['0-5', '5-10', '10-15', '15-20', '20-25', '25-30', '30-35', '35-40']
            
            df['faixa_tempo'] = pd.cut(df['Tempo de Serviço (Anos)'], bins=bins, labels=labels)
            tempo_counts = df['faixa_tempo'].value_counts().sort_index()
            
            # Gráfico com Plotly Express para melhor visualização
            fig = px.bar(
                x=tempo_counts.index, 
                y=tempo_counts.values,
                color=tempo_counts.values,
                color_continuous_scale='Reds',
                labels={'x': 'Tempo de Serviço (Anos)', 'y': 'Quantidade'},
                text=tempo_counts.values
            )
            
            fig.update_traces(
                textposition='auto',
                hovertemplate='Tempo: %{x} anos<br>Quantidade: %{y}<extra></extra>'
            )
            
            fig.update_layout(
                title={
                    'text': "Distribuição por Tempo de Serviço",
                    'font': {'size': 20}
                },
                coloraxis_showscale=False,
                plot_bgcolor=CORES_PADRAO['fundo'],
                paper_bgcolor=CORES_PADRAO['fundo'],
                font=dict(color=CORES_PADRAO['texto']),
                height=400,
                margin=dict(t=50, b=50, l=50, r=20),
                hovermode='closest'
            )
            
            # Adiciona estatísticas no gráfico
            stats_text = f"<b>Média: {df['Tempo de Serviço (Anos)'].mean():.1f} anos</b><br>"
            stats_text += f"<b>Mediana: {df['Tempo de Serviço (Anos)'].median():.1f} anos</b>"
            
            fig.add_annotation(
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                text=stats_text,
                showarrow=False,
                font=dict(size=12),
                align="left",
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#CCCCCC",
                borderwidth=1,
                borderpad=4
            )
            
            return fig
        except Exception as e:
            logger.error(f"Erro ao criar gráfico de tempo de serviço: {str(e)}", exc_info=True)
            return None


class DashboardUI:
    """Gerenciador aprimorado da interface do usuário"""
    
    @staticmethod
    def setup_page():
        """Configura a página do Streamlit com estilo melhorado"""
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
                border-radius: 4px;
                border: 1px solid #d1d1d1;
                background-color: #f8f9fa;
                transition: all 0.3s;
            }
            .stButton > button:hover {
                background-color: #e9ecef;
                border-color: #bbb;
            }
            .stButton > button:active {
                background-color: #dc3545;
                color: white;
            }
            .metric-container {
                background-color: #f9f9f9;
                padding: 1.2rem;
                border-radius: 0.5rem;
                margin: 0.5rem 0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                transition: transform 0.3s;
            }
            .metric-container:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
            }
            .stTabs [data-baseweb="tab"] {
                height: 50px;
                white-space: pre-wrap;
                background-color: #f8f9fa;
                border-radius: 4px 4px 0 0;
                gap: 1px;
                padding-top: 10px;
                padding-bottom: 10px;
            }
            .stTabs [aria-selected="true"] {
                background-color: #dc3545;
                color: white;
            }
            /* Cor primária personalizada */
            .st-bq {
                background-color: #F44336;
            }
            .st-af {
                border-color: #F44336;
            }
            /* Estilo para DataFrames */
            .dataframe-container {
                padding: 10px;
                background-color: #f9f9f9;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            div[data-testid="stDataFrame"] div[data-testid="stTable"] {
                width: 100%;
            }
            /* Estilo para cabeçalho */
            .header-container {
                background-color: #F44336;
                padding: 2rem 1rem;
                margin-bottom: 2rem;
                border-radius: 5px;
                color: white;
                text-align: center;
            }
            .subheader {
                padding: 0.5rem;
                background-color: #ffebee;
                border-left: 5px solid #F44336;
                margin: 1rem 0;
            }
            /* Tooltip customizado */
            .tooltip {
                position: relative;
                display: inline-block;
                cursor: help;
            }
            .tooltip:hover::after {
                content: attr(data-tooltip);
                position: absolute;
                bottom: 125%;
                left: 50%;
                transform: translateX(-50%);
                background-color: #333;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                white-space: nowrap;
                z-index: 1;
                font-size: 12px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Adiciona cabeçalho estilizado
        with open(os.path.join(os.path.dirname(__file__), "README.md"), "r") as readme:
            title = readme.read().strip().split("\n")[0]
        
        st.markdown(
            f"""
            <div class="header-container">
                <h1>🚒 {title}</h1>
                <p>Visualização e análise de dados do efetivo do Corpo de Bombeiros Militar do Paraná</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

    @staticmethod
    def create_summary_metrics(df: pd.DataFrame):
        """
        Cria métricas resumidas com design aprimorado
        
        Args:
            df: DataFrame com dados
        """
        st.markdown('<h3 class="subheader">📊 Métricas Resumidas</h3>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Total de Efetivo",
                f"{len(df):,}".replace(",", ".")
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Idade Média",
                f"{df['Idade'].mean():.1f} anos",
                delta=f"{df['Idade'].mean() - 35:.1f}" if 35 else None,
                delta_color="inverse"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Quantidade de Unidades",
                f"{df['Descrição da Unidade de Trabalho'].nunique()}"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            if 'Tempo de Serviço (Anos)' in df.columns:
                st.metric(
                    "Tempo Médio de Serviço",
                    f"{df['Tempo de Serviço (Anos)'].mean():.1f} anos"
                )
            else:
                st.metric(
                    "Aposentadoria",
                    f"{len(df[df['Idade'] > 50])} (>50 anos)"
                )
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Linha adicional de métricas
        aposentados = len(df[df['Recebe Abono Permanência'] == 'SIM']) if 'Recebe Abono Permanência' in df.columns else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Efetivo Praças",
                f"{len(df[df['Cargo'].isin(['Soldado 2ª Classe', 'Soldado 1ª Classe', 'Cabo', '3º Sargento', '2º Sargento', '1º Sargento', 'Subtenente'])])}"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Efetivo Oficiais",
                f"{len(df[df['Cargo'].isin(['Aspirante a Oficial', '2º Tenente', '1º Tenente', 'Capitão', 'Major', 'Tenente Coronel', 'Coronel'])])}"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Efetivo Alunos",
                f"{len(df[df['Cargo'].str.contains('Aluno', na=False)])}"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Recebem Abono",
                f"{aposentados}",
                delta=f"{aposentados/len(df)*100:.1f}%" if len(df) > 0 else None
            )
            st.markdown('</div>', unsafe_allow_html=True)

    @staticmethod
    def create_cargo_filters():
        """Cria filtros de cargo com design aprimorado"""
        if 'cargo_selecionado' not in st.session_state:
            st.session_state.cargo_selecionado = "Todos"
            
        st.markdown('<h3 class="subheader">🔍 Filtrar por Posto/Graduação</h3>', unsafe_allow_html=True)
            
        # Dividir em categorias
        pracas = ["Soldado 2ª Classe", "Soldado 1ª Classe", "Cabo", "3º Sargento", "2º Sargento", "1º Sargento", "Subtenente"]
        oficiais = ["Aspirante a Oficial", "2º Tenente", "2º Tenente 6", "1º Tenente", "Capitão", "Major", "Tenente Coronel", "Coronel"]
        alunos = ["Aluno de 1º Ano", "Aluno de 2º Ano", "Aluno de 3º Ano"]
        
        # Botão de Todos
        if st.button("Todos", use_container_width=True, 
                     help="Clique para ver todos os militares sem filtro"):
            st.session_state.cargo_selecionado = "Todos"
        
        # Criar abas para as categorias
        tab_pracas, tab_oficiais, tab_alunos = st.tabs(["💪 Praças", "⭐ Oficiais", "👨‍🎓 Alunos"])
        
        with tab_pracas:
            cols = st.columns(len(pracas))
            for i, cargo in enumerate(pracas):
                if cols[i].button(cargo, key=f"btn_p_{i}", use_container_width=True):
                    st.session_state.cargo_selecionado = cargo if st.session_state.cargo_selecionado != cargo else "Todos"
        
        with tab_oficiais:
            cols = st.columns(len(oficiais))
            for i, cargo in enumerate(oficiais):
                if cols[i].button(cargo, key=f"btn_o_{i}", use_container_width=True):
                    st.session_state.cargo_selecionado = cargo if st.session_state.cargo_selecionado != cargo else "Todos"
        
        with tab_alunos:
            cols = st.columns(len(alunos))
            for i, cargo in enumerate(alunos):
                if cols[i].button(cargo, key=f"btn_a_{i}", use_container_width=True):
                    st.session_state.cargo_selecionado = cargo if st.session_state.cargo_selecionado != cargo else "Todos"
        
        # Exibe o filtro atual
        if st.session_state.cargo_selecionado != "Todos":
            st.info(f"🎯 Filtro atual: {st.session_state.cargo_selecionado}")

    @staticmethod
    def display_detailed_data(df: pd.DataFrame):
        """
        Exibe dados detalhados com filtros e estilo aprimorado
        
        Args:
            df: DataFrame com dados
        """
        st.markdown('<h3 class="subheader">📋 Dados Detalhados</h3>', unsafe_allow_html=True)
        
        # Guias para diferentes visualizações de dados
        tabs = st.tabs(["🔍 Pesquisa por Nome/CPF", "🏛️ Filtro por Unidade", "👴 Previsão de Aposentadorias"])
        
        with tabs[0]:
            # Filtro de pesquisa melhorado
            col1, col2 = st.columns([3, 1])
            
            with col1:
                search_term = st.text_input("🔍 Pesquisar por nome ou CPF:", "")
            
            with col2:
                search_type = st.selectbox(
                    "Tipo de busca:", 
                    ["Contém", "Começa com", "Termina com", "Exato"],
                    help="Define como a busca será realizada"
                )
            
            if search_term:
                if search_type == "Contém":
                    mask = (df['Nome'].str.contains(search_term, case=False, na=False) | 
                           df['CPF'].str.contains(search_term, na=False))
                elif search_type == "Começa com":
                    mask = (df['Nome'].str.startswith(search_term, na=False) | 
                           df['CPF'].str.startswith(search_term, na=False))
                elif search_type == "Termina com":
                    mask = (df['Nome'].str.endswith(search_term, na=False) | 
                           df['CPF'].str.endswith(search_term, na=False))
                else:  # Exato
                    mask = (df['Nome'].str.lower() == search_term.lower()) | (df['CPF'] == search_term)
                
                df_display = df[mask]
            else:
                df_display = df
                
            # Limite de registros por página
            pagina_atual = st.number_input(
                "Página:", 
                min_value=1, 
                max_value=max(1, len(df_display) // 10 + 1),
                value=1,
                help="Navegue entre as páginas de resultados"
            )
            registros_por_pagina = st.select_slider(
                "Registros por página:", 
                options=[10, 25, 50, 100],
                value=25,
                help="Escolha quantos registros exibir por página"
            )
            
            inicio = (pagina_atual - 1) * registros_por_pagina
            fim = inicio + registros_por_pagina
            
            # Seleciona colunas para exibição
            display_columns = [col for col in COLUNAS_EXIBICAO if col in df.columns]
            
            # Formata as colunas de data
            df_paginated = df_display[inicio:fim].copy()
            
            date_columns = [col for col in ['Data Nascimento', 'Data Início'] if col in df_paginated.columns]
            for col in date_columns:
                try:
                    # Verifica se a coluna é do tipo datetime antes de usar .dt
                    if pd.api.types.is_datetime64_any_dtype(df_paginated[col]):
                        df_paginated[col] = df_paginated[col].dt.strftime('%d/%m/%Y')
                    else:
                        # Tenta converter para datetime
                        temp = pd.to_datetime(df_paginated[col], errors='coerce')
                        # Se a conversão funcionar, formata a data
                        if not pd.isna(temp).all():
                            df_paginated[col] = temp.dt.strftime('%d/%m/%Y')
                except Exception as e:
                    logger.warning(f"Erro ao formatar coluna de data {col}: {str(e)}")
                    # Mantém a coluna como está se houver erro
            
            # Substitui CPF pela versão formatada se disponível
            if 'CPF_formatado' in df_paginated.columns and 'CPF' in display_columns:
                df_paginated['CPF'] = df_paginated['CPF_formatado']
            
            # Exibe o DataFrame com estatísticas
            st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
            st.dataframe(
                df_paginated[display_columns], 
                use_container_width=True, 
                height=400,
                hide_index=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.caption(f"Exibindo {min(len(df_display), registros_por_pagina)} de {len(df_display)} registros encontrados")
            
            # Botão de download
            if not df_display.empty:
                col1, col2 = st.columns([1, 1])
                with col1:
                    csv = df_display[display_columns].to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"dados_bombeiros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    # Cria Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_display[display_columns].to_excel(writer, index=False, sheet_name='Dados')
                        # Formatar planilha
                        workbook = writer.book
                        worksheet = writer.sheets['Dados']
                        header_format = workbook.add_format({'bold': True, 'bg_color': '#F44336', 'color': 'white'})
                        
                        # Formato para cabeçalho
                        for col_num, value in enumerate(df_display[display_columns].columns.values):
                            worksheet.write(0, col_num, value, header_format)
                    
                    excel_data = output.getvalue()
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_data,
                        file_name=f"dados_bombeiros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        with tabs[1]:
            # Filtro por unidade
            unidades = ["Todas"] + sorted(df['Descrição da Unidade de Trabalho'].unique().tolist())
            unidade_selecionada = st.selectbox("Selecione a Unidade:", unidades)
            
            if unidade_selecionada != "Todas":
                df_unidade = df[df['Descrição da Unidade de Trabalho'] == unidade_selecionada]
            else:
                df_unidade = df
            
            # Estatísticas da unidade
            if unidade_selecionada != "Todas":
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Efetivo na Unidade", f"{len(df_unidade)}")
                with col2:
                    st.metric("Idade Média", f"{df_unidade['Idade'].mean():.1f} anos")
                with col3:
                    st.metric("Oficiais/Praças", 
                             f"{len(df_unidade[df_unidade['Cargo'].isin(oficiais)])}/{len(df_unidade[df_unidade['Cargo'].isin(pracas)])}")
                
                # Distribuição por cargo na unidade
                cargo_counts = df_unidade['Cargo'].value_counts()
                fig = px.pie(
                    values=cargo_counts.values,
                    names=cargo_counts.index,
                    title=f"Distribuição por Cargo na {unidade_selecionada}",
                    color_discrete_sequence=px.colors.sequential.Reds
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Tabela da unidade
            st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
            st.dataframe(
                df_unidade[display_columns],
                use_container_width=True,
                height=400,
                hide_index=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tabs[2]:
            # Previsão de aposentadorias
            st.write("### Previsão de Aposentadorias")
            
            # Obter candidatos à aposentadoria
            retirement_candidates = DataProcessor.create_retirement_candidates(df)
            
            # Estatísticas
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Total de Potenciais Aposentados", 
                    f"{len(retirement_candidates)}",
                    delta=f"{len(retirement_candidates)/len(df)*100:.1f}% do efetivo" if len(df) > 0 else None
                )
            with col2:
                st.metric(
                    "Idade Média", 
                    f"{retirement_candidates['Idade'].mean():.1f} anos"
                )
            
            # Cria gráfico de distribuição
            motivo_counts = retirement_candidates['Motivo'].value_counts()
            fig = px.pie(
                values=motivo_counts.values,
                names=motivo_counts.index,
                title="Motivos para Potencial Aposentadoria",
                color_discrete_sequence=px.colors.sequential.Reds
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela de aposentadorias
            st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
            colunas_aposentadoria = display_columns + ['Motivo'] if 'Motivo' in retirement_candidates.columns else display_columns
            st.dataframe(
                retirement_candidates[colunas_aposentadoria],
                use_container_width=True,
                height=400,
                hide_index=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Download
            csv = retirement_candidates[colunas_aposentadoria].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Lista de Potenciais Aposentados",
                data=csv,
                file_name=f"aposentadorias_bombeiros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )


def main():
    """Função principal do dashboard aprimorado"""
    try:
        # Define hora de início para medir desempenho
        start_time = time.time()
        
        # Configura a página
        DashboardUI.setup_page()
        
        # Adiciona instruções rápidas
        with st.expander("ℹ️ Como utilizar este dashboard", expanded=False):
            st.markdown("""
                ### Instruções de Uso
                
                1. **Upload de Dados:** Faça o upload do arquivo CSV do Portal da Transparência.
                2. **Filtros:** Utilize os filtros de posto/graduação para refinar os dados.
                3. **Visualizações:** Explore os gráficos de distribuição por idade e cargo.
                4. **Pesquisa:** Utilize a aba de pesquisa para localizar bombeiros específicos.
                5. **Download:** Baixe os dados filtrados em formato CSV ou Excel.
                
                > **Dica:** Clique nos elementos dos gráficos para ver mais detalhes.
            """)
        
        # Upload de arquivo
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "📤 Upload do arquivo CSV do Portal da Transparência", 
                type="csv",
                help="Faça o upload do arquivo CSV exportado do Portal da Transparência"
            )
            
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("ℹ️ Ajuda para obter o arquivo", use_container_width=True):
                st.info("""
                    Para obter o arquivo CSV:
                    1. Acesse o [Portal da Transparência](https://www.transparencia.pr.gov.br/)
                    2. Vá para "Funcionalismo" > "Consulta de Remuneração"
                    3. Filtre por "Corpo de Bombeiros"
                    4. Clique em "Exportar" > "CSV"
                """)
        
        if uploaded_file is not None:
            try:
                # Carrega os dados com feedback visual
                with st.spinner("Carregando e processando dados..."):
                    df = DataLoader.load_data(uploaded_file)
                
                if df is not None and DataValidator.validate_dataframe(df):
                    # Criar métricas resumidas
                    DashboardUI.create_summary_metrics(df)
                    
                    # Criar filtros de cargo
                    DashboardUI.create_cargo_filters()
                
                    try:
                        # Aplicar filtro selecionado
                        if (hasattr(st.session_state, 'cargo_selecionado') and 
                            st.session_state.cargo_selecionado and 
                            st.session_state.cargo_selecionado != "Todos"):
                            
                            df_filtered = df[df['Cargo'] == st.session_state.cargo_selecionado]
                            st.markdown(
                                f"<h3 class='subheader'>📊 Efetivo Filtrado: {len(df_filtered):,.0f} de {len(df):,.0f} ({len(df_filtered)/len(df)*100:.1f}%)</h3>".replace(",", "."), 
                                unsafe_allow_html=True
                            )
                        else:
                            df_filtered = df
                            st.markdown(
                                f"<h3 class='subheader'>📊 Efetivo Total: {len(df):,.0f}</h3>".replace(",", "."), 
                                unsafe_allow_html=True
                            )
                    
                        # Criar gráficos em guias
                        tabs = st.tabs(["📈 Distribuição de Idade", "👮 Postos e Graduações", "🏢 Unidades", "⏱️ Tempo de Serviço"])
                        
                        with tabs[0]:
                            fig_idade = ChartManager.create_age_chart(
                                df_filtered,
                                st.session_state.cargo_selecionado if hasattr(st.session_state, 'cargo_selecionado') else None
                            )
                            if fig_idade:
                                st.plotly_chart(fig_idade, use_container_width=True)
                        
                        with tabs[1]:
                            fig_cargo = ChartManager.create_cargo_chart(df_filtered)
                            if fig_cargo:
                                selected_points = plotly_events(fig_cargo, click_event=True)
                                
                                # Permite clicar em um cargo para filtrar
                                if selected_points:
                                    if 'y' in selected_points[0]:
                                        cargo_index = int(selected_points[0]['pointIndex'])
                                        cargo_selecionado = fig_cargo.data[0].y[cargo_index]
                                        st.session_state.cargo_selecionado = cargo_selecionado
                                        st.experimental_rerun()
                        
                        with tabs[2]:
                            fig_unit = ChartManager.create_unit_chart(df_filtered)
                            if fig_unit:
                                st.plotly_chart(fig_unit, use_container_width=True)
                                
                                # Tabela com dados agregados por unidade
                                unit_data = DataProcessor.aggregate_by_unit(df_filtered)
                                if not unit_data.empty:
                                    st.markdown("### Detalhamento por Unidade")
                                    st.dataframe(
                                        unit_data,
                                        use_container_width=True,
                                        height=300,
                                        hide_index=True
                                    )
                        
                        with tabs[3]:
                            if 'Data Início' in df.columns:
                                fig_service = ChartManager.create_service_time_chart(df_filtered)
                                if fig_service:
                                    st.plotly_chart(fig_service, use_container_width=True)
                            else:
                                st.warning("Dados de tempo de serviço não disponíveis. A coluna 'Data Início' não foi encontrada no arquivo.")
                        
                        # Exibir dados detalhados
                        DashboardUI.display_detailed_data(df_filtered)
                        
                        # Exibe tempo de processamento
                        processing_time = time.time() - start_time
                        st.caption(f"Dashboard carregado em {processing_time:.2f} segundos | Dados atualizados em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                    
                    except Exception as e:
                        logger.error(f"Erro ao processar dados filtrados: {str(e)}", exc_info=True)
                        st.error(f"Erro ao processar dados filtrados: {str(e)}")
                        
                        # Exibe o rastreamento da exceção para facilitar a depuração
                        with st.expander("Detalhes técnicos do erro"):
                            st.code(traceback.format_exc())
            except Exception as e:
                # Captura erros específicos durante o carregamento
                logger.error(f"Erro ao processar o arquivo: {str(e)}", exc_info=True)
                st.error(f"Erro ao processar o arquivo: {str(e)}")
                
                # Dá dicas específicas com base no erro
                if "Can only use .dt accessor with datetimelike values" in str(e):
                    st.warning("Problema com formato de datas no arquivo. Verifique se o arquivo está no formato correto.")
                elif "No columns to parse from file" in str(e):
                    st.warning("O arquivo não contém colunas válidas. Verifique se o separador é ';' e se o arquivo não está corrompido.")
                elif "Encoding" in str(e) or "decode" in str(e).lower():
                    st.warning("Problema com a codificação do arquivo. Tente salvar o arquivo como UTF-8 ou Windows-1252 (CP1252).")
                
                # Exibe o rastreamento da exceção em um expander para ajudar na depuração
                with st.expander("Detalhes técnicos do erro (para suporte)"):
                    st.code(traceback.format_exc())
        else:
            # Sem arquivo, exibe mensagem e exemplo
            st.info("👆 Faça o upload do arquivo CSV do Portal da Transparência para começar a análise.")
            
            # Adiciona dicas de resolução de problemas
            with st.expander("💡 Dicas para resolução de problemas comuns"):
                st.markdown("""
                    ### Problemas comuns e soluções
                    
                    1. **Erro de encoding**: Se o dashboard mostrar erro de encoding, tente:
                       - Abrir o CSV no Excel e salvar novamente como CSV (separado por ponto e vírgula)
                       - Verificar se o encoding está como Windows-1252 (CP1252) ou UTF-8
                    
                    2. **Erro com datas**: Se houver problemas com formato de data:
                       - Verifique se as datas estão no formato DD/MM/AAAA
                       - Certifique-se que não há mistura de formatos no arquivo
                    
                    3. **Arquivo não reconhecido**: 
                       - Verifique se o separador é ponto e vírgula (;)
                       - Certifique-se que o arquivo é o CSV exportado do Portal da Transparência
                       
                    4. **Dashboard lento**:
                       - Tente usar um navegador mais recente
                       - Feche outras abas do navegador para liberar memória
                """)
            
            # Exemplo de visualização com dados fictícios
            with st.expander("🔍 Ver exemplo com dados fictícios", expanded=False):
                st.write("Exemplo de visualização com 50 registros fictícios:")
                
                # Gera dados de exemplo
                np.random.seed(42)
                cargos = ["Soldado 1ª Classe", "Cabo", "3º Sargento", "Tenente", "Capitão"]
                unidades = ["1º GB - Curitiba", "2º GB - Ponta Grossa", "3º GB - Londrina", "4º GB - Cascavel"]
                
                exemplo_df = pd.DataFrame({
                    'Nome': [f"Bombeiro Exemplo {i}" for i in range(1, 51)],
                    'CPF': [f"{np.random.randint(100, 999)}.{np.random.randint(100, 999)}.{np.random.randint(100, 999)}-{np.random.randint(10, 99)}" for _ in range(50)],
                    'Idade': np.random.randint(25, 55, 50),
                    'Cargo': np.random.choice(cargos, 50),
                    'Descrição da Unidade de Trabalho': np.random.choice(unidades, 50),
                    'Data Nascimento': [datetime.now() - pd.Timedelta(days=np.random.randint(9000, 20000)) for _ in range(50)],
                    'Data Início': [datetime.now() - pd.Timedelta(days=np.random.randint(1000, 8000)) for _ in range(50)],
                    'Tempo de Serviço (Anos)': np.random.randint(2, 30, 50) / 10 * 10,
                    'Código da Unidade de Trabalho': np.random.randint(1000, 9999, 50),
                    'Recebe Abono Permanência': np.random.choice(['SIM', 'NÃO'], 50, p=[0.2, 0.8])
                })
                
                # Exibe gráficos de exemplo
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_idade = ChartManager.create_age_chart(exemplo_df)
                    if fig_idade:
                        st.plotly_chart(fig_idade, use_container_width=True)
                
                with col2:
                    fig_cargo = ChartManager.create_cargo_chart(exemplo_df)
                    if fig_cargo:
                        st.plotly_chart(fig_cargo, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Erro geral no dashboard: {str(e)}", exc_info=True)
        st.error(f"Ocorreu um erro no dashboard: {str(e)}")
        
        # Exibe o rastreamento da exceção em um expander para ajudar na depuração
        with st.expander("Detalhes técnicos do erro (para suporte)"):
            st.code(traceback.format_exc())
        
        st.warning("Por favor, recarregue a página e tente novamente. Se o erro persistir, verifique o formato do arquivo CSV.")

if __name__ == "__main__":
    main()
