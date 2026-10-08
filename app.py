from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st
from sqlalchemy import ForeignKey, String, create_engine, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

st.set_page_config(
    page_title="Análise Climática do Brasil",
    page_icon="🌦️",
    layout="wide",
)

sns.set_theme(style="whitegrid")

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_CSV = BASE_DIR / "dados" / "simulacao_clima_brasil.csv"
CAMINHO_LOCALIDADES = BASE_DIR / "dados" / "localidades.csv"
CAMINHO_BANCO = BASE_DIR / "database" / "clima.db"

ORDEM_ALERTA = ["Baixo", "Médio", "Alto", "Crítico"]
MAPA_ALERTA = {nivel: indice + 1 for indice, nivel in enumerate(ORDEM_ALERTA)}
CORES_ALERTA = {
    "Baixo": "#2ca02c",
    "Médio": "#f1c40f",
    "Alto": "#e67e22",
    "Crítico": "#c0392b",
}
ESTACOES = {
    12: "Verão", 1: "Verão", 2: "Verão",
    3: "Outono", 4: "Outono", 5: "Outono",
    6: "Inverno", 7: "Inverno", 8: "Inverno",
    9: "Primavera", 10: "Primavera", 11: "Primavera",
}
MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
VARIAVEIS = {
    "temperatura_media": "Temperatura média (°C)",
    "temperatura_maxima": "Temperatura máxima (°C)",
    "temperatura_minima": "Temperatura mínima (°C)",
    "amplitude_termica": "Amplitude térmica (°C)",
    "chuva_mm": "Chuva (mm)",
    "umidade": "Umidade (%)",
    "velocidade_vento": "Velocidade do vento",
    "eventos_extremos": "Eventos extremos",
}
VARIAVEIS_MAPA = [
    "temperatura_media",
    "amplitude_termica",
    "chuva_mm",
    "umidade",
    "velocidade_vento",
    "eventos_extremos",
]
ESCALAS_MAPA = {
    "chuva_mm": "Blues",
    "umidade": "Blues",
    "velocidade_vento": "Purples",
    "eventos_extremos": "OrRd",
}
VARIAVEIS_TEMPERATURA = {
    "temperatura_media",
    "temperatura_maxima",
    "temperatura_minima",
    "amplitude_termica",
}
ROTULOS_CORRELACAO = {**VARIAVEIS, "alerta_num": "Nível de alerta (1 a 4)"}

CONSULTA = """
SELECT
    r.id, r.data, r.ano, r.mes,
    l.regiao, l.uf, l.cidade, l.latitude, l.longitude,
    r.temperatura_media, r.temperatura_maxima, r.temperatura_minima,
    r.chuva_mm, r.umidade, r.velocidade_vento,
    r.eventos_extremos, r.nivel_alerta
FROM registros_clima r
INNER JOIN localidades l ON l.id = r.localidade_id
ORDER BY r.data, l.cidade
"""

COLUNAS_REGISTROS = [
    "localidade_id", "data", "ano", "mes",
    "temperatura_media", "temperatura_maxima", "temperatura_minima",
    "chuva_mm", "umidade", "velocidade_vento",
    "eventos_extremos", "nivel_alerta",
]


class Base(DeclarativeBase):
    pass


class Localidade(Base):
    __tablename__ = "localidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    cidade: Mapped[str] = mapped_column(String(80), unique=True)
    uf: Mapped[str] = mapped_column(String(2))
    regiao: Mapped[str] = mapped_column(String(20))
    latitude: Mapped[float]
    longitude: Mapped[float]


class RegistroClima(Base):
    __tablename__ = "registros_clima"

    id: Mapped[int] = mapped_column(primary_key=True)
    localidade_id: Mapped[int] = mapped_column(ForeignKey("localidades.id"))
    data: Mapped[str] = mapped_column(String(10))
    ano: Mapped[int]
    mes: Mapped[int]
    temperatura_media: Mapped[float]
    temperatura_maxima: Mapped[float]
    temperatura_minima: Mapped[float]
    chuva_mm: Mapped[float]
    umidade: Mapped[float]
    velocidade_vento: Mapped[float]
    eventos_extremos: Mapped[int]
    nivel_alerta: Mapped[str] = mapped_column(String(10))


