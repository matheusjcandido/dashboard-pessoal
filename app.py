import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import numpy as np
import re

# Configuração da página
st.set_page_config(
    page_title="Dashboard Pessoal CBMPR",
    page_icon="🔥",
    layout="wide"
)

# Definição de cores personalizadas do CBMPR
cores_cbmpr = {
    'azul_escuro': '#062733',
    'vermelho': '#D34339',
    'amarelo': '#FFD928',
    'cinza_escuro': '#606062',
    'cinza_claro': '#A39B96',
    'branco': '#FEFEFE',
    'preto': '#373435'
}

# CSS personalizado para a aplicação
st.markdown(f"""
<style>
    .stApp {{
        background-color: {cores_cbmpr['branco']};
    }}
    .stButton>button {{
        background-color: {cores_cbmpr['azul_escuro']};
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 5px;
        transition: all 0.3s;
    }}
    .stButton>button:hover {{
        background-color: {cores_cbmpr['vermelho']};
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    .stRadio label {{
        color: {cores_cbmpr['preto']};
    }}
    h1, h2, h3 {{
        color: {cores_cbmpr['azul_escuro']};
    }}
    .stMarkdown {{
        color: {cores_cbmpr['preto']};
    }}
    .stAlert {{
        background-color: {cores_cbmpr['cinza_claro']};
        color: {cores_cbmpr['preto']};
        border-radius: 8px;
    }}
    .stMetric {{
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    .stMetric label {{
        color: {cores_cbmpr['azul_escuro']};
        font-weight: bold;
    }}
    .stMetric .metric-value {{
        font-size: 24px;
        font-weight: bold;
        color: {cores_cbmpr['vermelho']};
    }}
    .stTabs {{
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    .stTab {{
        background-color: white;
    }}
    .stTab[aria-selected="true"] {{
        background-color: {cores_cbmpr['amarelo']};
        color: {cores_cbmpr['preto']};
        font-weight: bold;
    }}
    .stExpander {{
        border-radius: 8px;
        border: 1px solid {cores_cbmpr['cinza_claro']};
    }}
    .stDownloadButton>button {{
        background-color: {cores_cbmpr['vermelho']};
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 5px;
        transition: all 0.3s;
    }}
    .stDownloadButton>button:hover {{
        background-color: {cores_cbmpr['azul_escuro']};
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
</style>
""", unsafe_allow_html=True)

# Função para adicionar a seção de amostra de dados filtrados
def adicionar_secao_amostra_dados(df, filtro_abono=None):
    """
    Adiciona uma seção para visualizar e baixar amostra dos dados filtrados
    O dataframe df já deve estar com todos os filtros aplicados
    """
    # Limpar dados antes de exibir - remover possíveis linhas de totais ou vazias
    df_limpo = df.copy()
    
    # Remover linhas totalmente vazias
    df_limpo = df_limpo.dropna(how='all')
    
    # Identificar e remover linhas de totais (se existirem)
    if 'Nome' in df_limpo.columns:
        # Remover linhas onde o Nome contém "total", "totais", etc.
        df_limpo = df_limpo[~df_limpo['Nome'].astype(str).str.lower().str.contains('total')]
    
    # Remover linhas onde o ID está vazio ou contém "total"
    if 'ID' in df_limpo.columns:
        # Converter para string primeiro para evitar erros com NaN
        df_limpo = df_limpo[~df_limpo['ID'].astype(str).str.lower().str.contains('total')]
        df_limpo = df_limpo[df_limpo['ID'].astype(str).str.strip() != '']
    
    # Ordenar os dados alfabeticamente por Nome, se a coluna existir
    if 'Nome' in df_limpo.columns:
        df_ordenado = df_limpo.sort_values(by='Nome')
    else:
        # Se não houver coluna Nome, tentar ordenar pela primeira coluna de texto
        colunas_texto = df_limpo.select_dtypes(include=['object']).columns
        if len(colunas_texto) > 0:
            df_ordenado = df_limpo.sort_values(by=colunas_texto[0])
        else:
            df_ordenado = df_limpo
    
    # Mostrar amostra dos dados FILTRADOS
    st.subheader("Amostra dos Dados")
    with st.expander("Ver amostra dos dados"):
        # Exibir todos os dados com opção de rolagem, sem mostrar o índice
        st.dataframe(df_ordenado, height=400, use_container_width=True, hide_index=True)
        
        # Mostrar contador de linhas
        st.info(f"Mostrando todos os {len(df_ordenado)} registros. Use a barra de rolagem para navegar.")
        
        # Opção para download dos dados filtrados completos (também ordenados)
        csv_dados = df_ordenado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download dos Dados Filtrados (CSV)",
            data=csv_dados,
            file_name="dados_filtrados_cbmpr.csv",
            mime="text/csv"
        )

