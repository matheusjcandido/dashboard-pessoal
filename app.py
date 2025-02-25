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
        # Primeiro, vamos tentar ler o arquivo como texto para identificar possíveis problemas
        conteudo_arquivo = arquivo.read()
        arquivo.seek(0)  # Resetar o ponteiro do arquivo
        
        # Tentativa de determinar o delimiter
        # Vamos ler as primeiras linhas e verificar se há mais vírgulas ou ponto-e-vírgulas
        import io
        amostra = conteudo_arquivo[:2000].decode('cp1252', errors='replace')
        virgulas = amostra.count(',')
        pontovirgulas = amostra.count(';')
        tabs = amostra.count('\t')
        
        # Determinar qual delimitador usar
        if pontovirgulas > virgulas and pontovirgulas > tabs:
            delimitador = ';'
        elif tabs > virgulas and tabs > pontovirgulas:
            delimitador = '\t'
        else:
            delimitador = ','
            
        st.sidebar.info(f"Delimitador detectado: {delimitador}")
        
        # Tentativa com engine python para maior flexibilidade
        df = pd.read_csv(
            io.StringIO(conteudo_arquivo.decode('cp1252', errors='replace')),
            delimiter=delimitador,
            engine='python',  # Engine mais tolerante a erros
            on_bad_lines='skip',  # Pular linhas com problemas
            quoting=3,  # QUOTE_NONE - não considerar aspas como delimitadores especiais
            dtype=str,  # Tratar TODAS as colunas como string inicialmente
            skiprows=range(7)  # Pular as linhas de metadados
        )
        
        # Remover linhas vazias
        df = df.dropna(how='all')
        
        # Identificar colunas relevantes
        # Para encontrar a coluna de cabeçalho, buscar padrões específicos
        cabecalho_detectado = False
        for i, row in df.iterrows():
            # Verificar se esta linha parece um cabeçalho (contém palavras-chave esperadas)
            if any(col for col in row if isinstance(col, str) and ('ID' in col or 'Nome' in col)):
                # Usar esta linha como cabeçalho
                cabecalho = row.values
                df = df.iloc[i+1:].reset_index(drop=True)  # Pegar dados a partir da próxima linha
                # Atribuir novos nomes às colunas
                df.columns = cabecalho
                cabecalho_detectado = True
                break
        
        if not cabecalho_detectado:
            st.warning("Cabeçalho não detectado automaticamente. Usando a primeira linha de dados.")
        
        # Limpar nomes das colunas
        df.columns = [col.strip() if isinstance(col, str) else f"Col_{i}" for i, col in enumerate(df.columns)]
        
        # Remover colunas que não interessam (usando verificação por substring para maior flexibilidade)
        colunas_excluir = []
        for col in df.columns:
            if any(termo in col.lower() if isinstance(col, str) else False for termo in 
                  ['rgao', 'func', 'espec', 'empregado', 'provimento', 'categoria', 'trabalhista', 
                   'previdenci', 'segrega', 'rgps', 'cidade', 'unnamed']):
                colunas_excluir.append(col)
        
        # Excluir colunas identificadas e colunas vazias
        df = df.drop(columns=[col for col in colunas_excluir if col in df.columns])
        
        # Remover colunas sem cabeçalho ou com cabeçalho em branco
        colunas_sem_nome = [col for col in df.columns if not isinstance(col, str) or col.strip() == '']
        if colunas_sem_nome:
            df = df.drop(columns=colunas_sem_nome)
        
        # Identificar e renomear colunas importantes
        nome_col_idade = None
        nome_col_cargo = None
        nome_col_unidade = None
        nome_col_abono = None
        
        for col in df.columns:
            if isinstance(col, str):
                col_lower = col.lower()
                if 'idade' in col_lower:
                    nome_col_idade = col
                elif 'cargo' in col_lower or 'posto' in col_lower or 'gradua' in col_lower:
                    nome_col_cargo = col
                elif 'unidade' in col_lower and 'trabalho' in col_lower:
                    nome_col_unidade = col
                elif 'abono' in col_lower or 'perman' in col_lower:
                    nome_col_abono = col
        
        # Garantir que as colunas necessárias existam
        if nome_col_idade:
            # Converter idade para numérico preservando só os dígitos
            df['Idade'] = df[nome_col_idade].str.extract('(\d+)', expand=False)
            df['Idade'] = pd.to_numeric(df['Idade'], errors='coerce')
            if nome_col_idade != 'Idade':
                df = df.drop(columns=[nome_col_idade])
        else:
            df['Idade'] = np.nan
            st.warning("Coluna de idade não encontrada no arquivo")
        
        if nome_col_cargo:
            df = df.rename(columns={nome_col_cargo: 'Cargo'})
        else:
            df['Cargo'] = "Não informado"
            st.warning("Coluna de cargo não encontrada no arquivo")
        
        if nome_col_unidade:
            df = df.rename(columns={nome_col_unidade: 'Descrição da Unidade de Trabalho'})
        else:
            df['Descrição da Unidade de Trabalho'] = "Não informado"
            st.warning("Coluna de unidade de trabalho não encontrada no arquivo")
        
        if nome_col_abono:
            df = df.rename(columns={nome_col_abono: 'Recebe Abono Permanência'})
        else:
            df['Recebe Abono Permanência'] = "N"
            st.warning("Coluna de abono permanência não encontrada no arquivo")
        
        # Não converter datas - deixar como string conforme solicitado
        # Tratar colunas de data (Data Nascimento) como string sem conversão
        
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
        df['Ordem_Hierarquica'] = df['Cargo'].map(lambda x: hierarquia.get(x, 999) if pd.notnull(x) else 999)
        
        # Exibir informações sobre a importação
        st.sidebar.success(f"Dados carregados com sucesso: {len(df)} registros")
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        st.error("Detalhes do erro: Verifique se o arquivo está no formato correto.")
        return pd.DataFrame()

