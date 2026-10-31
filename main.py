import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Query 
from dotenv import load_dotenv
 
load_dotenv()  # lê o .env localmente

app = FastAPI(title="🍺📋 BrewInspector - API", 
            #   description="API REST para consulta de dados de receitas cervejeiras do catálogo DIY Dog da cervejaria escocesa BrewDog.")
            description=(
                        "API REST para consulta de dados de receitas cervejeiras "
                        "do catálogo DIY Dog da cervejaria escocesa BrewDog.\n\n"
                        "Desenvolvido por Denis W. da Silva.\n"
                        "© 2026 Denis W. da Silva. Todos os direitos reservados."
                        )
            )

def get_conn():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL nao configurada")
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)

# @app.get("/")
# def home():
#     return {"status": "ok", "mensagem": "API de cervejas no ar. Vá para o '/docs' para interagir com a aplicação"}

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@app.get("/status")
def status():
    """Verifica se a API e o banco de dados estão operacionais.
    Usado por sistemas de monitoramento (ex: Render) para checagem automática de disponibilidade."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        conn.close()
        return {"status": "ok", "banco": "conectado"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Banco indisponivel {e}")


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# @app.get("/cervejas/busca")
# def pesquisar_por_nome(
#     nome: str = Query(..., min_length=1, description="Nome ou parte do nome da cerveja"),
#     limite: int = Query(20, ge=1, le=100, description="Quantidade máxima de resultados")
# ):
#     """Pesquisa cervejas pelo nome, aceitando correspondências parciais."""

#     conn = get_conn()
#     cur = conn.cursor()

#     try:
#         cur.execute(
#             """
#             SELECT *
#             FROM tab_cervejas
#             WHERE nome ILIKE %s
#             ORDER BY nome
#             LIMIT %s;
#             """,
#             (f"%{nome}%", limite)
#         )

#         resultados = cur.fetchall()
#         return resultados

#     finally:
#         cur.close()
#         conn.close()

# #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Diferença pra função anterior de busca por nome, que foi substituída:
    # Pesquisa cervejas pelo nome, mostrando também: lúpulos, maltes e harmonizações.
    # As subconsultas permitem recuperar os registros das tabelas auxiliares
    # sem multiplicar as linhas da cerveja principal por causa dos relacionamentos 1:N.
@app.get("/cervejas/nome")
def pesquisar_por_nome(
    nome: str = Query(..., min_length=1, description="Nome ou parte do nome da cerveja"),
    limite: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Pesquisa cervejas pelo nome, aceitando correspondências parciais."""

    nome = nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome da cerveja")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                c.*,

                -- JSON_BUILD_OBJECT organiza os dados de cada ingrediente em um objeto JSON.
                -- JSON_AGG reúne esses objetos em uma lista, permitindo retornar vários registros associados à cerveja.
                -- COALESCE substitui NULL por uma lista vazia ([]) quando não há registros relacionados.
                (
                -- Começa recuperando os lúpulos e suas respectivas quantidades em uma lista JSON.
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'nome_lupulo', l.nome_lupulo,
                                'quantidade_g', l.quantidade_g,
                                'estagio_adicao', l.estagio_adicao,
                                'atributo', l.atributo
                            )
                            ORDER BY l.id
                        ),
                        '[]'::json
                    )
                    FROM tab_lupulos l
                    WHERE l.cerveja_id = c.id
                ) AS lupulos,

                -- Recupera os maltes e suas respectivas quantidades em uma lista JSON.
                (
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'nome_malte', m.nome_malte,
                                'quantidade_kg', m.quantidade_kg
                            )
                            ORDER BY m.id
                        ),
                        '[]'::json
                    )
                    FROM tab_maltes m
                    WHERE m.cerveja_id = c.id
                ) AS maltes,

                -- Recupera os pratos associados à cerveja para consulta de harmonizações.
                (
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'prato', h.prato
                            )
                            ORDER BY h.id
                        ),
                        '[]'::json
                    )
                    FROM tab_harmonizacao h
                    WHERE h.cerveja_id = c.id
                ) AS harmonizacoes

            FROM tab_cervejas c
            WHERE c.nome ILIKE %s
            ORDER BY c.nome
            LIMIT %s;
            """,
            (f"%{nome}%", limite)
        )

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# @app.get("/cerveja_id/{cerveja_id}")
# def pesquisar_por_ID(cerveja_id: int):
#     """Retorna os dados de uma cerveja específica pelo ID"""
#     conn = get_conn()
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM tab_cervejas WHERE id = %s;", (cerveja_id,))
#     resultado = cur.fetchone()
#     cur.close()
#     conn.close()
#     if resultado is None:
#         raise HTTPException(status_code=404, detail="Cerveja nao encontrada")
#     return resultado

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Diferença pra função anterior de busca por nome, que foi substituída:
    # Retorna os dados completos de uma cerveja específica pelo ID,
    # mostrando também: lúpulos, maltes e harmonizações.
