"""
Utilitário temporário: importa o histórico já publicado em dados.js (GitHub
Pages) para o banco SQLite local, reconstruindo o schema completo de
src/storage.py a partir do formato compacto usado pelo painel.

Só insere chaves que ainda não existem localmente (não sobrescreve
classificação mais recente já presente no banco local, ex: PLs dos últimos
dias já classificados nesta sessão). Uso:

    python _importar_dados_publicados.py caminho/para/dados.js
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import storage


def _parse_pl(pl: str, pais: str) -> tuple[str, str, int | None]:
    """'PL 5281/2026' -> ('PL', '5281', 2026). 'HR 123 (119º Congresso)' -> ('HR','123',119)."""
    pl = pl.strip()
    m = re.match(r"^(\S+)\s+(\S+?)(?:/(\d+))?$", pl)
    if not m:
        return pl, "", None
    sigla, numero, ano = m.group(1), m.group(2), m.group(3)
    if ano is None and pais == "US":
        m2 = re.search(r"\((\d+)", pl)
        ano = m2.group(1) if m2 else None
    return sigla, numero, (int(ano) if ano else None)


def importar(caminho_js: str) -> None:
    raw = Path(caminho_js).read_text(encoding="utf-8")
    raw = raw.replace("<\\/", "</")
    m = re.search(r"window\.RADAR_DADOS\s*=\s*(\[.*?\]);", raw, re.S)
    if not m:
        print("não encontrei window.RADAR_DADOS no arquivo")
        return
    dados = json.loads(m.group(1))

    conn = sqlite3.connect(str(storage.DB_PATH))
    existentes = {row[0] for row in conn.execute("SELECT chave FROM proposicoes")}
    conn.close()

    novos = [d for d in dados if d["id"] not in existentes]
    print(f"total no arquivo: {len(dados)} | já existiam localmente: {len(dados) - len(novos)} | novos: {len(novos)}")

    for d in novos:
        id_externo = d["id"].split(":", 2)[2]
        sigla, numero, ano = _parse_pl(d["pl"], d["pais"])
        registro = {
            "pais": d["pais"],
            "casa": d["casa"],
            "id_externo": id_externo,
            "sigla_tipo": sigla,
            "numero": numero,
            "ano": ano,
            "ementa": d.get("ementa"),
            "data_apresentacao": d.get("data"),
            "autores": d.get("autores"),
            "url_origem": d.get("url"),
            "url_inteiro_teor": None,  # não persistido no formato compacto do painel
            "ia_disponivel": 1 if d.get("fonte") == "ia" else 0,
            "fonte_classificacao": d.get("fonte") or "heuristica",
            "relevante": 1,  # dados.js só inclui PLs já filtrados como relevantes
            "justificativa_relevancia": d.get("justificativa"),
            "resumo": d.get("resumo"),
            "areas_impactadas": d.get("areas") or [],
            "tipo_impacto": d.get("tipos") or [],
            "abrangencia": d.get("abrangencia"),
            "nivel_impacto": d.get("nivel"),
            "ultima_tramitacao_data": d.get("tramitacaoData"),
            "ultima_tramitacao_descricao": d.get("tramitacaoDesc"),
            "orgao_atual": d.get("orgao"),
        }
        storage.salvar(registro)

    print(f"importado: {len(novos)} registros")


if __name__ == "__main__":
    importar(sys.argv[1])
