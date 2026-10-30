
import os
import streamlit as st
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from dotenv import load_dotenv

# Carrega as variáveis definidas no arquivo .env
load_dotenv()


# --------------------------------------------------
# Configurações gerais do aplicativo
# --------------------------------------------------

st.set_page_config(
    page_title="BrewInspector",
    page_icon="📊",
    layout="wide"
)


# --------------------------------------------------
# Apresentação do aplicativo
# --------------------------------------------------

# --------------------------------------------------
# Cabeçalho
# --------------------------------------------------

st.divider()

st.markdown(
    """
    <div style="text-align: center; color: gray; font-size: 12px;">
        Desenvolvido por Denis W. da Silva<br>
        © 2026 Denis W. da Silva. Todos os direitos reservados.
    </div>
    """,
    unsafe_allow_html=True
)
st.divider()
# --------------------------------------------------

st.title("🍺📊 BrewInspector - Dashboard")
st.subheader("Análise de Receitas Cervejeiras")

st.write(
    "Explore dados de 415 receitas cervejeiras do catálogo [DIY Dog](https://github.com/alxiw/punkapi) da "
    "cervejaria escocesa BrewDog, com análises gráficas sobre ingredientes e características das receitas."
)


# --------------------------------------------------
# Conexão com o PostgreSQL
# --------------------------------------------------

def conectar_banco():
    """
    Abre uma nova conexão com o PostgreSQL.
    A URL é obtida do .env local ou dos Secrets do Streamlit.
    """
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        try:
            database_url = st.secrets["DATABASE_URL"]
        except (FileNotFoundError, KeyError):
            database_url = None

    if not database_url:
        raise ValueError("DATABASE_URL não foi configurada.")

    return psycopg2.connect(database_url)


# --------------------------------------------------
# Consultas ao banco de dados
# --------------------------------------------------

@st.cache_data(ttl=600)
def carregar_lupulos(limite):
    """
    Retorna os lúpulos mais utilizados no catálogo.
    O resultado fica em cache por 10 minutos.
    """
    conn = conectar_banco()

    try:
        query = """
            SELECT nome_lupulo, COUNT(*) AS vezes_usado
            FROM tab_lupulos
            GROUP BY nome_lupulo
            ORDER BY vezes_usado DESC
            LIMIT %s;
        """

        return pd.read_sql_query(query, conn, params=(limite,))

    finally:
        conn.close()


@st.cache_data(ttl=600)
def carregar_ibu(coluna_ibu):
    """
    Calcula o IBU médio por faixa de ABV.
    O resultado fica em cache por 10 minutos.
    """
    # A conexão é aberta somente quando a consulta precisa ser executada.
    conn = conectar_banco()

    try:
        query = f"""
            SELECT
                CASE
                    WHEN abv < 5 THEN 'Baixo (<5%)'
                    WHEN abv < 8 THEN 'Médio (5-8%)'
                    ELSE 'Alto (8%+)'
                END AS faixa_abv,
                ROUND(AVG({coluna_ibu})::numeric, 1) AS ibu_medio
            FROM tab_cervejas
            WHERE abv IS NOT NULL
              AND {coluna_ibu} IS NOT NULL
            GROUP BY faixa_abv
            ORDER BY MIN(abv);
        """

        return pd.read_sql_query(query, conn)

    finally:
        conn.close()

@st.cache_data(ttl=600)
def carregar_maltes(limite):
    """Retorna os maltes mais utilizados nas receitas."""
    conn = conectar_banco()
    try:
        query = """
            SELECT nome_malte, COUNT(*) AS vezes_usado
            FROM tab_maltes
            GROUP BY nome_malte
            ORDER BY vezes_usado DESC
            LIMIT %s;
        """
        return pd.read_sql_query(query, conn, params=(limite,))
    finally:
        conn.close()


@st.cache_data(ttl=600)
def carregar_abv():
    """Retorna os valores de ABV das receitas."""
    conn = conectar_banco()
    try:
        query = """
            SELECT abv
            FROM tab_cervejas
            WHERE abv IS NOT NULL;
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


@st.cache_data(ttl=600)
def carregar_distribuicao_ibu(coluna_ibu):
    """Retorna os valores da métrica de IBU selecionada."""
    conn = conectar_banco()
    try:
        query = f"""
            SELECT {coluna_ibu}
            FROM tab_cervejas
            WHERE {coluna_ibu} IS NOT NULL;
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()

