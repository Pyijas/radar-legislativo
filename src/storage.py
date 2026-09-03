"""Armazenamento local (SQLite) das proposições coletadas e classificadas.

Cobre múltiplos países/casas legislativas (ver src/paises.py) na mesma
tabela. Cada proposição é identificada de forma única por (pais, casa,
id_externo) — não só por um id numérico — porque o id de origem não é
globalmente único (a Câmara e o Senado, por exemplo, têm suas próprias
sequências, e o Congress.gov dos EUA usa identificadores como "hr1234",
não numéricos).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "radar.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS proposicoes (
    chave TEXT PRIMARY KEY,
    pais TEXT NOT NULL,
    casa TEXT NOT NULL,
    id_externo TEXT NOT NULL,
    sigla_tipo TEXT,
    numero TEXT,
    ano INTEGER,
    ementa TEXT,
    data_apresentacao TEXT,
    autores TEXT,
    url_origem TEXT,
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
    ultima_tramitacao_data TEXT,
    ultima_tramitacao_descricao TEXT,
    orgao_atual TEXT,
    processado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# Colunas adicionadas depois da criação do schema atual — aplicadas via ALTER
# TABLE em bancos já existentes (CREATE TABLE IF NOT EXISTS não altera
# tabelas que já existem). Fica vazio por enquanto; é o padrão pra próximas
# adições incrementais de coluna, sem precisar reconstruir a tabela de novo.
_COLUNAS_NOVAS: dict[str, str] = {}


def _migrar(conn: sqlite3.Connection) -> None:
    colunas = {row[1] for row in conn.execute("PRAGMA table_info(proposicoes)")}

    if colunas and "chave" not in colunas:
        # Schema antigo (só Câmara/Brasil, PK = id numérico da Câmara).
        # Reconstrói a tabela no formato novo, preservando todos os dados.
        tabela_nova = _SCHEMA.replace("proposicoes (", "proposicoes_nova (", 1)
        conn.executescript(tabela_nova)
        conn.execute(
            """
            INSERT INTO proposicoes_nova (
                chave, pais, casa, id_externo, sigla_tipo, numero, ano, ementa,
                data_apresentacao, autores, url_origem, url_inteiro_teor,
                ia_disponivel, fonte_classificacao, relevante,
                justificativa_relevancia, resumo, areas_impactadas,
                tipo_impacto, abrangencia, nivel_impacto,
                ultima_tramitacao_data, ultima_tramitacao_descricao,
                orgao_atual, processado_em
            )
            SELECT
                'BR:camara:' || id, 'BR', 'camara', CAST(id AS TEXT), sigla_tipo,
                CAST(numero AS TEXT), ano, ementa, data_apresentacao, autores,
                url_camara, url_inteiro_teor, ia_disponivel, fonte_classificacao,
                relevante, justificativa_relevancia, resumo, areas_impactadas,
                tipo_impacto, abrangencia, nivel_impacto, ultima_tramitacao_data,
                ultima_tramitacao_descricao, orgao_atual, processado_em
            FROM proposicoes
            """
        )
        conn.execute("DROP TABLE proposicoes")
        conn.execute("ALTER TABLE proposicoes_nova RENAME TO proposicoes")
        colunas = {row[1] for row in conn.execute("PRAGMA table_info(proposicoes)")}

    for coluna, tipo in _COLUNAS_NOVAS.items():
        if coluna not in colunas:
            conn.execute(f"ALTER TABLE proposicoes ADD COLUMN {coluna} {tipo}")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    _migrar(conn)
    return conn


def _chave(pais: str, casa: str, id_externo) -> str:
    return f"{pais}:{casa}:{id_externo}"


def ja_processada(pais: str, casa: str, id_externo) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT 1 FROM proposicoes WHERE chave = ?", (_chave(pais, casa, id_externo),)
        )
        return cur.fetchone() is not None


def salvar(registro: dict) -> None:
    registro = dict(registro)
    registro["chave"] = _chave(registro["pais"], registro["casa"], registro["id_externo"])

    campos = [
        "chave", "pais", "casa", "id_externo", "sigla_tipo", "numero", "ano", "ementa",
        "data_apresentacao", "autores", "url_origem", "url_inteiro_teor", "ia_disponivel",
        "fonte_classificacao", "relevante", "justificativa_relevancia", "resumo",
        "areas_impactadas", "tipo_impacto", "abrangencia", "nivel_impacto",
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


def atualizar_tramitacao(pais: str, casa: str, id_externo, dados: dict) -> None:
    """Atualiza só os campos de tramitação de uma proposição já salva, sem tocar no resto."""
    campos = ["ultima_tramitacao_data", "ultima_tramitacao_descricao", "orgao_atual"]
    set_clause = ", ".join(f"{c} = ?" for c in campos)
    valores = [dados.get(c) for c in campos] + [_chave(pais, casa, id_externo)]
    with _connect() as conn:
        conn.execute(f"UPDATE proposicoes SET {set_clause} WHERE chave = ?", valores)


def listar_recentes(limite: int = 5000) -> list[sqlite3.Row]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM proposicoes ORDER BY data_apresentacao DESC LIMIT ?", (limite,)
        )
        return cur.fetchall()
