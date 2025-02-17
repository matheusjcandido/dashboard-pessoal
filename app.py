import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DashboardConfig:
    """Configuration class for dashboard settings"""
    page_title: str = "Dashboard CBMPR"
    page_icon: str = "🚒"
    layout: str = "wide"
    initial_sidebar_state: str = "expanded"
    idade_min: int = 18
    idade_max: int = 62

class DataProcessor:
    """Class to handle data processing operations"""
    
    @staticmethod
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def load_data(file) -> Optional[pd.DataFrame]:
        """Load and process CSV data with better error handling and caching"""
        try:
            column_names = [
                'ID', 'Nome', 'RG', 'CPF', 'Data Nascimento', 'Idade', 'Órgão',
                'Código da Unidade de Trabalho', 'Descrição da Unidade de Trabalho',
                'Cargo', 'Função', 'Espec. Função', 'Data Início'
            ]
            
            df = pd.read_csv(
                file,
                encoding='cp1252',
                skiprows=9,
                header=None,
                names=column_names,
                sep=';',
                dtype={col: str for col in column_names},
                on_bad_lines='skip'
            )
            
            return DataProcessor._clean_dataframe(df)
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return None

    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare DataFrame"""
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Clean string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        # Convert age to numeric
        df['Idade'] = pd.to_numeric(df['Idade'].str.replace(',', '.'), errors='coerce')
        
        # Filter valid ages
        df = df[df['Idade'].between(DashboardConfig.idade_min, DashboardConfig.idade_max)]
        
        return df

class ChartManager:
    """Class to handle chart creation and updates"""
    
    @staticmethod
    def create_age_distribution(df: pd.DataFrame, idade_column: str, cargo_filter: Optional[str] = None) -> go.Figure:
        """Create age distribution chart with improved styling"""
        try:
            filtered_df = df[df['Cargo'] == cargo_filter] if cargo_filter else df
            
            bins = list(range(18, 63, 5))
            labels = [f'{bins[i]}-{bins[i+1]-1}' for i in range(len(bins)-1)]
            
            filtered_df['faixa_etaria'] = pd.cut(filtered_df[idade_column], bins=bins, labels=labels)
            idade_counts = filtered_df['faixa_etaria'].value_counts().sort_index()
            
            fig = go.Figure(go.Bar(
                x=list(idade_counts.index),
                y=idade_counts.values,
                marker_color='rgba(255, 0, 0, 0.7)',
                text=idade_counts.values,
                textposition='auto',
            ))
            
            fig.update_layout(
                title=dict(
                    text=f"Distribuição por Idade{' - ' + cargo_filter if cargo_filter else ''}",
                    font=dict(size=20)
                ),
                xaxis_title="Faixa Etária",
                yaxis_title="Quantidade",
                template="plotly_white",
                height=400,
                hovermode='x'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating age chart: {str(e)}")
            return None

class DashboardUI:
    """Class to handle UI components and layout"""
    
    def __init__(self):
        self.config = DashboardConfig()
        self.setup_page_config()
        
    def setup_page_config(self):
        """Configure page settings"""
        st.set_page_config(
            page_title=self.config.page_title,
            page_icon=self.config.page_icon,
            layout=self.config.layout,
            initial_sidebar_state=self.config.initial_sidebar_state
        )
        
        self.apply_custom_css()
    
    @staticmethod
    def apply_custom_css():
        """Apply custom CSS styling"""
        st.markdown("""
            <style>
            .stApp {
                max-width: 1200px;
                margin: 0 auto;
            }
            .metric-card {
                background-color: #f0f2f6;
                border-radius: 0.5rem;
                padding: 1rem;
                margin: 0.5rem 0;
            }
            </style>
        """, unsafe_allow_html=True)

def main():
    """Main application entry point"""
    dashboard = DashboardUI()
    data_processor = DataProcessor()
    
    st.title("Dashboard - Corpo de Bombeiros Militar do Paraná")
    
    uploaded_file = st.file_uploader("Upload de Dados", type="csv")
    
    if uploaded_file:
        df = data_processor.load_data(uploaded_file)
        
        if df is not None:
            # Initialize session state if needed
            if 'cargo_selecionado' not in st.session_state:
                st.session_state.cargo_selecionado = None
            
            # Create dashboard components
            charts = ChartManager()
            
            # Display metrics and charts
            col1, col2 = st.columns(2)
            
            with col1:
                fig_idade = charts.create_age_distribution(
                    df,
                    'Idade',
                    st.session_state.cargo_selecionado
                )
                if fig_idade:
                    st.plotly_chart(fig_idade, use_container_width=True)
            
            # Add more dashboard components here...

if __name__ == "__main__":
    main()
