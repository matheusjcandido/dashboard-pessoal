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
    return df

def create_age_chart(df, selected_cargo=None):
    # Filtrar por cargo se selecionado
    if selected_cargo:
        df = df[df['CARGO'].isin(selected_cargo)]
    
    # Criar faixas etárias
    bins = [17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
    labels = ['18-22', '23-27', '28-32', '33-37', '38-42', '43-47', '48-52', '53-57', '58-62']
    df['faixa_etaria'] = pd.cut(df['IDADE'], bins=bins, labels=labels, right=True)
    
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

def create_cargo_chart(df, selected_age_ranges=None):
    # Filtrar por faixa etária se selecionado
    if selected_age_ranges:
        df = df[df['faixa_etaria'].isin(selected_age_ranges)]
    
    cargo_counts = df['CARGO'].value_counts()
    
    fig_cargo = px.bar(
        x=cargo_counts.values,
        y=cargo_counts.index,
        orientation='h',
        labels={'x': 'Quantidade', 'y': 'Posto/Graduação'},
        title="Distribuição por Posto/Graduação"
    )
    fig_cargo.update_traces(
        marker_color='gold',
        customdata=[cargo_counts.index],
        hovertemplate="<b>%{y}</b><br>" +
                     "Quantidade: %{x}<br>" +
                     "<extra></extra>"
    )
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
        
        # Inicializar session state para filtros
        if 'selected_cargo' not in st.session_state:
            st.session_state.selected_cargo = []
        if 'selected_age_ranges' not in st.session_state:
            st.session_state.selected_age_ranges = []

        # Mostrar efetivo total
        st.header(f"Efetivo Total: {len(df):,}")

        # Criar colunas para os gráficos
        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de idade
            fig_idade = create_age_chart(df, st.session_state.selected_cargo)
            
            # Adicionar callback para cliques no gráfico
            selected_ages = plotly_events(fig_idade, click_event=True)
            if selected_ages:
                clicked_age = selected_ages[0]['x']
                if clicked_age in st.session_state.selected_age_ranges:
                    st.session_state.selected_age_ranges.remove(clicked_age)
                else:
                    st.session_state.selected_age_ranges.append(clicked_age)

        with col2:
            # Gráfico de cargo
            fig_cargo = create_cargo_chart(df, st.session_state.selected_age_ranges)
            
            # Adicionar callback para cliques no gráfico
            selected_cargos = plotly_events(fig_cargo, click_event=True)
            if selected_cargos:
                clicked_cargo = selected_cargos[0]['y']
                if clicked_cargo in st.session_state.selected_cargo:
                    st.session_state.selected_cargo.remove(clicked_cargo)
                else:
                    st.session_state.selected_cargo.append(clicked_cargo)

        # Aplicar filtros aos dados
        filtered_df = df.copy()
        if st.session_state.selected_cargo:
            filtered_df = filtered_df[filtered_df['CARGO'].isin(st.session_state.selected_cargo)]
        if st.session_state.selected_age_ranges:
            filtered_df = filtered_df[filtered_df['faixa_etaria'].isin(st.session_state.selected_age_ranges)]

        # Dados Detalhados
        st.subheader("Dados Detalhados")
        cols_to_show = ['NOME', 'CARGO', 'IDADE', 'ÓRGÃO', 'UNIDADE DE TRABALHO']
        
        # Ordenar por nome
        filtered_df = filtered_df.sort_values('NOME')
        
        # Mostrar dados com paginação
        st.dataframe(
            filtered_df[cols_to_show],
            use_container_width=True,
            height=400  # Altura fixa para permitir rolagem
        )
        
        # Adicionar informação sobre registros mostrados
        st.write(f"Mostrando {len(filtered_df)} registros de um total de {len(df)}")

        # Botão de download dos dados filtrados
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download dos dados filtrados",
            data=csv,
            file_name=f"dados_bombeiros_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
