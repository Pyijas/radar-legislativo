"""
Utilitário temporário: classificação em lote feita diretamente por mim (Claude,
nesta sessão do Claude Code) em vez de chamar a API paga. Uso:

    python _classificar_com_claude.py contar
    python _classificar_com_claude.py dump N > data/_lote.json
    python _classificar_com_claude.py apply data/_resultado.json
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


def dump(n, arquivo="data/_lote.json"):
    c = conectar()
    c.row_factory = sqlite3.Row
    rows = c.execute(
        "SELECT id, sigla_tipo, numero, ano, ementa FROM proposicoes "
        "WHERE fonte_classificacao != ? ORDER BY id LIMIT ?", (MARCA, n)
    ).fetchall()
    saida = [{"id": r["id"], "pl": f"{r['sigla_tipo']} {r['numero']}/{r['ano']}", "ementa": r["ementa"]} for r in rows]
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False)
    print(f"dump: {len(saida)} registros -> {arquivo}")


def apply(arquivo):
    with open(arquivo, encoding="utf-8") as f:
        resultados = json.load(f)
    c = conectar()
    n = 0
    for r in resultados:
        c.execute(
            """UPDATE proposicoes SET
                relevante=?, justificativa_relevancia=?, resumo=?, areas_impactadas=?,
                tipo_impacto=?, abrangencia=?, nivel_impacto=?, ia_disponivel=1, fonte_classificacao=?
               WHERE id=?""",
            (
                int(bool(r["relevante"])),
                r["justificativa_relevancia"],
                r["resumo"],
                json.dumps(r["areas_impactadas"], ensure_ascii=False),
                json.dumps(r["tipo_impacto"], ensure_ascii=False),
                r["abrangencia"],
                r["nivel_impacto"],
                MARCA,
                r["id"],
            ),
        )
        n += 1
    c.commit()
    print(f"aplicado: {n} registros")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "contar":
        contar()
    elif cmd == "dump":
        dump(int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "data/_lote.json")
    elif cmd == "apply":
        apply(sys.argv[2])
    else:
        print("comando desconhecido")