def popular_banco(engine):
    with engine.begin() as conexao:
        conexao.execute(delete(RegistroClima))
        conexao.execute(delete(Localidade))
    localidades = pd.read_csv(CAMINHO_LOCALIDADES)
    localidades.to_sql("localidades", engine, if_exists="append", index=False)
    ids = pd.read_sql("SELECT id AS localidade_id, cidade FROM localidades", engine)
    registros = pd.read_csv(CAMINHO_CSV).merge(ids, on="cidade", how="left")
    registros[COLUNAS_REGISTROS].to_sql(
        "registros_clima", engine, if_exists="append", index=False
    )


@st.cache_resource
def obter_engine():
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{CAMINHO_BANCO.as_posix()}")
    Base.metadata.create_all(engine)
    with engine.connect() as conexao:
        total = conexao.execute(select(func.count(RegistroClima.id))).scalar()
    if not total:
        popular_banco(engine)
    return engine


def engenharia_atributos(df):
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    df["amplitude_termica"] = df["temperatura_maxima"] - df["temperatura_minima"]
    df["estacao"] = df["mes"].map(ESTACOES)
    df["alerta_num"] = df["nivel_alerta"].map(MAPA_ALERTA)
    df["alerta_alto_critico"] = df["alerta_num"] >= 3
    return df


@st.cache_data(show_spinner="Carregando dados do banco...")
def carregar_dados():
    engine = obter_engine()
    bruto = pd.read_sql(CONSULTA, engine)
    return engenharia_atributos(bruto)


def fmt(valor, casas=1):
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def mostrar(figura):
    st.pyplot(figura)
    plt.close(figura)


def calcular_kpis(d):
    return {
        "temperatura": d["temperatura_media"].mean(),
        "chuva": d["chuva_mm"].mean(),
        "umidade": d["umidade"].mean(),
        "amplitude": d["amplitude_termica"].mean(),
        "eventos_total": int(d["eventos_extremos"].sum()),
        "eventos_media": d["eventos_extremos"].mean(),
        "pct_alerta": d["alerta_alto_critico"].mean() * 100,
        "registros": len(d),
    }


def tendencia_anual(serie):
    if len(serie) < 3:
        return None
    x = np.arange(len(serie))
    coeficientes = np.polyfit(x, serie.values, 1)
    return coeficientes


def classificar_correlacao(r):
    if np.isnan(r):
        return "indefinida"
    a = abs(r)
    if a < 0.1:
        return "desprezível"
    if a < 0.3:
        return "fraca"
    if a < 0.5:
        return "moderada"
    if a < 0.7:
        return "forte"
    return "muito forte"


def pares_correlacao(corr):
    colunas = list(corr.columns)
    linhas = []
    for a, b in combinations(colunas, 2):
        r = corr.loc[a, b]
        linhas.append(
            {
                "Variável A": ROTULOS_CORRELACAO[a],
                "Variável B": ROTULOS_CORRELACAO[b],
                "Correlação": round(float(r), 3),
                "Intensidade": classificar_correlacao(r),
                "mecanica": a in VARIAVEIS_TEMPERATURA and b in VARIAVEIS_TEMPERATURA,
            }
        )
    tabela = pd.DataFrame(linhas)
    return tabela.sort_values("Correlação", key=lambda s: s.abs(), ascending=False)


df = carregar_dados()
kpis_base = calcular_kpis(df)

st.title("Análise Climática do Brasil (2015–2024)")
st.caption(
    "Aluno(a): Miguel Garcia | "
    "Disciplina: Linguagem de Programação | "
    "Turma: Quinta/noite"
)

st.header("Descrição do problema")
st.markdown(
    """
O clima brasileiro varia bastante entre regiões, cidades e épocas do ano. Entender como
temperatura, chuva, umidade, vento e eventos extremos se comportam ao longo do tempo ajuda
a identificar regiões mais expostas a riscos e apoia o planejamento de ações de prevenção.

Este dashboard analisa uma **base simulada** com 37 cidades de 20 unidades federativas,
em registros mensais de janeiro de 2015 a dezembro de 2024. Os dados ficam armazenados em um
banco **SQLite** (modelado com **SQLAlchemy**) e são integrados a uma tabela de coordenadas
geográficas das cidades.

**Perguntas que o dashboard responde:**
1. Como estão distribuídas as variáveis climáticas e os níveis de alerta?
2. Existe tendência ou sazonalidade ao longo dos anos e dos meses?
3. Quais regiões, estados e cidades se destacam em temperatura, chuva e eventos extremos?
4. Onde estão localizadas as cidades com maiores valores de cada indicador?
5. Quais variáveis se relacionam entre si?
"""
)