def exibir_distribuicao(df, coluna, titulo, rotulo_eixo, cor, sufixo=""):
# Colocar cache nessa função não é adequado, pois queremos que a interface seja reconstruída normalmente conforme o usuário altera o slider
    """
    Exibe um histograma interativo com a distribuição dos valores.
    Valores acima do percentil 99 são omitidos apenas da visualização.
    """

    st.header(titulo)

    # Define a quantidade de intervalos do histograma
    numero_intervalos = st.slider(
        "Número de intervalos:",
        min_value=5,
        max_value=30,
        value=15,
        step=1
    )

    # Limita a visualização ao percentil 99,3 
    # no ABV: mostra até o de 18.3% e não mostra 32.0%, 41.0% e 55.0%, que deixariam um vazio enorme no gráfico
    # no IBU: mostra até 250 e não mostra os 1085.0 e 1157.0, que também deixariam uma região vazia enorme no gráfico
    limite_superior = df[coluna].quantile(0.993)

    valores_visiveis = df.loc[
        df[coluna] <= limite_superior, coluna
    ]

    # Identifica os valores extremos que não serão exibidos
    valores_extremos = df.loc[
        df[coluna] > limite_superior, coluna
    ].sort_values()

    # Calcula as frequências e os limites de cada intervalo
    frequencias, limites = np.histogram(
        valores_visiveis,
        bins=numero_intervalos
    )

    # Calcula o centro e a largura de cada intervalo
    centros = (limites[:-1] + limites[1:]) / 2
    larguras = np.diff(limites)

    # Armazena os limites para exibição ao passar o mouse
    intervalos = np.column_stack((limites[:-1], limites[1:]))

    # Cria o gráfico de barras interativo
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=centros,
        y=frequencias,
        width=larguras,
        marker_color=cor,
        marker_line_color="white",
        marker_line_width=1,
        customdata=intervalos,
        hovertemplate=(
            f"Intervalo: %{{customdata[0]:.1f}} – "
            f"%{{customdata[1]:.1f}}{sufixo}"
            "<br>Receitas: %{y}"
            "<extra></extra>"
        )
    ))

    # Informa resumidamente por que os valores extremos não foram exibidos
    if not valores_extremos.empty:
        fig.add_annotation(
            x=0.98,
            y=0.95,
            xref="paper",
            yref="paper",
            text=(
                f"{len(valores_extremos)} valores extremos omitidos "
                f"(acima de {limite_superior:.1f}{sufixo})"
            ),
            showarrow=False,
            xanchor="right",
            yanchor="top",
            font=dict(size=27, color="#555555"),
            align="right"
        )

    # Ajusta os eixos e a disposição dos elementos
    fig.update_layout(
        xaxis_title=rotulo_eixo,
        yaxis_title="Quantidade de receitas",
        template="plotly_white",
        height=500,
        bargap=0.05,
        margin=dict(l=60, r=30, t=40, b=60),
        hoverlabel=dict(font_size=16)
    )

    fig.update_yaxes(
        rangemode="tozero",
        tickformat="d"
    )

    st.caption(
        "Passe o mouse sobre as barras para consultar "
        "os intervalos e a quantidade de receitas."
    )

    st.plotly_chart(fig, use_container_width=True)

    # Informa quais valores foram omitidos e por quê
    if not valores_extremos.empty:
        lista_extremos = ", ".join(
            f"{valor:.1f}{sufixo}" for valor in valores_extremos
        )

        st.warning(
            f"Os valores {lista_extremos} foram omitidos do histograma "
            "porque ampliariam excessivamente a escala horizontal, "
            "dificultando a visualização da distribuição das demais receitas. "
            "Os dados originais foram preservados."
        )


# --------------------------------------------------
# Paletas de cores
# --------------------------------------------------

paletas_lupulos = {
    "Verde": "Greens",
    "Preto e branco": "Greys",
    "Cobre": "copper",
    "Arco-íris": "rainbow",
    "Rosa e verde": "PiYG",
    "Azul e vermelho": "coolwarm"
}

paletas_maltes = {
    "Amarelo dourado": "Wistia",
    "Preto e branco": "Greys",
    "Cobre": "copper",
    "Arco-íris": "rainbow",
    "Rosa e verde": "PiYG",
    "Azul e vermelho": "coolwarm"
}

paletas_ibu = {
    "Amarelo e marrom": "YlOrBr",
    "Verde": "Greens",
    "Preto e branco": "Greys",
    "Cobre": "copper",
    "Arco-íris": "rainbow",
    "Rosa e verde": "PiYG",
    "Azul e vermelho": "coolwarm"
}

paletas_abv = {
    "Amarelo e marrom": "YlOrBr",
    "Preto e branco": "Greys",
    "Cobre": "copper",
    "Arco-íris": "rainbow",
    "Rosa e verde": "PiYG",
    "Azul e vermelho": "coolwarm"
}