@app.get("/cerveja_id/{cerveja_id}")
def pesquisar_por_ID(cerveja_id: int):
    """Retorna os dados de uma cerveja específica pelo ID"""

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                c.*,

                -- Assim como na função anterior, usaremos COALESCE, JSON_AGG e JSON_BUILD_OBJECT para os mesmos fins

                (
                -- Começa agrupando os registros de lúpulos associados à cerveja em uma lista JSON.
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'nome_lupulo', l.nome_lupulo,
                                'quantidade_g', l.quantidade_g,
                                'estagio_adicao', l.estagio_adicao,
                                'atributo', l.atributo
                            )
                            ORDER BY l.id
                        ),
                        '[]'::json
                    )
                    FROM tab_lupulos l
                    WHERE l.cerveja_id = c.id
                ) AS lupulos,

                -- Agrupa os registros de maltes e suas quantidades em uma lista JSON.
                (
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'nome_malte', m.nome_malte,
                                'quantidade_kg', m.quantidade_kg
                            )
                            ORDER BY m.id
                        ),
                        '[]'::json
                    )
                    FROM tab_maltes m
                    WHERE m.cerveja_id = c.id
                ) AS maltes,

                -- Agrupa os pratos associados à cerveja em uma lista JSON.
                (
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'prato', h.prato
                            )
                            ORDER BY h.id
                        ),
                        '[]'::json
                    )
                    FROM tab_harmonizacao h
                    WHERE h.cerveja_id = c.id
                ) AS harmonizacoes

            FROM tab_cervejas c
            WHERE c.id = %s;
            """,
            (cerveja_id,)
        )

        resultado = cur.fetchone()

        if resultado is None:
            raise HTTPException(status_code=404, detail="Cerveja não encontrada")

        return resultado

    finally:
        cur.close()
        conn.close()


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@app.get("/cervejas/descricao")
def pesquisar_por_descricao(
    termo: str = Query(..., min_length=1, description="Palavra ou trecho da descrição da cerveja"),
    limite: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Pesquisa cervejas por palavras ou trechos presentes na descrição."""

    termo = termo.strip()
    if not termo:
        raise HTTPException(status_code=400, detail="Informe um termo para pesquisar na descrição")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                c.*,
                -- Assim como nas funções anteriores, usaremos COALESCE, JSON_AGG e JSON_BUILD_OBJECT para os mesmos fins
                
                (
                -- Começa agrupando os registros de lúpulos associados à cerveja em uma lista JSON.
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'nome_lupulo', l.nome_lupulo,
                                'quantidade_g', l.quantidade_g,
                                'estagio_adicao', l.estagio_adicao,
                                'atributo', l.atributo
                            )
                            ORDER BY l.id
                        ),
                        '[]'::json
                    )
                    FROM tab_lupulos l
                    WHERE l.cerveja_id = c.id
                ) AS lupulos,

                -- Agrupa os registros de maltes e suas quantidades em uma lista JSON.
                (
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'nome_malte', m.nome_malte,
                                'quantidade_kg', m.quantidade_kg
                            )
                            ORDER BY m.id
                        ),
                        '[]'::json
                    )
                    FROM tab_maltes m
                    WHERE m.cerveja_id = c.id
                ) AS maltes,

                -- Agrupa os pratos associados à cerveja em uma lista JSON.
                (
                    SELECT COALESCE(
                        JSON_AGG(
                            JSON_BUILD_OBJECT(
                                'prato', h.prato
                            )
                            ORDER BY h.id
                        ),
                        '[]'::json
                    )
                    FROM tab_harmonizacao h
                    WHERE h.cerveja_id = c.id
                ) AS harmonizacoes

            FROM tab_cervejas c
            WHERE c.descricao ILIKE %s
            ORDER BY c.nome
            LIMIT %s;
            """,
            (f"%{termo}%", limite)
        )

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@app.get("/cervejas/lupulo")
def pesquisar_por_lupulo(
    nome: str = Query(..., min_length=1, description="Nome ou parte do nome do lúpulo"),
    limite: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Pesquisa cervejas que utilizam determinado lúpulo."""

    nome = nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome do lúpulo")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                c.id,
                c.nome,
                c.tagline,
                c.abv,
                c.ibu,
                STRING_AGG(DISTINCT l.nome_lupulo, ', ') AS lupulos_encontrados
            FROM tab_cervejas c
            INNER JOIN tab_lupulos l ON c.id = l.cerveja_id
            WHERE l.nome_lupulo ILIKE %s
            GROUP BY c.id, c.nome, c.tagline, c.abv, c.ibu
            ORDER BY RANDOM()
            LIMIT %s;
            """,
            (f"%{nome}%", limite)
        )

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@app.get("/cervejas/malte")
def pesquisar_por_malte(
    nome: str = Query(..., min_length=1, description="Nome ou parte do nome do malte"),
    limite: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Pesquisa cervejas que utilizam determinado malte."""

    nome = nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome do malte")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                c.id,
                c.nome,
                c.tagline,
                c.abv,
                c.ibu,
                STRING_AGG(DISTINCT m.nome_malte, ', ') AS maltes_encontrados
            FROM tab_cervejas c
            INNER JOIN tab_maltes m ON c.id = m.cerveja_id
            WHERE m.nome_malte ILIKE %s
            GROUP BY c.id, c.nome, c.tagline, c.abv, c.ibu
            ORDER BY RANDOM()
            LIMIT %s;
            """,
            (f"%{nome}%", limite)
        )

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@app.get("/cervejas/harmonizacao")
def pesquisar_por_harmonizacao(
    prato: str = Query(..., min_length=1, description="Nome ou parte do nome do prato"),
    limite: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Pesquisa cervejas recomendadas para harmonizar com determinado prato."""

    prato = prato.strip()
    if not prato:
        raise HTTPException(status_code=400, detail="Informe o nome do prato")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                c.id,
                c.nome,
                c.tagline,
                c.abv,
                c.ibu,
                STRING_AGG(DISTINCT h.prato, ', ') AS harmonizacoes_encontradas
            FROM tab_cervejas c
            INNER JOIN tab_harmonizacao h ON c.id = h.cerveja_id
            WHERE h.prato ILIKE %s
            GROUP BY c.id, c.nome, c.tagline, c.abv, c.ibu
            ORDER BY RANDOM()
            LIMIT %s;
            """,
            (f"%{prato}%", limite)
        )

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from enum import Enum
class Ordem(str, Enum):
    desc = "Decrescente (Mostrar mais utilizados)"
    asc = "Crescente (Mostrar menos utilizados)"

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from enum import Enum
class OrdemAlcoolica(str, Enum):
    desc = "Decrescente (Mostrar mais alcoólicas)"
    asc = "Crescente (Mostrar menos alcoólicas)"

@app.get("/teor_alcool")
# def teor_de_alcool(ordem_da_amostragem: OrdemAlcoolica = OrdemAlcoolica.desc, amostras: int = 10): # com campos opcionais
def teor_de_alcool( # colocando todas os campos como obrigatórios
    ordem_da_amostragem: OrdemAlcoolica = Query(..., json_schema_extra={"default": OrdemAlcoolica.desc}, description="Ordem do ranking alcoólico"), 
    amostras: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Top cervejas com mais/menos álcool no catálogo"""
    direcao_sql = "ASC" if ordem_da_amostragem == OrdemAlcoolica.asc else "DESC"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
                    SELECT id, nome, abv
                    FROM tab_cervejas
                    WHERE abv IS NOT NULL
                    ORDER BY abv {direcao_sql}
                    LIMIT %s;
                """, (amostras,))
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return resultado

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from enum import Enum
class OrdemIBU(str, Enum):
    desc = "Decrescente (Mostrar maiores IBUs)"
    asc = "Crescente (Mostrar menores IBUs)"

class TipoIBU(str, Enum):
    normal = "IBU Técnico (Valor teórico calculado em laboratório)"
    percebido = "IBU Percebido (Limite máximo prático de 120 para o paladar humano)"


@app.get("/teor_amargor")
# def teor_de_alcool(ordem_da_amostragem: OrdemIBU = OrdemIBU.desc, amostras: int = 10): # com campos opcionais
def teor_de_amargor( # colocando todas os campos como obrigatórios
    ordem_da_amostragem: OrdemIBU = Query(..., json_schema_extra={"default": OrdemIBU.desc}, description="Ordem do ranking de amargor"),
    metrica_de_amargor: TipoIBU = Query(..., json_schema_extra={"default": TipoIBU.percebido}, description="Escolha a métrica de amargor"),
    amostras: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Top cervejas com maiores/menores IBUs no catálogo"""
    direcao_sql = "ASC" if ordem_da_amostragem == OrdemIBU.asc else "DESC"
    coluna_ibu = "ibu" if metrica_de_amargor == TipoIBU.normal else "ibu_percebido" # coluna selecionada pelo usuário
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
                    SELECT id, nome, {coluna_ibu}
                    FROM tab_cervejas
                    WHERE {coluna_ibu} IS NOT NULL
                    ORDER BY {coluna_ibu} {direcao_sql}
                    LIMIT %s;
                """, (amostras,))
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return resultado

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@app.get("/lupulos")
# def lupulos(ordem_da_amostragem: Ordem = Ordem.desc, amostras: int = 10): # com campos opcionais
def lupulos( # colocando todas os campos como obrigatórios
    ordem_da_amostragem: Ordem = Query(..., json_schema_extra={"default": Ordem.desc}, description="Ordem da amostragem"), 
    amostras: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Top lúpulos mais/menos frequentes no catálogo"""
    direcao_sql = "ASC" if ordem_da_amostragem == Ordem.asc else "DESC"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
                    SELECT nome_lupulo, COUNT(*) as vezes_usado
                    FROM tab_lupulos
                    GROUP BY nome_lupulo
                    ORDER BY vezes_usado {direcao_sql}
                    LIMIT %s;
                """, (amostras,))
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return resultado

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from enum import Enum
class OrdemReceitas(str, Enum):
    desc = "Decrescente (Mostrar mais complexas)"
    asc = "Crescente (Mostrar menos complexas)"


@app.get("/receitas_complexas")
# def receitas_complexas(ordem_da_amostragem: OrdemReceitas = OrdemReceitas.desc, amostras: int = 10): # com campos opcionais
def complexidade_das_receitas( # colocando todas os campos como obrigatórios
    ordem_da_amostragem: OrdemReceitas = Query(..., json_schema_extra={"default": OrdemReceitas.desc}, description="Ordem da amostragem"), 
    amostras: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Top cervejas mais/menos ingredientes no catálogo"""
    direcao_sql = "ASC" if ordem_da_amostragem == OrdemReceitas.asc else "DESC"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
                    SELECT
                        c.nome,
                        tagline,
                        COALESCE(sub_tab_lupulo.qtd_lupulo, 0) AS qtd_lupulo,
                                                                        -- A função COALESCE serve para garantir que,
                                                                        -- se uma cerveja não tiver nenhum malte ou lúpulo cadastrado
                                                                        -- (retornando NULL), o SQL transforme esse NULL em 0
                        COALESCE(sub_tab_malte.qtd_malte, 0) AS qtd_malte,
                        (COALESCE(sub_tab_lupulo.qtd_lupulo, 0) + COALESCE(sub_tab_malte.qtd_malte, 0)) AS qtd_ingredientes
                    FROM tab_cervejas c

                    -- Subquery para contar lúpulos de forma isolada
                    LEFT JOIN (
                        SELECT cerveja_id, COUNT(*) AS qtd_lupulo
                        FROM tab_lupulos
                        GROUP BY cerveja_id
                    ) AS sub_tab_lupulo ON c.id = sub_tab_lupulo.cerveja_id

                    -- Subquery para contar maltes de forma isolada
                    LEFT JOIN (
                        SELECT cerveja_id, COUNT(*) AS qtd_malte
                        FROM tab_maltes
                        GROUP BY cerveja_id
                    ) AS sub_tab_malte ON c.id = sub_tab_malte.cerveja_id

                    ORDER BY qtd_ingredientes {direcao_sql}
                    LIMIT %s;
                """, (amostras,))
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return resultado

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@app.get("/harmonizacoes")
# def harmonizacoes(ordem_da_amostragem: Ordem = Ordem.desc, amostras: int = 10): # com campos opcionais
def harmonizacoes( # colocando todas os campos como obrigatórios
    ordem_da_amostragem: Ordem = Query(..., json_schema_extra={"default": Ordem.desc}, description="Ordem da amostragem"), 
    amostras: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Top pratos que aparecem mais/menos frequentemente como sugestões de harmonização"""
    direcao_sql = "ASC" if ordem_da_amostragem == Ordem.asc else "DESC"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
                    SELECT prato, COUNT(*) as vezes_recomendado
                    FROM tab_harmonizacao
                    GROUP BY prato
                    ORDER BY vezes_recomendado {direcao_sql}
                    LIMIT %s;
                """, (amostras,))
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return resultado


class FaixaTemperatura(str, Enum):
    baixa = "Baixa (<15°C)"
    media = "Média (15°C a 22°C)"
    alta = "Alta (>=22°C)"

class OrdemAlcool(str, Enum):
    desc = "Decrescente (Primeiros têm mais álcool)"
    asc = "Crescente (Primeiros têm menos alcool)"

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@app.get("/alcool_por_faixa_temperatura_de_fermentacao")
# def alcool_temp(faixa_de_temperatura_de_fermentacao: FaixaTemperatura = FaixaTemperatura.media , ordem_da_amostragem: OrdemAlcool = OrdemAlcool.desc, amostras: int = 10): # com campos opcionais
def teor_alcoolico_por_faixa_de_temperatura_de_fermentacao( # colocando todas os campos como obrigatórios
    faixa_de_temperatura_de_fermentacao: FaixaTemperatura = Query(..., json_schema_extra={"default": FaixaTemperatura.media}, description="Faixa de temperatura de fermentação"), 
    ordem_da_amostragem: OrdemAlcool = Query(..., json_schema_extra={"default": OrdemAlcool.desc}, description="Ordem da amostragem"), 
    amostras: int = Query(10, ge=1, le=100, description="Quantidade máxima de resultados")
):
    """Top cervejas que têm mais/menos álcool por faixa de temperatura de fermentação"""
    
    # Mapear a opção escolhida pelo usuário para o filtro SQL
    if faixa_de_temperatura_de_fermentacao == FaixaTemperatura.baixa:
        filtro_temp_sql = "fermentation_temp_celsius < 15"
    elif faixa_de_temperatura_de_fermentacao == FaixaTemperatura.media:
        filtro_temp_sql = "fermentation_temp_celsius >= 15 AND fermentation_temp_celsius < 22"
    else:
        filtro_temp_sql = "fermentation_temp_celsius >= 22"

    direcao_sql = "ASC" if ordem_da_amostragem == OrdemAlcool.asc else "DESC"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
                    WITH cervejas_classificadas AS (
                        SELECT
                            nome,
                            abv,
                            ibu_percebido,
                            fermentation_temp_celsius,
                            tagline,
                            
                            ROW_NUMBER() OVER (
                                ORDER BY abv {direcao_sql}
                            ) as ranking

                        FROM tab_cervejas
                        WHERE 
                            {filtro_temp_sql} -- filtrar pra faixa selecionada pelo usuário
                            AND abv IS NOT NULL 
                            AND ibu_percebido IS NOT NULL 
                            AND fermentation_temp_celsius IS NOT NULL
                    )
                    SELECT
                        ranking,
                        nome,
                        abv,
                        ibu_percebido,
                        fermentation_temp_celsius,
                        tagline
                    FROM cervejas_classificadas
                    WHERE ranking <= %s -- Quantas cervejas por faixa
                    ORDER BY abv {direcao_sql};
                    """, (amostras,))
    resultado = cur.fetchall()
    cur.close()
    conn.close()
    return resultado