# Função para processar o arquivo CSV
def processar_arquivo_csv(uploaded_file):
    """
    Processa o arquivo CSV da SEAP, detectando automaticamente o delimitador
    """
    try:
        # Leitura inicial do arquivo
        conteudo = uploaded_file.read()
        
        # Tentar decodificar com cp1252 (Windows Latin-1)
        try:
            texto = conteudo.decode('cp1252')
        except UnicodeDecodeError:
            # Fallback para utf-8
            texto = conteudo.decode('utf-8', errors='replace')
        
        # Dividir em linhas
        linhas = texto.split('\r\n')
        if len(linhas) <= 1:
            linhas = texto.split('\n')
        
        # Detectar linha de cabeçalho e delimitador
        indice_header = -1
        delimitador = ','  # padrão
        
        for i, linha in enumerate(linhas):
            # Procurar por padrão de cabeçalho (começa com ID e contém Nome, RG, CPF)
            if re.match(r'^ID[,;]Nome[,;]RG', linha):
                indice_header = i
                # Determinar o delimitador
                if ';' in linha:
                    delimitador = ';'
                break
        
        if indice_header == -1:
            st.error("Formato de arquivo inválido. Não foi possível encontrar o cabeçalho com ID, Nome, RG.")
            return None
        
        # Extrair nomes das colunas
        colunas = linhas[indice_header].split(delimitador)
        
        # Criar lista de dicionários com os dados
        dados = []
        for i in range(indice_header + 2, len(linhas)):  # +2 para pular a linha vazia após o header
            linha = linhas[i].strip()
            if not linha:  # Pular linhas vazias
                continue
            
            campos = linha.split(delimitador)
            if len(campos) >= len(colunas):
                # Criar dicionário com os dados da linha
                registro = {}
                for j, coluna in enumerate(colunas):
                    if j < len(campos):
                        registro[coluna] = campos[j]
                
                # Verificar se não é uma linha de totais
                primeira_coluna = list(registro.values())[0] if registro else ""
                if primeira_coluna.lower().startswith("total") or primeira_coluna == "":
                    continue
                
                # Verificar se a linha tem conteúdo real (não só espaços)
                valores_nao_vazios = [v for v in registro.values() if v.strip()]
                if len(valores_nao_vazios) > 1:  # Pelo menos 2 campos não vazios
                    dados.append(registro)
        
        # Converter para DataFrame
        df = pd.DataFrame(dados)
        
        # Remover linhas onde todas as colunas são vazias ou NaN
        df = df.dropna(how='all')
        
        # Remover linhas onde o ID está vazio (geralmente linhas de totais ou dummies)
        if 'ID' in df.columns:
            df = df[df['ID'].notna() & (df['ID'] != '')]
        
        # Converter colunas numéricas
        if 'Idade' in df.columns:
            df['Idade'] = pd.to_numeric(df['Idade'], errors='coerce')
        
        # Informação de debug
        st.success(f"Arquivo processado com sucesso!\n"
                  f"- Delimitador detectado: '{delimitador}'\n"
                  f"- {len(df)} registros encontrados")
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        return None

# Função para criar o gráfico de distribuição de idade
def criar_grafico_distribuicao_idade(df, filtro_abono=None):
    if 'Idade' not in df.columns:
        st.error("Coluna de idade não encontrada no arquivo.")
        return None
    
    # Aplicar filtro de abono se solicitado
    if filtro_abono is not None and 'Recebe Abono Permanência' in df.columns:
        df = df[df['Recebe Abono Permanência'] == filtro_abono]
    
    # Remover valores nulos
    df_idade = df.dropna(subset=['Idade'])
    
    # Criar figura
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Histograma com KDE usando a cor azul escuro do CBMPR
    sns.histplot(df_idade['Idade'], bins=40, kde=True, ax=ax, color=cores_cbmpr['azul_escuro'])
    
    # Adicionar grade, títulos e ajustes visuais
    ax.grid(alpha=0.3)
    titulo = 'Distribuição de Idade - Corpo de Bombeiros Militar do Paraná'
    if filtro_abono == 'S':
        titulo += ' (Com Abono Permanência)'
    elif filtro_abono == 'N':
        titulo += ' (Sem Abono Permanência)'
    ax.set_title(titulo, fontsize=16)
    ax.set_xlabel('Idade (anos)', fontsize=12)
    ax.set_ylabel('Frequência', fontsize=12)
    
    # Adicionar estatísticas
    media = df_idade['Idade'].mean()
    mediana = df_idade['Idade'].median()
    min_idade = df_idade['Idade'].min()
    max_idade = df_idade['Idade'].max()
    
    # Adicionar linhas de média e mediana com cores do CBMPR
    ax.axvline(media, color=cores_cbmpr['vermelho'], linestyle='--', alpha=0.7, label=f'Média: {media:.1f} anos')
    ax.axvline(mediana, color=cores_cbmpr['amarelo'], linestyle='-.', alpha=0.7, label=f'Mediana: {mediana:.1f} anos')
    ax.legend()
    
    # Adicionar texto com estatísticas (usando cinza claro em vez de branco)
    stats_text = f"Estatísticas:\n" \
                 f"• Média: {media:.1f} anos\n" \
                 f"• Mediana: {mediana:.1f} anos\n" \
                 f"• Mínima: {min_idade:.0f} anos\n" \
                 f"• Máxima: {max_idade:.0f} anos\n" \
                 f"• Total: {len(df_idade)} militares"
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round,pad=0.5', facecolor=cores_cbmpr['cinza_claro'], alpha=0.8))
    
    plt.tight_layout()
    return fig