st.sidebar.header("Filtros")

regioes = sorted(df["regiao"].unique())
regioes_sel = st.sidebar.multiselect("Região", regioes, default=regioes)

ufs_disponiveis = sorted(df[df["regiao"].isin(regioes_sel)]["uf"].unique())
ufs_sel = st.sidebar.multiselect("UF", ufs_disponiveis, default=ufs_disponiveis)

cidades_disponiveis = sorted(
    df[df["regiao"].isin(regioes_sel) & df["uf"].isin(ufs_sel)]["cidade"].unique()
)
cidades_sel = st.sidebar.multiselect(
    "Cidade", cidades_disponiveis, default=cidades_disponiveis
)

ano_min = int(df["ano"].min())
ano_max = int(df["ano"].max())
ano_inicio, ano_fim = st.sidebar.slider(
    "Período (anos)", ano_min, ano_max, (ano_min, ano_max)
)

alertas_sel = st.sidebar.multiselect(
    "Nível de alerta", ORDEM_ALERTA, default=ORDEM_ALERTA
)

filtro = (
    df["regiao"].isin(regioes_sel)
    & df["uf"].isin(ufs_sel)
    & df["cidade"].isin(cidades_sel)
    & df["ano"].between(ano_inicio, ano_fim)
    & df["nivel_alerta"].isin(alertas_sel)
)
dff = df[filtro]

if dff.empty:
    st.warning("Nenhum registro encontrado com os filtros selecionados. Ajuste os filtros na barra lateral.")
    st.stop()

st.sidebar.caption(f"{fmt(len(dff), 0)} de {fmt(len(df), 0)} registros selecionados")

kpis = calcular_kpis(dff)

st.header("Indicadores (KPIs)")
linha1 = st.columns(4)
linha1[0].metric(
    "Temperatura média",
    f"{fmt(kpis['temperatura'])} °C",
    f"{kpis['temperatura'] - kpis_base['temperatura']:+.2f} °C vs. base completa",
    delta_color="off",
)
linha1[1].metric(
    "Chuva média mensal",
    f"{fmt(kpis['chuva'])} mm",
    f"{kpis['chuva'] - kpis_base['chuva']:+.1f} mm vs. base completa",
    delta_color="off",
)
linha1[2].metric(
    "Umidade média",
    f"{fmt(kpis['umidade'])} %",
    f"{kpis['umidade'] - kpis_base['umidade']:+.1f} p.p. vs. base completa",
    delta_color="off",
)
linha1[3].metric(
    "Amplitude térmica média",
    f"{fmt(kpis['amplitude'])} °C",
    f"{kpis['amplitude'] - kpis_base['amplitude']:+.2f} °C vs. base completa",
    delta_color="off",
)

linha2 = st.columns(4)
linha2[0].metric("Eventos extremos (total)", fmt(kpis["eventos_total"], 0))
linha2[1].metric(
    "Eventos por cidade/mês",
    fmt(kpis["eventos_media"], 2),
    f"{kpis['eventos_media'] - kpis_base['eventos_media']:+.2f} vs. base completa",
    delta_color="off",
)
linha2[2].metric(
    "Alertas Alto ou Crítico",
    f"{fmt(kpis['pct_alerta'])} %",
    f"{kpis['pct_alerta'] - kpis_base['pct_alerta']:+.1f} p.p. vs. base completa",
    delta_color="off",
)
linha2[3].metric("Registros analisados", fmt(kpis["registros"], 0))

abas = st.tabs(
    [
        "Visão geral",
        "Análise temporal",
        "Comparativos",
        "Mapa interativo",
        "Correlações",
        "Dados",
    ]
)