paletas_distribuicao_ibu = {
    "Verde": "Greens",
    "Amarelo e marrom": "YlOrBr",
    "Preto e branco": "Greys",
    "Cobre": "copper",
    "Arco-íris": "rainbow",
    "Rosa e verde": "PiYG",
    "Azul e vermelho": "coolwarm"
}


# --------------------------------------------------
# Geração das cores dos gráficos
# --------------------------------------------------

def gerar_cores(valores, nome_paleta):
    """
    Distribui as cores de uma paleta de acordo com os valores.
    Permite inverter a escala e ajustar seus limites para evitar
    cores extremas que prejudiquem a leitura do gráfico.
    """
    cmap = plt.get_cmap(nome_paleta)

    if valores.max() == valores.min():
        normalizados = pd.Series([0.5] * len(valores))
    else:
        normalizados = (
            (valores - valores.min()) /
            (valores.max() - valores.min())
        )

    # Ajusta a escala de cores conforme a paleta selecionada.
    if nome_paleta == "rainbow":
        normalizados = 1 - normalizados

    elif nome_paleta == "Greys" or nome_paleta == "Greens" or nome_paleta == "YlOrBr":
        normalizados = 0.30 + normalizados * 0.70 # o limite inferior de 30% impede que a barra mais clara desapareça no fundo branco

    elif nome_paleta == "copper":
        normalizados = 0.15 + normalizados * 0.70 # limitar a escala aqui também evita os extremos muito claros e muito escuros
        normalizados = 1 - normalizados

    elif nome_paleta == "PiYG":
        normalizados = 0.15 + normalizados * 0.70 # limita a escala aos 15%–85%, evitando que a barra intermediária fique praticamente branca
        normalizados = 1 - normalizados

    return cmap(normalizados)


# --------------------------------------------------
# Seleção da análise
# --------------------------------------------------

st.divider()

analise = st.selectbox(
    "Selecione a análise que deseja visualizar:",
    [
        "Lúpulos mais utilizados",
        "Maltes mais utilizados",
        "IBU por faixa de ABV",
        "Distribuição do teor alcoólico (ABV)",
        "Distribuição do IBU"
    ]
)

# A seleção de IBU será usada tanto no gráfico de média quanto no histograma
metricas_ibu = {
    "IBU Percebido (Limite máximo prático de 120 para o paladar humano)": "ibu_percebido",
    "IBU Técnico (Valor teórico calculado em laboratório)": "ibu"
}

# --------------------------------------------------
# Gráfico 1 - Lúpulos mais utilizados
# --------------------------------------------------

if analise == "Lúpulos mais utilizados":

    st.header("Top lúpulos mais utilizados nas receitas")

    # # Usa um menu de dropdown pra definir a quantidade de resultados exibidos
    # limite_lupulos = st.selectbox(
    #     "Quantidade de lúpulos:",
    #     options=list(range(1, 21)),
    #     index=9
    # )

    # # Usa um slider pra definir a quantidade de resultados exibidos
    limite_lupulos = st.slider(
        "Quantidade de lúpulos:",
        min_value=1,
        max_value=20,
        value=10,
        step=1
    )

    # Permite selecionar a paleta de cores do gráfico
    paleta = st.selectbox(
        "Paleta de cores:",
        options=list(paletas_lupulos.keys()),
        index=0
    )

    df_lupulos = carregar_lupulos(limite_lupulos)

    # Gera uma cor para cada barra de acordo com sua frequência
    cores_barras = gerar_cores(
        df_lupulos["vezes_usado"],
        paletas_lupulos[paleta]
    )

    # Cria o gráfico de barras horizontais
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.barh(
        df_lupulos["nome_lupulo"],
        df_lupulos["vezes_usado"],
        color=cores_barras
    )

    # Adiciona os valores ao lado das barras
    for bar in ax.patches:
        largura = bar.get_width()

        ax.text(
            largura + df_lupulos["vezes_usado"].max() * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{int(largura)}",
            ha="left",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="#333333"
        )

    # Ajusta os eixos e a disposição dos elementos
    ax.set_xlim(0, df_lupulos["vezes_usado"].max() * 1.12)
    ax.set_xlabel("Vezes utilizado")
    ax.set_ylabel("")
    ax.invert_yaxis()

    fig.tight_layout()

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)



# --------------------------------------------------
# Gráfico 2 - Maltes mais utilizados
# --------------------------------------------------