# Função para criar o gráfico de faixas etárias
def criar_grafico_faixas_etarias(df, filtro_abono=None):
    if 'Idade' not in df.columns:
        return None
    
    # Aplicar filtro de abono se solicitado
    if filtro_abono is not None and 'Recebe Abono Permanência' in df.columns:
        df = df[df['Recebe Abono Permanência'] == filtro_abono]
    
    # Remover valores nulos
    df_idade = df.dropna(subset=['Idade'])
    
    # Definir faixas etárias
    bins = [18, 25, 30, 35, 40, 45, 50, 55, 60]
    labels = ['18-25', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '56+']
    
    # Categorizar idades
    df_idade['Faixa Etária'] = pd.cut(df_idade['Idade'], bins=bins, labels=labels, right=True)
    
    # Contagem por faixa etária
    contagem = df_idade['Faixa Etária'].value_counts().sort_index()
    
    # Criar figura
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Definir cores personalizadas para cada barra usando a paleta CBMPR
    cores_barras = [
        cores_cbmpr['azul_escuro'],
        cores_cbmpr['vermelho'],
        cores_cbmpr['amarelo'],
        cores_cbmpr['cinza_escuro'],
        cores_cbmpr['cinza_claro'],
        cores_cbmpr['preto'],
        cores_cbmpr['azul_escuro'],
        cores_cbmpr['vermelho']
    ]
    
    # Criar gráfico de barras
    bars = ax.bar(contagem.index, contagem.values, color=cores_barras[:len(contagem)])
    
    # Adicionar títulos e ajustes visuais
    titulo = 'Distribuição por Faixas Etárias - Corpo de Bombeiros Militar do Paraná'
    if filtro_abono == 'S':
        titulo += ' (Com Abono Permanência)'
    elif filtro_abono == 'N':
        titulo += ' (Sem Abono Permanência)'
    ax.set_title(titulo, fontsize=16)
    ax.set_xlabel('Faixa Etária (anos)', fontsize=12)
    ax.set_ylabel('Quantidade de Militares', fontsize=12)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    return fig

# Função para criar o gráfico de distribuição por Unidade de Trabalho
def criar_grafico_distribuicao_unidade(df, filtro_abono=None):
    """
    Cria um gráfico de barras horizontais para visualizar a distribuição de militares por unidade de trabalho
    """
    # Verificar se a coluna de unidade de trabalho existe
    if 'Descrição da Unidade de Trabalho' in df.columns:
        coluna_unidade = 'Descrição da Unidade de Trabalho'
    elif 'Unidade de Trabalho' in df.columns:
        coluna_unidade = 'Unidade de Trabalho'
    elif 'Unidade' in df.columns:
        coluna_unidade = 'Unidade'
    else:
        st.error("Coluna de Unidade de Trabalho não encontrada no arquivo.")
        return None
    
    # Aplicar filtro de abono se solicitado
    df_unidade = df.copy()
    if filtro_abono is not None and 'Recebe Abono Permanência' in df.columns:
        df_unidade = df_unidade[df_unidade['Recebe Abono Permanência'] == filtro_abono]
    
    # Contagem por unidade
    contagem_unidade = df_unidade[coluna_unidade].value_counts()
    
    # Limitar para mostrar apenas as 20 maiores unidades se houver muitas
    if len(contagem_unidade) > 20:
        contagem_unidade = contagem_unidade.head(20)
        titulo_extra = " (20 maiores unidades)"
    else:
        titulo_extra = ""
    
    # Criar figura - garantindo espaço suficiente para os nomes das unidades
    altura_grafico = max(10, len(contagem_unidade) * 0.5)  # Ajusta a altura com base no número de unidades
    fig, ax = plt.subplots(figsize=(14, altura_grafico))
    
    # Criar um ciclo de cores
    cores_unidades = [
        cores_cbmpr['azul_escuro'], 
        cores_cbmpr['vermelho'], 
        cores_cbmpr['amarelo'],
        cores_cbmpr['cinza_escuro'], 
        cores_cbmpr['cinza_claro'],
        cores_cbmpr['preto']
    ]
    
    # Criar mapeamento de cores
    cores_mapeadas = [cores_unidades[i % len(cores_unidades)] for i in range(len(contagem_unidade))]
    
    # Criar gráfico de barras horizontais
    bars = ax.barh(contagem_unidade.index, contagem_unidade.values, color=cores_mapeadas)
    
    # Adicionar títulos e ajustes visuais
    titulo = f'Distribuição por Unidade de Trabalho - Corpo de Bombeiros Militar do Paraná{titulo_extra}'
    if filtro_abono == 'S':
        titulo += ' (Com Abono Permanência)'
    elif filtro_abono == 'N':
        titulo += ' (Sem Abono Permanência)'
    ax.set_title(titulo, fontsize=16)
    ax.set_xlabel('Quantidade de Militares', fontsize=12)
    ax.set_ylabel('Unidade de Trabalho', fontsize=12)
    
    # Adicionar grade apenas no eixo x
    ax.grid(axis='x', alpha=0.3)
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    return fig