with abas[0]:
    st.subheader("Distribuição das variáveis")
    var_dist = st.selectbox(
        "Variável",
        list(VARIAVEIS),
        format_func=lambda v: VARIAVEIS[v],
        key="var_dist",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.histplot(
            data=dff,
            x=var_dist,
            discrete=var_dist == "eventos_extremos",
            kde=var_dist != "eventos_extremos",
            color="#1f77b4",
            ax=ax,
        )
        ax.set_title(f"Distribuição de {VARIAVEIS[var_dist]}")
        ax.set_xlabel(VARIAVEIS[var_dist])
        ax.set_ylabel("Frequência")
        mostrar(fig)

    with col_b:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.countplot(
            data=dff,
            x="nivel_alerta",
            order=ORDEM_ALERTA,
            hue="nivel_alerta",
            hue_order=ORDEM_ALERTA,
            palette=CORES_ALERTA,
            legend=False,
            ax=ax,
        )
        ax.set_title("Registros por nível de alerta")
        ax.set_xlabel("Nível de alerta")
        ax.set_ylabel("Quantidade de registros")
        mostrar(fig)

    serie_dist = dff[var_dist]
    media = serie_dist.mean()
    mediana = serie_dist.median()
    desvio = serie_dist.std()
    coef_var = desvio / media * 100 if media != 0 else float("nan")
    contagem_alerta = dff["nivel_alerta"].value_counts()
    nivel_freq = contagem_alerta.idxmax()
    st.info(
        f"**Interpretação:** na seleção atual, {VARIAVEIS[var_dist]} tem média de "
        f"{fmt(media, 2)} e mediana de {fmt(mediana, 2)}, com desvio padrão de {fmt(desvio, 2)} "
        f"(coeficiente de variação de {fmt(coef_var)} %). "
        f"Quando média e mediana são próximas, a distribuição é aproximadamente simétrica. "
        f"O nível de alerta mais frequente é **{nivel_freq}**, com "
        f"{fmt(contagem_alerta.max() / len(dff) * 100)} % dos registros."
    )

    st.subheader("Resumo estatístico")
    resumo = dff[list(VARIAVEIS)].describe().T.round(2)
    resumo = resumo.rename(
        columns={
            "count": "Contagem",
            "mean": "Média",
            "std": "Desvio padrão",
            "min": "Mínimo",
            "25%": "1º quartil",
            "50%": "Mediana",
            "75%": "3º quartil",
            "max": "Máximo",
        },
        index=VARIAVEIS,
    )
    st.dataframe(resumo)

with abas[1]:
    st.subheader("Evolução ao longo do tempo")
    var_t = st.selectbox(
        "Variável",
        list(VARIAVEIS),
        format_func=lambda v: VARIAVEIS[v],
        key="var_temporal",
    )

    serie = dff.groupby("data")[var_t].mean().sort_index()
    media_movel = serie.rolling(12, min_periods=1).mean()
    coeficientes = tendencia_anual(serie)

    fig_t = go.Figure()
    fig_t.add_trace(
        go.Scatter(
            x=serie.index,
            y=serie.values,
            mode="lines",
            name="Média mensal",
            line=dict(width=1.2, color="#9ecae1"),
        )
    )
    fig_t.add_trace(
        go.Scatter(
            x=serie.index,
            y=media_movel.values,
            mode="lines",
            name="Média móvel (12 meses)",
            line=dict(width=3, color="#08519c"),
        )
    )
    if coeficientes is not None:
        fig_t.add_trace(
            go.Scatter(
                x=serie.index,
                y=np.polyval(coeficientes, np.arange(len(serie))),
                mode="lines",
                name="Tendência linear",
                line=dict(width=2, dash="dash", color="#c0392b"),
            )
        )
    fig_t.update_layout(
        title=f"{VARIAVEIS[var_t]}: média mensal, média móvel e tendência",
        xaxis_title="Data",
        yaxis_title=VARIAVEIS[var_t],
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25),
    )
    st.plotly_chart(fig_t)

    por_mes = dff.groupby("mes")[var_t].mean()
    mes_max = int(por_mes.idxmax())
    mes_min = int(por_mes.idxmin())
    variacao_sazonal = (por_mes.max() - por_mes.min()) / abs(por_mes.mean()) * 100
    if coeficientes is not None:
        variacao_anual = coeficientes[0] * 12
        texto_tendencia = (
            f"A tendência linear indica variação de {variacao_anual:+.3f} por ano em "
            f"{VARIAVEIS[var_t]}, ou {variacao_anual * 10:+.2f} ao longo de dez anos."
        )
    else:
        texto_tendencia = "Há poucos meses selecionados para estimar uma tendência linear."
    if variacao_sazonal < 10:
        texto_sazonal = "a variação sazonal é pequena"
    else:
        texto_sazonal = "há variação sazonal relevante"
    st.info(
        f"**Interpretação:** {texto_tendencia} Entre os meses do ano, a maior média ocorre em "
        f"{MESES[mes_max - 1]} ({fmt(por_mes.max(), 2)}) e a menor em {MESES[mes_min - 1]} "
        f"({fmt(por_mes.min(), 2)}); a diferença equivale a {fmt(variacao_sazonal)} % da média geral, "
        f"portanto {texto_sazonal}."
    )

    col_c, col_d = st.columns(2)
    with col_c:
        anual = dff.groupby(["ano", "regiao"], as_index=False)[var_t].mean()
        fig_a = px.line(
            anual,
            x="ano",
            y=var_t,
            color="regiao",
            markers=True,
            labels={"ano": "Ano", var_t: VARIAVEIS[var_t], "regiao": "Região"},
            title="Média anual por região",
        )
        st.plotly_chart(fig_a)

    with col_d:
        pivo = dff.pivot_table(index="ano", columns="mes", values=var_t, aggfunc="mean")
        fig, ax = plt.subplots(figsize=(8, 4.5))
        sns.heatmap(
            pivo,
            cmap="YlOrRd",
            annot=True,
            fmt=".1f",
            annot_kws={"size": 7},
            linewidths=0.4,
            cbar_kws={"label": VARIAVEIS[var_t]},
            ax=ax,
        )
        ax.set_title(f"Mapa de calor: {VARIAVEIS[var_t]} por ano e mês")
        ax.set_xlabel("Mês")
        ax.set_ylabel("Ano")
        mostrar(fig)