elif analise == "Maltes mais utilizados":

    st.header("Top maltes mais utilizados nas receitas")

    # # Define a quantidade de resultados exibidos
    # limite_maltes = st.selectbox(
    #     "Quantidade de maltes:",
    #     options=list(range(1, 21)),
    #     index=9
    # )

    # # Usa um slider pra definir a quantidade de resultados exibidos
    limite_maltes = st.slider(
        "Quantidade de maltes:",
        min_value=1,
        max_value=20,
        value=10,
        step=1
    )

    # Permite selecionar a paleta de cores do gráfico
    paleta = st.selectbox(
        "Paleta de cores:",
        options=list(paletas_maltes.keys()),
        index=0
    )

    df_maltes = carregar_maltes(limite_maltes)

    # Gera uma cor para cada barra de acordo com sua frequência
    cores_barras = gerar_cores(
        df_maltes["vezes_usado"],
        paletas_maltes[paleta]
    )

    # Cria o gráfico de barras horizontais
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.barh(
        df_maltes["nome_malte"],
        df_maltes["vezes_usado"],
        color=cores_barras # barras com gradiente de cor
        # color=plt.get_cmap("Wistia")(0.55) # cor fixa se quisermos evitar a associação entre frequência e cor do malte
    )

    # Adiciona os valores ao lado das barras
    for bar in ax.patches:
        largura = bar.get_width()

        ax.text(
            largura + df_maltes["vezes_usado"].max() * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{int(largura)}",
            ha="left",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="#333333"
        )

    # Ajusta os eixos e a disposição dos elementos
    ax.set_xlim(0, df_maltes["vezes_usado"].max() * 1.12)
    ax.set_xlabel("Vezes utilizado")
    ax.set_ylabel("")
    ax.invert_yaxis()

    fig.tight_layout()

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)



# --------------------------------------------------
# Gráfico 3 - IBU por faixa de ABV
# --------------------------------------------------

elif analise == "IBU por faixa de ABV":

    st.header("IBU médio por faixa de ABV")


    metrica_selecionada = st.selectbox(
        "Métrica de amargor:",
        options=list(metricas_ibu.keys()),
        index=0
    )

    coluna_ibu = metricas_ibu[metrica_selecionada]

    # Permite selecionar a paleta de cores do gráfico
    paleta = st.selectbox(
        "Paleta de cores:",
        options=list(paletas_ibu.keys()),
        index=0
    )

    df_ibu = carregar_ibu(coluna_ibu)

    # Gera uma cor para cada barra de acordo com o IBU médio
    cores_barras = gerar_cores(
        df_ibu["ibu_medio"],
        paletas_ibu[paleta]
    )

    # Cria o gráfico de barras verticais
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.bar(
        df_ibu["faixa_abv"],
        df_ibu["ibu_medio"],
        color=cores_barras
    )

    # Adiciona os valores acima das barras
    for bar in ax.patches:
        altura = bar.get_height()

        ax.text(
            bar.get_x() + bar.get_width() / 2,
            altura + df_ibu["ibu_medio"].max() * 0.015,
            f"{altura:.1f}",
            ha="center",
            va="bottom",
            fontsize=11,
            color="#333333"
        )

    # Ajusta os eixos e a disposição dos elementos
    ax.set_ylim(0, df_ibu["ibu_medio"].max() * 1.12)
    ax.set_xlabel("Faixa de teor alcoólico (ABV)")
    ax.set_ylabel(str(f"{metrica_selecionada} médio").split("(")[0])
    ax.tick_params(axis="x", rotation=30)

    fig.tight_layout()

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# --------------------------------------------------
# Gráfico 4 - Distribuição do teor alcoólico (ABV)
# --------------------------------------------------

elif analise == "Distribuição do teor alcoólico (ABV)":

    df_abv = carregar_abv()

    exibir_distribuicao(
        df=df_abv,
        coluna="abv",
        titulo="Distribuição do teor alcoólico das receitas",
        rotulo_eixo="Teor alcoólico (ABV, %)",
        cor="#8c6bb1",
        sufixo="%"
    )

# --------------------------------------------------
# Gráfico 5 - Distribuição do IBU
# --------------------------------------------------

elif analise == "Distribuição do IBU":

    # Permite selecionar a métrica de IBU
    metrica_selecionada = st.selectbox(
        "Métrica de IBU:",
        options=list(metricas_ibu.keys())
    )

    coluna_ibu = metricas_ibu[metrica_selecionada]

    # Identifica a métrica selecionada sem incluir a explicação entre parênteses
    nome_metrica = metrica_selecionada.split("(")[0].strip()

    df_ibu = carregar_distribuicao_ibu(coluna_ibu)

    exibir_distribuicao(
        df=df_ibu,
        coluna=coluna_ibu,
        titulo="Distribuição dos valores de IBU",
        rotulo_eixo=nome_metrica,
        cor="#41ab5d"
    )