# Função para criar o gráfico de distribuição por Cargo (Posto/Graduação)
def criar_grafico_distribuicao_cargo(df, filtro_abono=None):
    if 'Cargo' not in df.columns:
        st.error("Coluna de Cargo (Posto/Graduação) não encontrada no arquivo.")
        return None
    
    # Aplicar filtro de abono se solicitado
    if filtro_abono is not None and 'Recebe Abono Permanência' in df.columns:
        df = df[df['Recebe Abono Permanência'] == filtro_abono]
    
    # Limpar e padronizar valores da coluna Cargo
    df_cargo = df.copy()
    
    # Contagem por cargo
    contagem_cargo = df_cargo['Cargo'].value_counts()
    
    # Ordenar os cargos conforme hierarquia militar específica (ordem correta com Coronel no topo)
    hierarquia = [
        'Soldado 2ª Classe', 'Soldado 1ª Classe', 'Cabo', '3º Sargento', '2º Sargento', '1º Sargento',
        'Subtenente', 'Aluno de 1º Ano', 'Aluno de 2º Ano', 'Aluno de 3º Ano', 'Aspirante a Oficial',
        '2º Tenente 6', '2º Tenente', '1º Tenente', 'Capitão', 'Major', 'Tenente Coronel', 'Coronel'
    ]
    
    # Filtrar e reordenar os cargos encontrados conforme a hierarquia
    ordem_personalizada = []
    for rank in hierarquia:
        for cargo in contagem_cargo.index:
            if rank in cargo:
                ordem_personalizada.append(cargo)
    
    # Adicionar quaisquer outros cargos que não se encaixam na hierarquia padrão
    for cargo in contagem_cargo.index:
        if cargo not in ordem_personalizada:
            ordem_personalizada.append(cargo)
    
    # Filtrar para manter apenas os cargos que existem no DataFrame
    ordem_final = [cargo for cargo in ordem_personalizada if cargo in contagem_cargo.index]
    
    # Reordenar a contagem
    contagem_cargo = contagem_cargo.reindex(ordem_final)
    
    # Criar figura - garantindo espaço suficiente para os nomes dos cargos
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Definir cores personalizadas sem usar branco
    # Azul escuro, vermelho, amarelo, cinza escuro, cinza claro, verde, preto
    cores_cbmpr = ['#062733', '#D34339', '#FFD928', '#606062', '#A39B96', '#2E8B57', '#373435']
    
    # Criar um mapeamento de cores para cada posto/graduação
    n_cargos = len(contagem_cargo)
    cores_mapeadas = []
    
    # Distribuir as cores entre os cargos, repetindo se necessário
    for i in range(n_cargos):
        cor_idx = i % len(cores_cbmpr)
        cores_mapeadas.append(cores_cbmpr[cor_idx])
    
    # Criar gráfico de barras horizontais com as cores personalizadas
    bars = ax.barh(contagem_cargo.index, contagem_cargo.values, color=cores_mapeadas)
    
    # Adicionar títulos e ajustes visuais
    titulo = 'Distribuição por Posto/Graduação - Corpo de Bombeiros Militar do Paraná'
    if filtro_abono == 'S':
        titulo += ' (Com Abono Permanência)'
    elif filtro_abono == 'N':
        titulo += ' (Sem Abono Permanência)'
    ax.set_title(titulo, fontsize=16)
    ax.set_xlabel('Quantidade de Militares', fontsize=12)
    ax.set_ylabel('Posto/Graduação', fontsize=12)
    
    # Adicionar grade apenas no eixo x
    ax.grid(axis='x', alpha=0.3)
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    return fig

# Interface principal do Streamlit
st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, {cores_cbmpr['azul_escuro']} 0%, {cores_cbmpr['vermelho']} 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    ">
        <h1 style="color: white; text-align: center; margin: 0;">🚒 Dashboard - Pessoal CBMPR</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# Inicializar session_state para gerenciar o estado da aplicação
if 'filtros_cargo' not in st.session_state:
    st.session_state.filtros_cargo = []
if 'filtros_unidade' not in st.session_state:
    st.session_state.filtros_unidade = []

st.markdown(
    f"""
    <div style="
        background-color: {cores_cbmpr['cinza_claro']}30;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid {cores_cbmpr['amarelo']};
        margin-bottom: 20px;
    ">
        <p style="margin: 0; color: {cores_cbmpr['preto']};">
            Este dashboard apresenta visualizações para os dados de pessoal do Corpo de Bombeiros Militar do Paraná. 
            Faça o upload do arquivo CSV gerado pela SEAP para visualizar as informações.
        </p>
    </div>
    
    <div style="
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
    ">
        <div style="
            background-color: {cores_cbmpr['azul_escuro']}; 
            color: white; 
            padding: 10px; 
            border-radius: 5px;
            width: 48%;
            text-align: center;
        ">
            <strong>📄 Formato suportado:</strong> CSV com delimitador vírgula (,)
        </div>
        <div style="
            background-color: {cores_cbmpr['vermelho']}; 
            color: white; 
            padding: 10px; 
            border-radius: 5px;
            width: 48%;
            text-align: center;
        ">
            <strong>📄 Formato suportado:</strong> CSV com delimitador ponto-e-vírgula (;)
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Seção de upload de arquivo
st.markdown(
    f"""
    <div style="
        background-color: {cores_cbmpr['azul_escuro']};
        padding: 12px 20px;
        border-radius: 8px 8px 0 0;
        margin-top: 30px;
        margin-bottom: 0px;
    ">
        <h2 style="color: white; margin: 0; font-size: 1.5em;">1. Carregar Arquivo</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# Adicionar um fundo claro para a seção de upload
st.markdown(
    f"""
    <div style="
        background-color: {cores_cbmpr['cinza_claro']}20;
        padding: 20px;
        border-radius: 0 0 8px 8px;
        margin-bottom: 30px;
        border: 1px solid {cores_cbmpr['cinza_claro']}60;
    ">
    </div>
    """,
    unsafe_allow_html=True
)

# Opção para usar dados simulados para teste
usar_dados_teste = st.checkbox("Usar dados de exemplo para teste", value=False)

if usar_dados_teste:
    # Criar dados de exemplo com distribuição similar à encontrada na análise
    np.random.seed(42)  # Para reprodutibilidade
    
    # Distribuição aproximada de idade
    faixas = {
        "18-25": 138,
        "26-30": 264,
        "31-35": 762,
        "36-40": 876,
        "41-45": 568,
        "46-50": 363,
        "51-55": 231,
        "56+": 9
    }
    
    # Distribuição aproximada de cargos
    cargos = {
        "Coronel": 5,
        "Tenente Coronel": 20,
        "Major": 35,
        "Capitão": 90,
        "1º Tenente": 140,
        "2º Tenente": 180,
        "Subtenente": 200,
        "1º Sargento": 300,
        "2º Sargento": 450,
        "3º Sargento": 600,
        "Cabo": 700,
        "Soldado 1ª Classe": 450,
        "Soldado 2ª Classe": 50
    }
    
    # Gerar idades com base na distribuição
    idades = []
    for faixa, quantidade in faixas.items():
        if faixa == "18-25":
            idades.extend(np.random.randint(18, 26, quantidade))
        elif faixa == "26-30":
            idades.extend(np.random.randint(26, 31, quantidade))
        elif faixa == "31-35":
            idades.extend(np.random.randint(31, 36, quantidade))
        elif faixa == "36-40":
            idades.extend(np.random.randint(36, 41, quantidade))
        elif faixa == "41-45":
            idades.extend(np.random.randint(41, 46, quantidade))
        elif faixa == "46-50":
            idades.extend(np.random.randint(46, 51, quantidade))
        elif faixa == "51-55":
            idades.extend(np.random.randint(51, 56, quantidade))
        elif faixa == "56+":
            idades.extend(np.random.randint(56, 61, quantidade))
    
    # Gerar lista de cargos
    lista_cargos = []
    for cargo, quantidade in cargos.items():
        lista_cargos.extend([cargo] * quantidade)
    
    # Ajustar tamanhos se necessário
    min_len = min(len(idades), len(lista_cargos))
    idades = idades[:min_len]
    lista_cargos = lista_cargos[:min_len]
    
    # Gerar valores para Abono Permanência (mais comuns para idade > 50)
    recebe_abono = []
    for idade in idades:
        if idade >= 50:
            # 80% das pessoas com 50+ anos recebem abono
            recebe_abono.append('S' if np.random.random() < 0.8 else 'N')
        else:
            # 5% das pessoas abaixo de 50 anos recebem abono
            recebe_abono.append('S' if np.random.random() < 0.05 else 'N')
    
    # Criar dataframe de exemplo
    df = pd.DataFrame({
        'ID': range(1, min_len + 1),
        'Nome': [f'Bombeiro Exemplo {i}' for i in range(1, min_len + 1)],
        'Idade': idades,
        'Cargo': lista_cargos,
        'Recebe Abono Permanência': recebe_abono
    })

# Remover a seção de "Ver amostra dos dados" que aparece logo após o upload
# E adicionar filtro de dados
if usar_dados_teste:
    # Exibir contagem total em um card grande
    st.success(f"Dados de exemplo carregados com sucesso!")
    
    # Card destacado com o efetivo total
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {cores_cbmpr['vermelho']} 0%, {cores_cbmpr['azul_escuro']} 100%);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 20px 0;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        ">
            <h2 style="color: white; margin: 0; font-weight: 400;">Efetivo Total</h2>
            <h1 style="color: white; font-size: 48px; margin: 10px 0;">{len(df)}</h1>
            <p style="color: white; margin: 0;">militares</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