with abas[2]:
    st.subheader("Comparativos entre regiões, estados e cidades")
    var_c = st.selectbox(
        "Variável",
        list(VARIAVEIS),
        format_func=lambda v: VARIAVEIS[v],
        key="var_comparativo",
    )

    col_e, col_f = st.columns(2)
    with col_e:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.boxplot(
            data=dff,
            x="regiao",
            y=var_c,
            hue="regiao",
            palette="Set2",
            legend=False,
            ax=ax,
        )
        ax.set_title(f"{VARIAVEIS[var_c]} por região")
        ax.set_xlabel("Região")
        ax.set_ylabel(VARIAVEIS[var_c])
        mostrar(fig)

    with col_f:
        por_uf = (
            dff.groupby("uf", as_index=False)["eventos_extremos"]
            .mean()
            .sort_values("eventos_extremos", ascending=False)
        )
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.barplot(
            data=por_uf.head(15),
            x="uf",
            y="eventos_extremos",
            hue="uf",
            palette="viridis",
            legend=False,
            ax=ax,
        )
        ax.set_title("Eventos extremos por cidade/mês, por UF (top 15)")
        ax.set_xlabel("UF")
        ax.set_ylabel("Média de eventos extremos")
        mostrar(fig)

    media_regiao = dff.groupby("regiao")[var_c].mean().sort_values(ascending=False)
    eventos_regiao = dff.groupby("regiao")["eventos_extremos"].mean().sort_values(ascending=False)
    st.info(
        f"**Interpretação:** em {VARIAVEIS[var_c]}, a maior média regional é a da região "
        f"**{media_regiao.index[0]}** ({fmt(media_regiao.iloc[0], 2)}) e a menor é a da região "
        f"**{media_regiao.index[-1]}** ({fmt(media_regiao.iloc[-1], 2)}); a diferença é de "
        f"{fmt(media_regiao.iloc[0] - media_regiao.iloc[-1], 2)}. Quanto aos eventos extremos, "
        f"a maior média por cidade/mês aparece na região **{eventos_regiao.index[0]}** "
        f"({fmt(eventos_regiao.iloc[0], 2)}). Diferenças pequenas entre as caixas indicam "
        f"que as regiões se comportam de forma parecida."
    )

    tabela_alerta = (
        pd.crosstab(dff["regiao"], dff["nivel_alerta"], normalize="index")
        .reindex(columns=ORDEM_ALERTA, fill_value=0)
        * 100
    )
    tabela_alerta = tabela_alerta.reset_index().melt(
        id_vars="regiao", var_name="nivel_alerta", value_name="percentual"
    )
    fig_alerta = px.bar(
        tabela_alerta,
        x="regiao",
        y="percentual",
        color="nivel_alerta",
        category_orders={"nivel_alerta": ORDEM_ALERTA},
        color_discrete_map=CORES_ALERTA,
        barmode="stack",
        labels={"regiao": "Região", "percentual": "Percentual (%)", "nivel_alerta": "Nível de alerta"},
        title="Composição dos níveis de alerta por região",
    )
    st.plotly_chart(fig_alerta)

    st.subheader("Ranking de cidades")
    ranking = (
        dff.groupby(["cidade", "uf", "regiao"], as_index=False)
        .agg(
            temperatura_media=("temperatura_media", "mean"),
            chuva_media=("chuva_mm", "mean"),
            umidade_media=("umidade", "mean"),
            eventos_total=("eventos_extremos", "sum"),
            pct_alerta=("alerta_alto_critico", "mean"),
        )
        .sort_values("eventos_total", ascending=False)
    )
    ranking["pct_alerta"] = ranking["pct_alerta"] * 100
    ranking = ranking.round(2).rename(
        columns={
            "cidade": "Cidade",
            "uf": "UF",
            "regiao": "Região",
            "temperatura_media": "Temperatura média (°C)",
            "chuva_media": "Chuva média (mm)",
            "umidade_media": "Umidade média (%)",
            "eventos_total": "Eventos extremos (total)",
            "pct_alerta": "Alertas Alto/Crítico (%)",
        }
    )
    st.dataframe(ranking, hide_index=True)