# Função para gerar estatísticas
def gerar_estatisticas(df):
    total_efetivo = len(df)
    
    # Verificar se a coluna de idade existe e tem dados válidos
    if 'Idade' in df.columns:
        try:
            # Converter para numérico, ignorando erros
            idades_validas = pd.to_numeric(df['Idade'], errors='coerce').dropna()
            
            if len(idades_validas) > 0:
                media_idade = idades_validas.mean()
            else:
                media_idade = None
        except Exception as e:
            st.warning(f"Erro ao calcular estatísticas de idade: {str(e)}")
            media_idade = None
    else:
        media_idade = None
    
    return {
        'total_efetivo': total_efetivo,
        'media_idade': media_idade
    }

# Função para criar gráfico de distribuição por idade
def grafico_distribuicao_idade(df):
    # Verificar se há dados de idade disponíveis
    df_idade = df.dropna(subset=['Idade'])
    
    if len(df_idade) == 0:
        # Criar um gráfico vazio com mensagem se não houver dados
        fig = go.Figure()
        fig.add_annotation(
            text="Dados de idade não disponíveis",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=VERMELHO, size=16)
        )
        fig.update_layout(title_text="Distribuição por Faixa Etária")
        return fig
    
    # Criar faixas etárias
    bins = [18, 25, 30, 35, 40, 45, 50, 55, 100]
    labels = ['18-25', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '56+']
    
    # Garantir que a idade é numérica
    df_idade['Idade'] = pd.to_numeric(df_idade['Idade'], errors='coerce')
    df_idade = df_idade.dropna(subset=['Idade'])
    
    try:
        df_idade['Faixa_Etaria'] = pd.cut(df_idade['Idade'], bins=bins, labels=labels, right=False)
        
        # Contar por faixa etária
        contagem_idade = df_idade['Faixa_Etaria'].value_counts().sort_index()
        
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
        
    except Exception as e:
        # Em caso de erro, criar um gráfico vazio com mensagem
        fig = go.Figure()
        fig.add_annotation(
            text=f"Erro ao processar dados de idade: {str(e)}",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=VERMELHO, size=14)
        )
        fig.update_layout(title_text="Distribuição por Faixa Etária")
    
    return fig