else:
    # Upload de arquivo CSV
    uploaded_file = st.file_uploader("Escolha o arquivo CSV", type="csv")
    
    if uploaded_file is not None:
        try:
            df = processar_arquivo_csv(uploaded_file)
            
            if df is not None:
                # Card destacado com o efetivo total
                st.markdown(
                    f"""
                    <div style="
                        background-color: {cores_cbmpr['vermelho']};
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        margin: 20px 0;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    ">
                        <h2 style="color: white; margin: 0;">Efetivo Total</h2>
                        <h1 style="color: white; font-size: 48px; margin: 10px 0;">{len(df)}</h1>
                        <p style="color: white; margin: 0;">militares</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.stop()
        
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            st.stop()
    else:
        st.info("Por favor, faça upload de um arquivo CSV ou use os dados de exemplo.")
        st.stop()

# Seção de Filtros
st.markdown(
    f"""
    <div style="
        background-color: {cores_cbmpr['azul_escuro']};
        padding: 12px 20px;
        border-radius: 8px 8px 0 0;
        margin-top: 30px;
        margin-bottom: 0px;
    ">
        <h2 style="color: white; margin: 0; font-size: 1.5em;">2. Filtros</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# Adicionar um fundo claro para a seção de filtros
st.markdown(
    f"""
    <div style="
        background-color: {cores_cbmpr['cinza_claro']}20;
        padding: 10px 20px;
        border-radius: 0 0 8px 8px;
        margin-bottom: 20px;
        border: 1px solid {cores_cbmpr['cinza_claro']}60;
    ">
    </div>
    """,
    unsafe_allow_html=True
)

# Inicializar variáveis de filtro
filtros_cargo = []
filtros_unidade = []

# Aplicar função de filtragem
def aplicar_filtros(dataframe, filtro_abono, filtros_cargo, filtros_unidade=None):
    """Aplica todos os filtros selecionados ao dataframe"""
    df_filtrado = dataframe.copy()
    
    # Aplicar filtro de abono, se houver
    if filtro_abono is not None and 'Recebe Abono Permanência' in dataframe.columns:
        df_filtrado = df_filtrado[df_filtrado['Recebe Abono Permanência'] == filtro_abono]
    
    # Aplicar filtro de cargos, se houver
    if filtros_cargo and 'Cargo' in dataframe.columns:
        df_filtrado = df_filtrado[df_filtrado['Cargo'].isin(filtros_cargo)]
    
    # Aplicar filtro de unidades, se houver
    if filtros_unidade:
        # Verificar qual coluna de unidade existe
        coluna_unidade = None
        for possivel_coluna in ['Descrição da Unidade de Trabalho', 'Unidade de Trabalho', 'Unidade']:
            if possivel_coluna in dataframe.columns:
                coluna_unidade = possivel_coluna
                break
        
        if coluna_unidade and filtros_unidade:
            df_filtrado = df_filtrado[df_filtrado[coluna_unidade].isin(filtros_unidade)]
    
    return df_filtrado

# Criar tabs para os diferentes tipos de filtros
tab_cargo, tab_unidade, tab_abono = st.tabs(["Filtro por Posto/Graduação", "Filtro por Unidade", "Filtro por Abono"])

# Tab 1: Filtro de Abono Permanência
with tab_abono:
    # Verificar se a coluna de Abono está presente
    tem_coluna_abono = 'Recebe Abono Permanência' in df.columns

    if tem_coluna_abono:
        opcoes_abono = ["Todos", "Apenas que recebem", "Apenas que não recebem"]
        filtro_escolhido = st.radio("Filtrar por Abono Permanência:", opcoes_abono)
        
        if filtro_escolhido == "Todos":
            filtro_abono = None
        elif filtro_escolhido == "Apenas que recebem":
            filtro_abono = 'S'
        else:  # "Apenas que não recebem"
            filtro_abono = 'N'
    else:
        st.warning("Coluna 'Recebe Abono Permanência' não encontrada no arquivo. O filtro não está disponível.")
        filtro_abono = None

# Tab 2: Filtro por Posto/Graduação
with tab_cargo:
    if 'Cargo' in df.columns:
        # Obter lista única de postos/graduações
        cargos = df['Cargo'].unique()
        
        # Ordenar os cargos conforme hierarquia militar específica (com Coronel no topo)
        hierarquia = [
            'Soldado 2ª Classe', 'Soldado 1ª Classe', 'Cabo', '3º Sargento', '2º Sargento', '1º Sargento',
            'Subtenente', 'Aluno de 1º Ano', 'Aluno de 2º Ano', 'Aluno de 3º Ano', 'Aspirante a Oficial',
            '2º Tenente 6', '2º Tenente', '1º Tenente', 'Capitão', 'Major', 'Tenente Coronel', 'Coronel'
        ]
        
        # Ordenar cargos conforme hierarquia
        cargos_ordenados = []
        for rank in hierarquia:
            for cargo in cargos:
                if rank in cargo and cargo not in cargos_ordenados:
                    cargos_ordenados.append(cargo)
        
        # Adicionar quaisquer outros cargos que não se encaixam na hierarquia padrão
        for cargo in cargos:
            if cargo not in cargos_ordenados:
                cargos_ordenados.append(cargo)
        
        # Inicializar o estado dos filtros de cargo se ainda não existir
        if 'filtros_cargo' not in st.session_state:
            st.session_state.filtros_cargo = cargos_ordenados.copy()
        
        # Função para selecionar todos os cargos
        def selecionar_todos_cargos():
            st.session_state.filtros_cargo = cargos_ordenados.copy()
        
        # Função para limpar todos os cargos
        def limpar_cargos():
            st.session_state.filtros_cargo = []
        
        # Opção para selecionar todos ou nenhum
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Selecionar Todos (Posto/Grad)", on_click=selecionar_todos_cargos):
                pass
        with col2:
            if st.button("Limpar Postos/Grad", on_click=limpar_cargos):
                pass
        
        # Verificar se há muitos cargos e criar selectbox com multiselect ou usar checkboxes
        if len(cargos_ordenados) > 10:
            # Usar multiselect para muitos cargos
            filtros_cargo = st.multiselect(
                "Selecione os Postos/Graduações:",
                options=cargos_ordenados,
                default=st.session_state.filtros_cargo,
                key="multiselect_cargos"
            )
            # Atualizar o estado com a seleção atual
            st.session_state.filtros_cargo = filtros_cargo
        else:
            # Para poucos cargos, usar checkboxes
            st.write("Selecione os Postos/Graduações:")
            filtros_cargo = []
            # Organizar em 2 colunas
            cols = st.columns(2)
            for i, cargo in enumerate(cargos_ordenados):
                col_idx = i % 2
                with cols[col_idx]:
                    # Determinar se o checkbox deve estar marcado com base no estado
                    valor_padrao = cargo in st.session_state.filtros_cargo
                    if st.checkbox(cargo, value=valor_padrao, key=f"cargo_{i}"):
                        filtros_cargo.append(cargo)
            
            # Atualizar o estado com a seleção atual
            st.session_state.filtros_cargo = filtros_cargo
    else:
        st.warning("Coluna 'Cargo' não encontrada no arquivo. O filtro por Posto/Graduação não está disponível.")
        filtros_cargo = []

# Tab 3: Filtro por Unidade de Trabalho
with tab_unidade:
    # Verificar qual coluna de unidade existe
    coluna_unidade = None
    for possivel_coluna in ['Descrição da Unidade de Trabalho', 'Unidade de Trabalho', 'Unidade']:
        if possivel_coluna in df.columns:
            coluna_unidade = possivel_coluna
            break
    
    if coluna_unidade:
        # Obter lista única de unidades e ordená-las alfabeticamente
        unidades = sorted(df[coluna_unidade].unique())
        
        # Inicializar o estado dos filtros de unidade se ainda não existir
        if 'filtros_unidade' not in st.session_state:
            st.session_state.filtros_unidade = unidades.copy()
        
        # Função para selecionar todas as unidades
        def selecionar_todas_unidades():
            st.session_state.filtros_unidade = unidades.copy()
        
        # Função para limpar todas as unidades
        def limpar_unidades():
            st.session_state.filtros_unidade = []
        
        # Opção para selecionar todos ou nenhum
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Selecionar Todas (Unidades)", on_click=selecionar_todas_unidades):
                pass
        with col2:
            if st.button("Limpar Unidades", on_click=limpar_unidades):
                pass
        
        # Usar multiselect para unidades
        filtros_unidade = st.multiselect(
            "Selecione as Unidades de Trabalho:",
            options=unidades,
            default=st.session_state.filtros_unidade,
            key="multiselect_unidades"
        )
        
        # Atualizar o estado com a seleção atual
        st.session_state.filtros_unidade = filtros_unidade
    else:
        st.warning("Coluna de Unidade de Trabalho não encontrada no arquivo. O filtro não está disponível.")
        filtros_unidade = []

# Aplicar os filtros ao dataframe
df_filtrado = aplicar_filtros(df, filtro_abono, filtros_cargo, filtros_unidade)

# Mostrar contadores com base nos filtros aplicados
st.markdown(
    f"""
    <div style="
        background-color: {cores_cbmpr['amarelo']};
        padding: 12px 20px;
        border-radius: 8px 8px 0 0;
        margin-bottom: 0px;
    ">
        <h3 style="color: {cores_cbmpr['preto']}; margin: 0; font-size: 1.3em;">Estatísticas com base nos filtros aplicados</h3>
    </div>
    """,
    unsafe_allow_html=True
)

total_original = len(df)
total_filtrado = len(df_filtrado)

col1, col2 = st.columns(2)
with col1:
    st.metric("Total de Militares (Original)", f"{total_original}")
with col2:
    st.metric("Total após filtros", f"{total_filtrado} ({total_filtrado/total_original*100:.1f}%)")

# Adicionar estatísticas de idade
if 'Idade' in df_filtrado.columns:
    # Remover valores nulos para cálculos
    df_idade = df_filtrado.dropna(subset=['Idade'])
    
    if len(df_idade) > 0:  # Verificar se há dados após filtro
        st.markdown(
            f"""
            <div style="
                background-color: {cores_cbmpr['vermelho']};
                padding: 12px 20px;
                border-radius: 8px 8px 0 0;
                margin-top: 20px;
                margin-bottom: 0px;
            ">
                <h3 style="color: white; margin: 0; font-size: 1.3em;">Estatísticas de Idade</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Idade Média", f"{df_idade['Idade'].mean():.1f} anos")
        with col2:
            st.metric("Idade Mediana", f"{df_idade['Idade'].median():.1f} anos")
        with col3:
            st.metric("Idade Mínima", f"{df_idade['Idade'].min():.0f} anos")
        with col4:
            st.metric("Idade Máxima", f"{df_idade['Idade'].max():.0f} anos")

# Se houver filtro de abono, mostrar estatísticas específicas
if tem_coluna_abono:
    total = len(df_filtrado)
    recebe = len(df_filtrado[df_filtrado['Recebe Abono Permanência'] == 'S'])
    nao_recebe = len(df_filtrado[df_filtrado['Recebe Abono Permanência'] == 'N'])
    
    st.markdown(
        f"""
        <div style="
            background-color: {cores_cbmpr['cinza_escuro']};
            padding: 12px 20px;
            border-radius: 8px 8px 0 0;
            margin-top: 20px;
            margin-bottom: 0px;
        ">
            <h3 style="color: white; margin: 0; font-size: 1.3em;">Estatísticas de Abono Permanência</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total com Filtros", f"{total}")
    with col2:
        st.metric("Recebem Abono", f"{recebe} ({recebe/total*100:.1f}% do filtrado)" if total > 0 else "0 (0%)")
    with col3:
        st.metric("Não Recebem Abono", f"{nao_recebe} ({nao_recebe/total*100:.1f}% do filtrado)" if total > 0 else "0 (0%)")

# Adicionar opção para download das estatísticas gerais
if 'Idade' in df_filtrado.columns:
    df_idade = df_filtrado.dropna(subset=['Idade'])
    if len(df_idade) > 0:
        # Tabela de estatísticas para download
        estatisticas = pd.DataFrame({
            'Estatística': ['Média', 'Mediana', 'Mínima', 'Máxima', 'Total de Militares'],
            'Valor': [
                f"{df_idade['Idade'].mean():.1f} anos",
                f"{df_idade['Idade'].median():.1f} anos",
                f"{df_idade['Idade'].min():.0f} anos",
                f"{df_idade['Idade'].max():.0f} anos",
                f"{len(df_idade)}"
            ]
        })
        
        csv_estatisticas = estatisticas.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download das Estatísticas (CSV)",
            data=csv_estatisticas,
            file_name="estatisticas_gerais_cbmpr.csv",
            mime="text/csv"
        )

# Seção de visualização
st.markdown(
    f"""
    <div style="
        background-color: {cores_cbmpr['azul_escuro']};
        padding: 12px 20px;
        border-radius: 8px 8px 0 0;
        margin-top: 30px;
        margin-bottom: 0px;
    ">
        <h2 style="color: white; margin: 0; font-size: 1.5em;">3. Visualizações</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# Adicionar um fundo claro para a seção de visualização
st.markdown(
    f"""
    <div style="
        background-color: {cores_cbmpr['cinza_claro']}20;
        padding: 10px 20px;
        border-radius: 0 0 8px 8px;
        margin-bottom: 20px;
        border: 1px solid {cores_cbmpr['cinza_claro']}60;
    ">
    </div>
    """,
    unsafe_allow_html=True
)

# Opções de visualização
tipo_grafico = st.radio(
    "Escolha o tipo de visualização:",
    ["Distribuição por Faixas Etárias", 
     "Distribuição por Posto/Graduação",
     "Distribuição por Unidade de Trabalho"]
)

# Nota: A partir daqui, usamos df_filtrado em vez de df para visualizações
if tipo_grafico == "Distribuição por Faixas Etárias":
    st.subheader("Distribuição por Faixas Etárias")
    # Usar dataframe já filtrado
    fig = criar_grafico_faixas_etarias(df_filtrado, None)  # Filtro já aplicado
    
    if fig:
        st.pyplot(fig)
        
        # Opção para download do gráfico
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        
        st.download_button(
            label="📥 Download do Gráfico (PNG)",
            data=buf,
            file_name="faixas_etarias_cbmpr.png",
            mime="image/png"
        )
        
        # Exibir tabela de faixas etárias
        st.subheader("Tabela de Faixas Etárias")
        
        # Remover valores nulos do dataframe já filtrado
        df_idade = df_filtrado.dropna(subset=['Idade'])
        
        # Definir faixas etárias
        bins = [18, 25, 30, 35, 40, 45, 50, 55, 60]
        labels = ['18-25', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '56+']
        
        # Categorizar idades
        df_idade['Faixa Etária'] = pd.cut(df_idade['Idade'], bins=bins, labels=labels, right=True)
        
        # Contagem por faixa etária
        contagem = df_idade['Faixa Etária'].value_counts().sort_index()
        percentual = (contagem / contagem.sum() * 100).round(2) if len(contagem) > 0 else pd.Series()
        
        tabela_faixas = pd.DataFrame({
            'Faixa Etária': contagem.index,
            'Quantidade': contagem.values,
            'Percentual (%)': percentual.values
        })
        
        st.dataframe(tabela_faixas, use_container_width=True, hide_index=True)
        
        # Opção para download da tabela
        csv = tabela_faixas.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download da Tabela (CSV)",
            data=csv,
            file_name="tabela_faixas_etarias_cbmpr.csv",
            mime="text/csv"
        )
        
        # Adicionar seção de amostra de dados após as visualizações e análises
        adicionar_secao_amostra_dados(df_filtrado, None)  # Filtro já aplicado

elif tipo_grafico == "Distribuição por Posto/Graduação":
    st.subheader("Distribuição por Posto/Graduação")
    # Usar dataframe já filtrado
    fig = criar_grafico_distribuicao_cargo(df_filtrado, None)  # Filtro já aplicado
    
    if fig:
        st.pyplot(fig)
        
        # Opção para download do gráfico
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        
        st.download_button(
            label="📥 Download do Gráfico (PNG)",
            data=buf,
            file_name="distribuicao_posto_graduacao_cbmpr.png",
            mime="image/png"
        )
        
        # Exibir tabela de cargos
        st.subheader("Tabela de Distribuição por Posto/Graduação")
        
        # Contagem por cargo no dataframe já filtrado
        contagem = df_filtrado['Cargo'].value_counts()
        percentual = (contagem / contagem.sum() * 100).round(2) if len(contagem) > 0 else pd.Series()
        
        tabela_cargos = pd.DataFrame({
            'Posto/Graduação': contagem.index,
            'Quantidade': contagem.values,
            'Percentual (%)': percentual.values
        })
        
        st.dataframe(tabela_cargos, use_container_width=True, hide_index=True)
        
        # Opção para download da tabela
        csv = tabela_cargos.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download da Tabela (CSV)",
            data=csv,
            file_name="tabela_postos_graduacoes_cbmpr.csv",
            mime="text/csv"
        )
        
        # Adicionar seção de amostra de dados após as visualizações e análises
        adicionar_secao_amostra_dados(df_filtrado, None)  # Filtro já aplicado

else:  # Distribuição por Unidade de Trabalho
    st.subheader("Distribuição por Unidade de Trabalho")
    
    # Verificar qual coluna de unidade existe
    if 'Descrição da Unidade de Trabalho' in df_filtrado.columns:
        coluna_unidade = 'Descrição da Unidade de Trabalho'
    elif 'Unidade de Trabalho' in df_filtrado.columns:
        coluna_unidade = 'Unidade de Trabalho'
    elif 'Unidade' in df_filtrado.columns:
        coluna_unidade = 'Unidade'
    else:
        st.error("Coluna de Unidade de Trabalho não encontrada no arquivo.")
        adicionar_secao_amostra_dados(df_filtrado, None)  # Filtro já aplicado
        st.stop()
    
    # Exibir tabela de unidades - ordenada alfabeticamente
    st.subheader("Tabela de Distribuição por Unidade de Trabalho")
    
    # Contagem por unidade no dataframe já filtrado
    contagem = df_filtrado[coluna_unidade].value_counts()
    percentual = (contagem / contagem.sum() * 100).round(2) if len(contagem) > 0 else pd.Series()
    
    # Criar dataframe com contagens e ordenar alfabeticamente
    tabela_unidades = pd.DataFrame({
        'Unidade de Trabalho': contagem.index,
        'Quantidade': contagem.values,
        'Percentual (%)': percentual.values
    })
    
    # Ordenar por unidade (alfabética) em vez de por contagem
    tabela_unidades = tabela_unidades.sort_values('Unidade de Trabalho')
    
    st.dataframe(tabela_unidades, use_container_width=True, hide_index=True)
    
    # Opção para download da tabela
    csv = tabela_unidades.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download da Tabela (CSV)",
        data=csv,
        file_name="tabela_unidades_cbmpr.csv",
        mime="text/csv"
    )
    
    # Adicionar seção de amostra de dados após as visualizações e análises
    adicionar_secao_amostra_dados(df_filtrado, None)  # Filtro já aplicado

# Rodapé
st.markdown("---")
st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, {cores_cbmpr['cinza_escuro']} 0%, {cores_cbmpr['azul_escuro']} 100%);
        padding: 25px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-top: 40px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    ">
        <p style="margin-bottom: 10px;"><strong>Dashboard desenvolvido para o Corpo de Bombeiros Militar do Paraná</strong></p>
        <p style="margin: 0;">💻 Para mais informações, consulte o repositório no GitHub</p>
        <div style="font-size: 30px; margin-top: 10px;">
            <span style="margin: 0 10px; color: {cores_cbmpr['amarelo']};">🚒</span>
            <span style="margin: 0 10px; color: {cores_cbmpr['vermelho']};">🔥</span>
            <span style="margin: 0 10px; color: {cores_cbmpr['amarelo']};">🚒</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