with abas[3]:
    st.subheader("Mapa interativo das cidades")
    var_m = st.selectbox(
        "Variável representada pela cor",
        VARIAVEIS_MAPA,
        format_func=lambda v: VARIAVEIS[v],
        key="var_mapa",
    )

    agregacoes = {v: (v, "mean") for v in VARIAVEIS}
    agregacoes["eventos_total"] = ("eventos_extremos", "sum")
    cidades = dff.groupby(
        ["cidade", "uf", "regiao", "latitude", "longitude"], as_index=False
    ).agg(**agregacoes)
    cidades["tamanho"] = cidades["eventos_total"].clip(lower=1)

    fig_m = px.scatter_map(
        cidades,
        lat="latitude",
        lon="longitude",
        color=var_m,
        size="tamanho",
        size_max=28,
        hover_name="cidade",
        hover_data={
            "uf": True,
            "regiao": True,
            var_m: ":.2f",
            "eventos_total": True,
            "latitude": False,
            "longitude": False,
            "tamanho": False,
        },
        color_continuous_scale=ESCALAS_MAPA.get(var_m, "RdYlBu_r"),
        zoom=3,
        center={"lat": -14.5, "lon": -52.0},
        map_style="open-street-map",
        height=620,
        labels={var_m: VARIAVEIS[var_m], "eventos_total": "Eventos extremos (total)"},
    )
    fig_m.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_m)

    cidade_max = cidades.loc[cidades[var_m].idxmax()]
    cidade_min = cidades.loc[cidades[var_m].idxmin()]
    cidade_eventos = cidades.loc[cidades["eventos_total"].idxmax()]
    st.info(
        f"**Interpretação:** a cor de cada círculo representa a média de {VARIAVEIS[var_m]} "
        f"e o tamanho representa o total de eventos extremos. A maior média está em "
        f"**{cidade_max['cidade']} ({cidade_max['uf']})** com {fmt(cidade_max[var_m], 2)} e a menor em "
        f"**{cidade_min['cidade']} ({cidade_min['uf']})** com {fmt(cidade_min[var_m], 2)}. "
        f"A cidade com mais eventos extremos é **{cidade_eventos['cidade']} "
        f"({cidade_eventos['uf']})**, com {fmt(cidade_eventos['eventos_total'], 0)} ocorrências no período."
    )

