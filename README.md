# BrewInspector — Análise de Dados de Receitas Cervejeiras

Projeto de portfólio que integra coleta e tratamento de dados (ETL), modelagem relacional, análise exploratória e consultas SQL a uma API REST desenvolvida com FastAPI, utilizando dados do catálogo Punk API / DIY Dog.

🔗 **Demo online:** [API no Render (Swagger)](https://etl-e-analise-de-dados-cervejeiros.onrender.com/docs) — no plano gratuito a API "dorme" quando ocioso, então a primeira requisição pode levar cerca de um minuto.


## Fonte dos dados

Os dados vêm do **DIY Dog**, o livro de receitas open-source da cervejaria BrewDog, acessados via um espelho comunitário da Punk API (a API oficial foi descontinuada em 2023). Licença: uso livre para replicar e compartilhar, **não-comercial** — este projeto é de portfólio pessoal, dentro dos termos de uso.

Foram extraídas **415 receitas**, iterando por ID com checkpoint de progresso (retomada segura em caso de interrupção), respeitando um intervalo entre requisições para não sobrecarregar o servidor do espelho.

## Duas versões disponíveis

- **`Postgres_-_ETL_e_Analise_de_Dados_Cervejeiros.ipynb`** (versão atual) — roda em PostgreSQL hospedado gratuitamente no [Neon](https://neon.tech), simulando um ambiente de banco de dados real, com suporte a múltiplos usuários simultâneos.
- **`SQLite_-_ETL_e_Analise_de_Dados_Cervejeiros.ipynb`** (versão anterior, mantida como referência) — versão original em SQLite local, mais simples de rodar sem nenhuma configuração externa.

A lógica analítica e a modelagem de dados são as mesmas nas duas; o que muda é a sintaxe específica de cada banco (ver seção abaixo).

## Arquitetura do banco

Dados normalizados em 4 tabelas relacionadas por chave estrangeira (`cerveja_id`):

| Tabela | Conteúdo |
|---|---|
| `tab_cervejas` | Dados principais: nome, ABV, IBU, temperatura de fermentação, etc. (tabela de dimensão) |
| `tab_maltes` | Maltes usados por receita (um-para-muitos) |
| `tab_lupulos` | Lúpulos usados, com quantidade e estágio de adição (um-para-muitos) |
| `tab_harmonizacao` | Pratos recomendados para cada cerveja (um-para-muitos) |

Decisão de design: normalizar em vez de manter tudo em uma tabela larga, evitando redundância e garantindo uma fonte única de verdade para os dados de cada cerveja (ao custo de exigir `JOIN` nas consultas que cruzam informação).

## Qualidade de dados

Durante a análise, dois tipos de valor atípico foram encontrados e tratados de forma diferente, após investigação:

- **IBU acima de 120 (alguns acima de 1000):** não é erro de importação — é uma característica conhecida da metodologia de cálculo teórico de IBU (fórmulas como Tinseth/Rager), que pode superar o teto de percepção humana (~100-120) em receitas muito carregadas de lúpulo. Em vez de apagar, foi criada uma coluna derivada `ibu_percebido` (limitada a 120), preservando o valor original calculado para não perder informação legítima.
- **Temperatura de fermentação de 99°C (1 registro):** fisicamente impossível — leveduras de cerveja não sobrevivem a essa temperatura. Testada a hipótese de erro de conversão Fahrenheit→Celsius (não se confirmou). Sem explicação sistemática encontrada, o valor foi corrigido para `NULL` (desconhecido), com o registro documentado aqui em vez de inventar um valor plausível.

## Técnicas de SQL demonstradas

- **Modelagem relacional** com chaves estrangeiras e tabelas de dimensão/fato
- **Window functions** (`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`) para ranking de cervejas mais amargas por faixa de temperatura de fermentação
- **Índices e plano de execução**: comparação documentada de varredura completa vs. busca direta via índice, antes e depois de criar índice (`EXPLAIN QUERY PLAN` na versão SQLite; `EXPLAIN ANALYZE`, com tempo real de execução, na versão PostgreSQL)
- **Transações com SAVEPOINT**: inserção em lote com checkpoint intermediário. Se um lote falha (ex: violação de chave primária duplicada), apenas aquele lote é revertido, sem perder lotes anteriores já confirmados; registros perdidos são automaticamente reprocessados individualmente
- **Função customizada reutilizável dentro do SQL**: registrada em Python (`conn.create_function`) na versão SQLite; implementada como função nativa `PL/pgSQL` (`CREATE OR REPLACE FUNCTION`) na versão PostgreSQL
- **Auditoria de sessão**: log automático de todo comando SQL executado, com timestamp, sem necessidade de instrumentar cada célula manualmente — via `sqlite3.trace_callback` na versão SQLite; via uma classe de cursor customizada (`cursor_factory`) na versão PostgreSQL
- **Reconexão resiliente** (versão PostgreSQL): função dedicada para lidar com o encerramento automático de conexões ociosas do plano gratuito do Neon
- **Visualizações exploratórias** com Matplotlib (lúpulos mais usados, IBU médio por faixa de ABV), geradas a partir das próprias queries analíticas. Os gráficos de análise dos dados são gerados nos notebooks Jupyter. A API disponibiliza consultas e resultados em formato de resposta HTTP, mas não possui uma interface própria para exibição de gráficos.

## Como rodar

**Versão SQLite** (mais simples, sem configuração externa):
1. Instale as dependências: `pip install -r requirements.txt`
2. Abra `SQLite_-_ETL_e_Analise_de_Dados_Cervejeiros.ipynb` no Google Colab ou Jupyter local
3. Rode as células em ordem (Kernel → Restart & Run All) — os dados brutos são baixados automaticamente pelo próprio notebook

**Versão PostgreSQL** (requer um banco Neon próprio):
1. Crie um banco gratuito em [neon.tech](https://neon.tech) e copie a connection string
2. Defina a variável de ambiente `DATABASE_URL` com essa string (localmente, num arquivo `.env`; no Colab, como um Secret chamado `DATABASE_URL`)
3. Instale as dependências: `pip install -r requirements.txt`
4. Abra `Postgres_-_ETL_e_Analise_de_Dados_Cervejeiros.ipynb` e rode as células em ordem


## API de consulta (FastAPI)

Disponível online (Render): https://etl-e-analise-de-dados-cervejeiros.onrender.com/docs

O arquivo `main.py` expõe os dados do banco PostgreSQL por uma API REST, com parâmetros de ordenação (menu suspenso), quantidade de resultados e filtros. Endpoints:

- `/cervejas/{id}` — dados de uma cerveja
- `/teor_alcool` — ranking por teor alcoólico
- `/teor_amargor` — ranking por IBU (técnico ou percebido)
- `/lupulos` — lúpulos mais/menos usados
- `/receitas_complexas` — receitas por quantidade de ingredientes
- `/harmonizacoes` — pratos mais/menos recomendados
- `/alcool_por_faixa_temperatura_de_fermentacao` — ranking de ABV por faixa de temperatura

Para rodar localmente (com `DATABASE_URL` configurada no `.env`):

    uvicorn main:app --reload

Depois abra `http://127.0.0.1:8000/docs` para testar os endpoints pela interface interativa.

## Limitações conhecidas
- A API roda no plano gratuito do Render, que "dorme" após um período sem uso; a primeira requisição pode levar cerca de um minuto para responder.
- Os notebooks foram projetados para execução única e sequencial, do início ao fim (Kernel → Restart & Run All). Não são idempotentes: re-executar isoladamente certas células (ex: inserção de dados de teste) pode falhar por depender de estado criado anteriormente na mesma sessão.
- A versão PostgreSQL depende de um banco Neon no plano gratuito, que entra em modo de espera (scale to zero) após período de inatividade — a primeira consulta após um tempo parado pode demorar alguns segundos a mais.
- Camada de visualização/BI mais completa sobre os dados já modelados

## Autor

Denis Willian da Silva — [LinkedIn](https://www.linkedin.com/in/denis-w-silva/) · [GitHub](https://github.com/da-silva-d-w)
