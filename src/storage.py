"""Armazenamento local (SQLite) das proposições coletadas e classificadas."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "radar.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS proposicoes (
    id INTEGER PRIMARY KEY,
    sigla_tipo TEXT,
    numero INTEGER,
    ano INTEGER,
    ementa TEXT,
    data_apresentacao TEXT,
    autores TEXT,
    url_camara TEXT,
    url_inteiro_teor TEXT,
    ia_disponivel INTEGER,
    fonte_classificacao TEXT,
    relevante INTEGER,
    justificativa_relevancia TEXT,
    resumo TEXT,
    areas_impactadas TEXT,
    tipo_impacto TEXT,
    abrangencia TEXT,
    nivel_impacto TEXT,
    processado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# Colunas adicionadas depois da criação inicial da tabela — aplicadas via
# ALTER TABLE em bancos já existentes (CREATE TABLE IF NOT EXISTS não altera
# tabelas que já existem).
_COLUNAS_NOVAS = {
    "ultima_tramitacao_data": "TEXT",
    "ultima_tramitacao_descricao": "TEXT",
    "orgao_atual": "TEXT",
}


def _migrar(conn: sqlite3.Connection) -> None:
    existentes = {row[1] for row in conn.execute("PRAGMA table_info(proposicoes)")}
    for coluna, tipo in _COLUNAS_NOVAS.items():
        if coluna not in existentes:
            conn.execute(f"ALTER TABLE proposicoes ADD COLUMN {coluna} {tipo}")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    _migrar(conn)
    return conn


def ja_processada(id_proposicao: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("SELECT 1 FROM proposicoes WHERE id = ?", (id_proposicao,))
        return cur.fetchone() is not None


def salvar(registro: dict) -> None:
    campos = [
        "id", "sigla_tipo", "numero", "ano", "ementa", "data_apresentacao", "autores",
        "url_camara", "url_inteiro_teor", "ia_disponivel", "fonte_classificacao", "relevante",
        "justificativa_relevancia", "resumo", "areas_impactadas", "tipo_impacto",
        "abrangencia", "nivel_impacto",
        "ultima_tramitacao_data", "ultima_tramitacao_descricao", "orgao_atual",
    ]
    valores = []
    for campo in campos:
        v = registro.get(campo)
        if isinstance(v, (list, dict)):
            v = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, bool):
            v = int(v)
        valores.append(v)

    placeholders = ", ".join("?" for _ in campos)
    colunas = ", ".join(campos)
    with _connect() as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO proposicoes ({colunas}) VALUES ({placeholders})",
            valores,
        )


def atualizar_tramitacao(id_proposicao: int, dados: dict) -> None:
    """Atualiza só os campos de tramitação de uma proposição já salva, sem tocar no resto."""
    campos = ["ultima_tramitacao_data", "ultima_tramitacao_descricao", "orgao_atual"]
    set_clause = ", ".join(f"{c} = ?" for c in campos)
    valores = [dados.get(c) for c in campos] + [id_proposicao]
    with _connect() as conn:
        conn.execute(f"UPDATE proposicoes SET {set_clause} WHERE id = ?", valores)


def listar_recentes(limite: int = 200) -> list[sqlite3.Row]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM proposicoes ORDER BY data_apresentacao DESC LIMIT ?", (limite,)
        )
        return cur.fetchall()