with abas[4]:
    st.subheader("Correlação estatística")
    metodo = st.radio(
        "Método de correlação",
        ["pearson", "spearman"],
        horizontal=True,
        format_func=lambda m: m.capitalize(),
    )

    if len(dff) < 3:
        st.warning("Selecione mais registros para calcular correlações.")
    else:
        colunas_corr = list(VARIAVEIS) + ["alerta_num"]
        corr = dff[colunas_corr].corr(method=metodo)

        fig, ax = plt.subplots(figsize=(9, 7))
        sns.heatmap(
            corr.rename(index=ROTULOS_CORRELACAO, columns=ROTULOS_CORRELACAO),
            annot=True,
            fmt=".2f",
            annot_kws={"size": 8},
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            center=0,
            square=True,
            linewidths=0.5,
            ax=ax,
        )
        ax.set_title(f"Matriz de correlação ({metodo.capitalize()})")
        mostrar(fig)

        pares = pares_correlacao(corr)
        independentes = pares[~pares["mecanica"]]
        melhor = independentes.iloc[0]
        st.info(
            f"**Interpretação:** as variáveis de temperatura (média, máxima, mínima e amplitude) "
            f"são fortemente relacionadas entre si porque derivam umas das outras. Excluindo essas "
            f"relações, a maior correlação absoluta é entre **{melhor['Variável A']}** e "
            f"**{melhor['Variável B']}** (r = {fmt(melhor['Correlação'], 3)}), classificada como "
            f"**{melhor['Intensidade']}**. Correlação não implica causalidade."
        )

        st.subheader("Pares de variáveis mais correlacionados")
        st.dataframe(
            pares.drop(columns=["mecanica"]).head(15),
            hide_index=True,
        )

        st.subheader("Diagrama de dispersão")
        opcoes = list(VARIAVEIS)
        col_g, col_h = st.columns(2)
        eixo_x = col_g.selectbox(
            "Eixo X",
            opcoes,
            index=opcoes.index("temperatura_media"),
            format_func=lambda v: VARIAVEIS[v],
            key="eixo_x",
        )
        eixo_y = col_h.selectbox(
            "Eixo Y",
            opcoes,
            index=opcoes.index("chuva_mm"),
            format_func=lambda v: VARIAVEIS[v],
            key="eixo_y",
        )
        r_xy = float(np.corrcoef(dff[eixo_x], dff[eixo_y])[0, 1])

        fig, ax = plt.subplots(figsize=(8, 4.5))
        sns.regplot(
            data=dff,
            x=eixo_x,
            y=eixo_y,
            scatter_kws={"alpha": 0.25, "s": 12},
            line_kws={"color": "#c0392b"},
            ax=ax,
        )
        ax.set_title(f"{VARIAVEIS[eixo_y]} vs. {VARIAVEIS[eixo_x]}")
        ax.set_xlabel(VARIAVEIS[eixo_x])
        ax.set_ylabel(VARIAVEIS[eixo_y])
        mostrar(fig)
        st.info(
            f"**Interpretação:** o coeficiente de Pearson entre {VARIAVEIS[eixo_x]} e "
            f"{VARIAVEIS[eixo_y]} é {fmt(r_xy, 3)}, o que indica correlação "
            f"**{classificar_correlacao(r_xy)}**. A linha vermelha é a reta de regressão linear."
        )

