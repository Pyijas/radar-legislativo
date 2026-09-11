"""
Utilitário temporário: classificação em lote feita diretamente por mim (Claude,
nesta sessão do Claude Code) em vez de chamar a API paga (anthropic/gemini).
Escrevo a saída no mesmo formato que classify.classificar() devolveria — o
resto do pipeline (report.py, painel) não sabe nem precisa saber a
diferença.

Uso:
    python _classificar_com_claude.py contar
    python _classificar_com_claude.py dump N > data/_lote.json
    python _classificar_com_claude.py apply data/_resultado.json

Corrigido em 04/09/2026 pra usar `chave` (pais:casa:id_externo) como
identificador — o schema atual (multi-país) não tem mais uma coluna `id`
numérica única; ver a migração em src/storage.py.
"""
import json
import sqlite3
import sys

DB = "data/radar.db"
MARCA = "ia_claude"  # fonte_classificacao usada pra marcar o que já passou por essa classificação manual


def conectar():
    return sqlite3.connect(DB)


def contar():
    c = conectar()
    total = c.execute("SELECT COUNT(*) FROM proposicoes").fetchone()[0]
    pendentes = c.execute("SELECT COUNT(*) FROM proposicoes WHERE fonte_classificacao != ?", (MARCA,)).fetchone()[0]
    print(f"total={total} pendentes={pendentes}")


def dump(n, arquivo="data/_lote.json", pais=None):
    c = conectar()
    c.row_factory = sqlite3.Row
    # "idioma" não é persistido no schema (só usado em memória durante a coleta,
    # ver main.py) — deriva de `pais` aqui, já que é 1:1 hoje (BR->pt, US->en, CL->es).
    _IDIOMA_POR_PAIS = {"BR": "pt", "US": "en", "CL": "es"}
    # texto_inteiro_teor também não é persistido (só usado em memória durante
    # a coleta) — o lote de classificação trabalha só com a ementa, que é o
    # mesmo texto de entrada mínimo garantido pra qualquer registro.
    sql = ("SELECT chave, pais, casa, sigla_tipo, numero, ano, ementa "
           "FROM proposicoes WHERE fonte_classificacao != ?")
    params = [MARCA]
    if pais:
        sql += " AND pais = ?"
        params.append(pais)
    sql += " ORDER BY pais, casa, data_apresentacao LIMIT ?"
    params.append(n)
    rows = c.execute(sql, params).fetchall()
    saida = [
        {
            "chave": r["chave"],
            "pais": r["pais"],
            "casa": r["casa"],
            "pl": f"{r['sigla_tipo']} {r['numero']}" + (f"/{r['ano']}" if r["pais"] != "CL" else ""),
            "idioma": _IDIOMA_POR_PAIS.get(r["pais"], "pt"),
            "ementa": r["ementa"],
        }
        for r in rows
    ]
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False)
    print(f"dump: {len(saida)} registros -> {arquivo}")


def apply(arquivo):
    with open(arquivo, encoding="utf-8") as f:
        resultados = json.load(f)
    c = conectar()
    n = 0
    for r in resultados:
        cur = c.execute(
            """UPDATE proposicoes SET
                relevante=?, justificativa_relevancia=?, resumo=?, areas_impactadas=?,
                tipo_impacto=?, abrangencia=?, nivel_impacto=?, ia_disponivel=1, fonte_classificacao=?
               WHERE chave=?""",
            (
                int(bool(r["relevante"])),
                r["justificativa_relevancia"],
                r["resumo"],
                json.dumps(r["areas_impactadas"], ensure_ascii=False),
                json.dumps(r["tipo_impacto"], ensure_ascii=False),
                r["abrangencia"],
                r["nivel_impacto"],
                MARCA,
                r["chave"],
            ),
        )
        if cur.rowcount == 0:
            print(f"aviso: chave não encontrada no banco: {r['chave']}")
        n += 1
    c.commit()
    print(f"aplicado: {n} registros")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "contar":
        contar()
    elif cmd == "dump":
        n_arg = int(sys.argv[2])
        arquivo_arg = sys.argv[3] if len(sys.argv) > 3 else "data/_lote.json"
        pais_arg = sys.argv[4] if len(sys.argv) > 4 else None
        dump(n_arg, arquivo_arg, pais_arg)
    elif cmd == "apply":
        apply(sys.argv[2])
    else:
        print("comando desconhecido")
