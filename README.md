# Análise Climática do Brasil (2015–2024)

**Aluno(a):** Miguel Garcia Lopes do Amaral
**Disciplina:** Linguagem de Programação  
**Turma:** Quinta/noite
**Professor: Alexandre Neves Louzada

## Links do projeto

| Item | Link |
|---|---|
| Repositório GitHub | https://github.com/Mi-gue-l/Projeto-de-An-lise-e-Visualiza-o-de-Dados-com-Python |
| Página do projeto (GitHub Pages) | https://mi-gue-l.github.io/Projeto-de-An-lise-e-Visualiza-o-de-Dados-com-Python/ |
| Dashboard (Streamlit Community Cloud) | https://projeto-de-an-lise-e-visualiza-o-de-dados-com-python-5cjbd7z2n.streamlit.app/ |

## Descrição

Projeto de análise e visualização de dados sobre o clima brasileiro. A base é **simulada** e contém 4.440 registros mensais de 37 cidades (20 UFs), de janeiro de 2015 a dezembro de 2024, com temperatura, chuva, umidade, vento, eventos extremos e nível de alerta.

O projeto cobre: tratamento e preparação da base, engenharia de atributos, análise exploratória, KPIs, visualizações, dashboard interativo e publicação online.

> Os dados são simulados. Os resultados demonstram o método de análise e não representam o clima real do Brasil.

## Tecnologias

Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Streamlit, SQLAlchemy, SQLite, GitHub e GitHub Pages.

## Funcionalidades

**Intermediárias**
- Filtros múltiplos no Streamlit (região, UF, cidade, período e nível de alerta)
- KPIs dinâmicos, com comparação com a base completa
- Gráficos interativos (Plotly)
- Análise temporal
- Integração entre tabelas (JOIN entre `registros_clima` e `localidades`)
- Dashboard organizado em seções (abas)
- Visualizações comparativas
- Análises geográficas

**Avançadas**
- Persistência em banco (SQLAlchemy + SQLite)
- Modelagem relacional (SQLAlchemy, com chave estrangeira entre as tabelas)
- Mapas interativos (Plotly)
- Séries temporais avançadas (média móvel de 12 meses e tendência linear com NumPy)
- Correlação estatística (Pearson e Spearman)
- Integração de múltiplas fontes (CSV + banco de dados)

## Estrutura do projeto

```
projeto-clima-brasil/
  ├── app.py
  ├── requirements.txt
  ├── README.md
  ├── index.html
  ├── dados/
  │     ├── simulacao_clima_brasil.csv
  │     └── localidades.csv
  ├── database/
  │     └── clima.db
  ├── notebooks/
  │     └── analise_clima_brasil.ipynb
  └── imagens/
```

## Banco de dados

O arquivo `database/clima.db` contém duas tabelas relacionadas:

- `localidades` (id, cidade, uf, regiao, latitude, longitude)
- `registros_clima` (id, localidade_id, data, ano, mes, temperatura_media, temperatura_maxima, temperatura_minima, chuva_mm, umidade, velocidade_vento, eventos_extremos, nivel_alerta)

Se o arquivo não existir, o `app.py` cria o banco automaticamente a partir dos arquivos da pasta `dados/`.

## Principais resultados

- Temperatura média de 24,99 °C e chuva média mensal de 105,9 mm
- 8.918 eventos extremos (média de 2,01 por cidade/mês)
- 48,7 % dos registros em alerta Alto ou Crítico
- Tendência de temperatura de +0,023 °C por ano
- Correlação forte apenas entre as temperaturas; demais variáveis com correlação desprezível
- O nível de alerta não é explicado pelas variáveis climáticas da base