with abas[5]:
    st.subheader("Tabela de dados filtrados")
    exportar = dff.drop(columns=["alerta_num", "alerta_alto_critico"]).copy()
    exportar["data"] = exportar["data"].dt.strftime("%Y-%m-%d")
    st.dataframe(exportar, hide_index=True)
    st.download_button(
        "Baixar dados filtrados (CSV)",
        data=exportar.to_csv(index=False).encode("utf-8-sig"),
        file_name="clima_filtrado.csv",
        mime="text/csv",
    )

    with st.expander("Dicionário de dados"):
        dicionario = pd.DataFrame(
            {
                "Coluna": [
                    "data", "ano", "mes", "regiao", "uf", "cidade", "latitude", "longitude",
                    "temperatura_media", "temperatura_maxima", "temperatura_minima",
                    "chuva_mm", "umidade", "velocidade_vento", "eventos_extremos",
                    "nivel_alerta", "amplitude_termica", "estacao",
                ],
                "Descrição": [
                    "Primeiro dia do mês do registro",
                    "Ano do registro",
                    "Mês do registro (1 a 12)",
                    "Região do Brasil",
                    "Unidade federativa",
                    "Cidade",
                    "Latitude da cidade (tabela localidades)",
                    "Longitude da cidade (tabela localidades)",
                    "Temperatura média do mês (°C)",
                    "Temperatura máxima do mês (°C)",
                    "Temperatura mínima do mês (°C)",
                    "Chuva acumulada no mês (mm)",
                    "Umidade relativa do ar (%)",
                    "Velocidade média do vento",
                    "Quantidade de eventos extremos no mês",
                    "Nível de alerta: Baixo, Médio, Alto ou Crítico",
                    "Atributo criado: temperatura máxima menos mínima",
                    "Atributo criado: estação do ano (hemisfério sul)",
                ],
            }
        )
        st.dataframe(dicionario, hide_index=True)

    with st.expander("Consulta SQL utilizada (integração entre tabelas)"):
        st.code(CONSULTA, language="sql")

st.divider()
st.header("Conclusão executiva")

temp_regiao = dff.groupby("regiao")["temperatura_media"].mean().sort_values(ascending=False)
chuva_regiao = dff.groupby("regiao")["chuva_mm"].mean().sort_values(ascending=False)
evento_regiao = dff.groupby("regiao")["eventos_extremos"].mean().sort_values(ascending=False)
serie_geral = dff.groupby("data")["temperatura_media"].mean().sort_index()
coef_geral = tendencia_anual(serie_geral)
if coef_geral is not None:
    texto_tend = (
        f"A temperatura média apresenta tendência de {coef_geral[0] * 12:+.3f} °C por ano "
        f"no período selecionado."
    )
else:
    texto_tend = "Não há meses suficientes para estimar tendência de temperatura."

if len(dff) >= 3:
    corr_final = dff[list(VARIAVEIS) + ["alerta_num"]].corr()
    pares_final = pares_correlacao(corr_final)
    pares_final = pares_final[~pares_final["mecanica"]]
    maior_corr = abs(pares_final.iloc[0]["Correlação"])
    texto_corr = (
        f"Fora das relações entre as próprias temperaturas, a maior correlação absoluta encontrada "
        f"é {fmt(maior_corr, 3)}."
    )
else:
    texto_corr = ""

st.markdown(
    f"""
Considerando os filtros atuais ({fmt(kpis['registros'], 0)} registros):

- A temperatura média é de **{fmt(kpis['temperatura'])} °C**, com a região **{temp_regiao.index[0]}** apresentando a maior média ({fmt(temp_regiao.iloc[0], 2)} °C).
- A chuva média mensal é de **{fmt(kpis['chuva'])} mm**, e a região **{chuva_regiao.index[0]}** é a mais chuvosa ({fmt(chuva_regiao.iloc[0], 1)} mm).
- Foram contabilizados **{fmt(kpis['eventos_total'], 0)} eventos extremos**; a região **{evento_regiao.index[0]}** tem a maior média por cidade/mês ({fmt(evento_regiao.iloc[0], 2)}).
- **{fmt(kpis['pct_alerta'])} %** dos registros estão em nível de alerta Alto ou Crítico.
- {texto_tend} {texto_corr}

**Leitura geral:** na base completa, as diferenças entre regiões, anos e meses são pequenas e as variáveis climáticas
quase não se correlacionam entre si, o que é típico de dados simulados de forma aleatória. O nível de alerta
também não é explicado pelas variáveis climáticas da base. Assim, o projeto cumpre o objetivo de demonstrar o
fluxo completo de análise (tratamento, indicadores, visualizações e dashboard), mas as conclusões não devem ser
usadas como diagnóstico climático real.

**Recomendação:** para uma análise aplicada, substituir a base simulada por dados observados (por exemplo, de
estações meteorológicas) e definir de forma explícita o critério usado para classificar o nível de alerta.
"""
)
