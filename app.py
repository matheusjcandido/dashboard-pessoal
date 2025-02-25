import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import numpy as np
import re

# Configuração da página
st.set_page_config(
    page_title="Dashboard CBMPR - Efetivo",
    page_icon="🚒",
    layout="wide"
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
                dados.append(registro)
        
        # Converter para DataFrame
        df = pd.DataFrame(dados)
        
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
def criar_grafico_distribuicao_idade(df):
    if 'Idade' not in df.columns:
        st.error("Coluna de idade não encontrada no arquivo.")
        return None
    
    # Remover valores nulos
    df_idade = df.dropna(subset=['Idade'])
    
    # Criar figura
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Histograma com KDE
    sns.histplot(df_idade['Idade'], bins=40, kde=True, ax=ax, color='#1e3d59')
    
    # Adicionar grade, títulos e ajustes visuais
    ax.grid(alpha=0.3)
    ax.set_title('Distribuição de Idade - Corpo de Bombeiros Militar do Paraná', fontsize=16)
    ax.set_xlabel('Idade (anos)', fontsize=12)
    ax.set_ylabel('Frequência', fontsize=12)
    
    # Adicionar estatísticas
    media = df_idade['Idade'].mean()
    mediana = df_idade['Idade'].median()
    min_idade = df_idade['Idade'].min()
    max_idade = df_idade['Idade'].max()
    
    # Adicionar linhas de média e mediana
    ax.axvline(media, color='red', linestyle='--', alpha=0.7, label=f'Média: {media:.1f} anos')
    ax.axvline(mediana, color='green', linestyle='-.', alpha=0.7, label=f'Mediana: {mediana:.1f} anos')
    ax.legend()
    
    # Adicionar texto com estatísticas
    stats_text = f"Estatísticas:\n" \
                 f"• Média: {media:.1f} anos\n" \
                 f"• Mediana: {mediana:.1f} anos\n" \
                 f"• Mínima: {min_idade:.0f} anos\n" \
                 f"• Máxima: {max_idade:.0f} anos\n" \
                 f"• Total: {len(df_idade)} militares"
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    return fig

# Função para criar o gráfico de faixas etárias
def criar_grafico_faixas_etarias(df):
    if 'Idade' not in df.columns:
        return None
    
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
    
    # Cores para o gráfico de barras
    cores = sns.color_palette("Blues_r", len(labels))
    
    # Criar gráfico de barras
    bars = ax.bar(contagem.index, contagem.values, color=cores)
    
    # Adicionar rótulos em cima das barras
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{height:,}', ha='center', va='bottom')
    
    # Adicionar percentuais
    total = contagem.sum()
    percentuais = contagem / total * 100
    
    for i, (bar, pct) in enumerate(zip(bars, percentuais)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height / 2,
                f'{pct:.1f}%', ha='center', va='center', color='white', fontweight='bold')
    
    # Adicionar títulos e ajustes visuais
    ax.set_title('Distribuição por Faixas Etárias - Corpo de Bombeiros Militar do Paraná', fontsize=16)
    ax.set_xlabel('Faixa Etária (anos)', fontsize=12)
    ax.set_ylabel('Quantidade de Militares', fontsize=12)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    return fig

# Função para criar o gráfico de distribuição por Cargo (Posto/Graduação)
def criar_grafico_distribuicao_cargo(df):
    if 'Cargo' not in df.columns:
        st.error("Coluna de Cargo (Posto/Graduação) não encontrada no arquivo.")
        return None
    
    # Limpar e padronizar valores da coluna Cargo
    df_cargo = df.copy()
    
    # Contagem por cargo
    contagem_cargo = df_cargo['Cargo'].value_counts()
    
    # Ordenar os cargos conforme hierarquia militar típica
    # Lista com a ordem hierárquica aproximada no Corpo de Bombeiros
    hierarquia = [
        'Coronel', 'Tenente-Coronel', 'Major', 'Capitão',
        '1º Tenente', '2º Tenente', 'Aspirante',
        'Subtenente', '1º Sargento', '2º Sargento', '3º Sargento',
        'Cabo', 'Soldado'
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
    
    # Criar gráfico de barras horizontais
    cores = sns.color_palette("viridis", len(contagem_cargo))
    bars = ax.barh(contagem_cargo.index, contagem_cargo.values, color=cores)
    
    # Adicionar rótulos nas barras
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 5, bar.get_y() + bar.get_height()/2, 
                f'{width:,}', va='center')
    
    # Adicionar percentuais
    total = contagem_cargo.sum()
    for i, bar in enumerate(bars):
        width = bar.get_width()
        percentual = (width / total) * 100
        if percentual >= 2:  # Mostrar percentual apenas para barras maiores
            ax.text(width / 2, bar.get_y() + bar.get_height()/2, 
                    f'{percentual:.1f}%', va='center', ha='center', 
                    color='white', fontweight='bold')
    
    # Adicionar títulos e ajustes visuais
    ax.set_title('Distribuição por Posto/Graduação - Corpo de Bombeiros Militar do Paraná', fontsize=16)
    ax.set_xlabel('Quantidade de Militares', fontsize=12)
    ax.set_ylabel('Posto/Graduação', fontsize=12)
    
    # Adicionar grade apenas no eixo x
    ax.grid(axis='x', alpha=0.3)
    ax.set_axisbelow(True)
    
    # Inverter o eixo y para que a hierarquia superior fique no topo
    ax.invert_yaxis()
    
    plt.tight_layout()
    return fig

# Interface principal do Streamlit
st.title("🚒 Dashboard - Corpo de Bombeiros Militar do Paraná")

st.markdown("""
Este dashboard apresenta visualizações sobre os dados de pessoal do Corpo de Bombeiros Militar do Paraná.
Faça o upload do arquivo CSV gerado pela SEAP para visualizar os gráficos.

**Formatos Suportados:**
- Arquivos CSV com delimitador vírgula (,)
- Arquivos CSV com delimitador ponto-e-vírgula (;)
""")

# Seção de upload de arquivo
st.header("1. Carregar Arquivo")

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
        "Tenente-Coronel": 20,
        "Major": 35,
        "Capitão": 90,
        "1º Tenente": 140,
        "2º Tenente": 180,
        "Subtenente": 200,
        "1º Sargento": 300,
        "2º Sargento": 450,
        "3º Sargento": 600,
        "Cabo": 700,
        "Soldado": 500
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
    
    # Criar dataframe de exemplo
    df = pd.DataFrame({
        'ID': range(1, min_len + 1),
        'Nome': [f'Bombeiro Exemplo {i}' for i in range(1, min_len + 1)],
        'Idade': idades,
        'Cargo': lista_cargos
    })
    
    # Exibir contagem total em um card grande
    st.success(f"Dados de exemplo carregados com sucesso!")
    
    # Card destacado com o efetivo total
    st.markdown(
        f"""
        <div style="
            background-color: #FF4500;
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
    
    # Mostrar amostra dos dados
    with st.expander("Ver amostra dos dados"):
        st.dataframe(df.head(10))
    
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
                        background-color: #FF4500;
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
                
                # Mostrar amostra dos dados
                with st.expander("Ver amostra dos dados"):
                    st.dataframe(df.head(10))
            else:
                st.stop()
        
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {str(e)}")
            st.stop()
    else:
        st.info("Por favor, faça upload de um arquivo CSV ou use os dados de exemplo.")
        st.stop()

# Seção de visualização
st.header("2. Visualizações")

# Opções de visualização
tipo_grafico = st.radio(
    "Escolha o tipo de visualização:",
    ["Distribuição por Idade (Histograma)", 
     "Distribuição por Faixas Etárias", 
     "Distribuição por Posto/Graduação"]
)

if tipo_grafico == "Distribuição por Idade (Histograma)":
    st.subheader("Distribuição de Idades")
    fig = criar_grafico_distribuicao_idade(df)
    
    if fig:
        st.pyplot(fig)
        
        # Opção para download do gráfico
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        
        st.download_button(
            label="📥 Download do Gráfico (PNG)",
            data=buf,
            file_name="distribuicao_idade_cbmpr.png",
            mime="image/png"
        )
        
        # Exibir estatísticas em colunas
        st.subheader("Estatísticas")
        
        # Remover valores nulos
        df_idade = df.dropna(subset=['Idade'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Idade Média", f"{df_idade['Idade'].mean():.1f} anos")
        with col2:
            st.metric("Idade Mediana", f"{df_idade['Idade'].median():.1f} anos")
        with col3:
            st.metric("Idade Mínima", f"{df_idade['Idade'].min():.0f} anos")
        with col4:
            st.metric("Idade Máxima", f"{df_idade['Idade'].max():.0f} anos")

elif tipo_grafico == "Distribuição por Faixas Etárias":
    st.subheader("Distribuição por Faixas Etárias")
    fig = criar_grafico_faixas_etarias(df)
    
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
        
        # Remover valores nulos
        df_idade = df.dropna(subset=['Idade'])
        
        # Definir faixas etárias
        bins = [18, 25, 30, 35, 40, 45, 50, 55, 60]
        labels = ['18-25', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '56+']
        
        # Categorizar idades
        df_idade['Faixa Etária'] = pd.cut(df_idade['Idade'], bins=bins, labels=labels, right=True)
        
        # Contagem por faixa etária
        contagem = df_idade['Faixa Etária'].value_counts().sort_index()
        percentual = (contagem / contagem.sum() * 100).round(2)
        
        tabela_faixas = pd.DataFrame({
            'Faixa Etária': contagem.index,
            'Quantidade': contagem.values,
            'Percentual (%)': percentual.values
        })
        
        st.dataframe(tabela_faixas, use_container_width=True)

else:  # Distribuição por Posto/Graduação
    st.subheader("Distribuição por Posto/Graduação")
    fig = criar_grafico_distribuicao_cargo(df)
    
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
        
        # Contagem por cargo
        contagem = df['Cargo'].value_counts()
        percentual = (contagem / contagem.sum() * 100).round(2)
        
        tabela_cargos = pd.DataFrame({
            'Posto/Graduação': contagem.index,
            'Quantidade': contagem.values,
            'Percentual (%)': percentual.values
        })
        
        st.dataframe(tabela_cargos, use_container_width=True)

# Rodapé
st.markdown("---")
st.markdown("**Dashboard desenvolvido para o Corpo de Bombeiros Militar do Paraná**")
st.markdown("💻 Para mais informações, consulte o repositório no GitHub")
