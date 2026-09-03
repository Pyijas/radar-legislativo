"""
Metadados dos países/casas legislativas cobertos pelo Radar — fonte única de
verdade usada tanto pela coleta (main.py, pra rotular pais/casa/casaLabel em
cada registro) quanto pelo relatório (report.py, pra montar a página inicial
com bandeiras e os filtros de casa dentro de cada país).

Adicionar um país novo aqui NÃO ativa a coleta sozinho — precisa também de um
cliente (ex: src/congress_client.py) e de estar listado em main.py. Um país
sem cliente ainda pode aparecer no hub como "em breve" via EM_BREVE abaixo.
"""
from __future__ import annotations

PAISES = {
    "BR": {
        "nome": "Brasil",
        "bandeira": "🇧🇷",
        "casas": {
            "camara": "Câmara dos Deputados",
            "senado": "Senado Federal",
        },
    },
    "US": {
        "nome": "Estados Unidos",
        "bandeira": "🇺🇸",
        "casas": {
            "house": "House of Representatives",
            "senate": "Senate",
        },
    },
}

# Países pesquisados (ver EXPANSAO-INTERNACIONAL.md) mas ainda sem cliente de
# coleta implementado — aparecem no hub como cards desabilitados "em breve",
# pra deixar visível o roteiro sem prometer dado que ainda não existe.
EM_BREVE = [
    {"nome": "Chile", "bandeira": "🇨🇱"},
    {"nome": "Argentina", "bandeira": "🇦🇷"},
    {"nome": "Colômbia", "bandeira": "🇨🇴"},
    {"nome": "Guatemala", "bandeira": "🇬🇹"},
]