# Função para criar gráfico de distribuição por cargo
def grafico_distribuicao_cargo(df):
    # Verificar se há dados de cargo disponíveis
    if 'Cargo' not in df.columns or df['Cargo'].isna().all():
        # Criar um gráfico vazio com mensagem
        fig = go.Figure()
        fig.add_annotation(
            text="Dados de posto/graduação não disponíveis",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=VERMELHO, size=16)
        )
        fig.update_layout(title_text="Distribuição por Posto/Graduação")
        return fig
    
    try:
        # Contar por cargo e ordenar pela hierarquia
        contagem_cargo = df.groupby(['Cargo', 'Ordem_Hierarquica']).size().reset_index(name='Quantidade')
        contagem_cargo = contagem_cargo.sort_values('Ordem_Hierarquica')
        
        # Se não houver dados após o agrupamento
        if len(contagem_cargo) == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="Sem dados suficientes para exibição",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(color=VERMELHO, size=16)
            )
            fig.update_layout(title_text="Distribuição por Posto/Graduação")
            return fig
        
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
        
    except Exception as e:
        # Em caso de erro, criar um gráfico vazio com mensagem
        fig = go.Figure()
        fig.add_annotation(
            text=f"Erro ao processar dados de posto/graduação: {str(e)}",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=VERMELHO, size=14)
        )
        fig.update_layout(title_text="Distribuição por Posto/Graduação")
    
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
                if estatisticas["media_idade"] is not None:
                    st.markdown(f'<div class="metrica">{estatisticas["media_idade"]:.1f}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="metrica">N/D</div>', unsafe_allow_html=True)
                    st.markdown('<div class="metrica-label">Dados de idade não disponíveis</div>', unsafe_allow_html=True)
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
        
        # Instruções detalhadas
        st.markdown("""
        ## Dashboard de Efetivo do CBMPR
        
        Este dashboard foi desenvolvido para visualização dos dados de pessoal do Corpo de Bombeiros Militar do Paraná.
        
        ### Instruções de Uso:
        
        1. **Upload do Arquivo:**
           - Clique no botão "Browse files" no menu lateral
           - Selecione o arquivo CSV contendo os dados do efetivo
           - O arquivo deve ter os cabeçalhos e dados conforme o padrão do CBMPR
        
        2. **Interagindo com o Dashboard:**
           - Utilize os filtros no menu lateral para refinar a visualização
           - Passe o mouse sobre os gráficos para ver detalhes
           - Ordene e filtre a tabela conforme necessário
           - Faça download dos dados filtrados em formato CSV
        
        ### Funcionalidades:
        - Visualização do total de efetivo
        - Média de idade do efetivo
        - Gráfico de distribuição por faixa etária
        - Gráfico de distribuição por posto/graduação
        - Filtros por cargo, unidade de trabalho e abono permanência
        - Tabela interativa com opção de download
        
        ### Solução de Problemas Comuns:
        
        #### Erro "Expected 1 fields in line X, saw Y"
        Este erro ocorre quando o delimitador no arquivo CSV não é consistente. Você pode:
        - Verificar o delimitador usado (vírgula, ponto-e-vírgula, tab)
        - Abrir o arquivo em um editor de texto e verificar a linha problemática
        - Salvar o arquivo garantindo o mesmo delimitador em todas as linhas
        
        #### Problema com codificação de caracteres
        Se os acentos e caracteres especiais aparecerem incorretamente:
        - Salve o arquivo com codificação Windows-1252 (CP1252)
        - Tente converter o arquivo para UTF-8 usando um editor de texto
        
        #### Problema com formato de dados
        O sistema trata automaticamente datas como texto. Não é necessário fazer conversões.
        """)
        
        # Adicionar exemplo de formato esperado
        with st.expander("Ver Exemplo de Formato Esperado"):
            st.markdown("""
            O arquivo CSV deve ter um formato similar a este:
            
            ```
            ID,Nome,RG,CPF,Data Nascimento,Idade,Descrição da Unidade de Trabalho,Cargo,Recebe Abono Permanência
            12345,JOÃO DA SILVA,1234567,123.456.789-00,01/01/1980,45,1GB 1SGB 1SEC BM,Coronel,S
            67890,MARIA SANTOS,7654321,987.654.321-00,15/05/1990,35,3GB 1SGB 1SEC BM,Capitão,N
            ```
            
            **Dicas para preparar o arquivo:**
            
            1. Verifique se todas as linhas têm o mesmo número de campos
            2. Certifique-se de que o delimitador seja consistente (vírgula, ponto-e-vírgula ou tab)
            3. Se abrir no Excel:
               - Salve como CSV (Separado por vírgulas)
               - Ou use "Salvar como" e selecione CSV (MS-DOS)
            """)
        
        # Informações para usuários técnicos
        with st.expander("Informações Técnicas para Resolução de Problemas"):
            st.markdown("""
            ### Resolução de Problemas Técnicos
            
            #### Para problemas de delimitação:
            ```python
            # Se o arquivo usa ponto-e-vírgula como delimitador:
            df = pd.read_csv('seu_arquivo.csv', delimiter=';', encoding='cp1252')
            
            # Se o arquivo usa tab como delimitador:
            df = pd.read_csv('seu_arquivo.csv', delimiter='\\t', encoding='cp1252')
            ```
            
            #### Para problemas com linhas de metadados:
            ```python
            # Pular as primeiras X linhas:
            df = pd.read_csv('seu_arquivo.csv', skiprows=X, encoding='cp1252')
            ```
            
            #### Para problemas com linhas mal formadas:
            ```python
            # Ignorar linhas com problemas:
            df = pd.read_csv('seu_arquivo.csv', on_bad_lines='skip', encoding='cp1252')
            ```
            
            O dashboard tenta automaticamente detectar o delimitador correto e ignorar linhas problemáticas.
            """)
        
        # Footer com informações
        st.markdown('<div class="footer">Dashboard desenvolvido para o Corpo de Bombeiros Militar do Paraná.<br/>Desenvolvido em Python com Streamlit.</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
