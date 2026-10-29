import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Query 
from dotenv import load_dotenv
 
load_dotenv()  # lê o .env localmente

app = FastAPI(title="BrewInspector", description="API para consulta e análise de dados de receitas cervejeiras do catálogo Punk API / DIY Dog.")

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

@app.get("/cervejas/{cerveja_id}")
def pesquisar_por_ID(cerveja_id: int):
    """Retorna os dados de uma cerveja específica pelo ID"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tab_cervejas WHERE id = %s;", (cerveja_id,))
    resultado = cur.fetchone()
    cur.close()
    conn.close()
    if resultado is None:
        raise HTTPException(status_code=404, detail="Cerveja nao encontrada")
    return resultado

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
    amostras: int = Query(10, ge=1, le=100)
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
    amostras: int = Query(10, ge=1, le=100)
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
    amostras: int = Query(10, ge=1, le=100)
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
    amostras: int = Query(10, ge=1, le=100)
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
    amostras: int = Query(10, ge=1, le=100)
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
    amostras: int = Query(10, ge=1, le=100)
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