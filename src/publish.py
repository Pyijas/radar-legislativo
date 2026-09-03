"""
Publicação automática do relatório no GitHub Pages.

Copia o relatório mais recente para docs/index.html e faz commit + push, se
houver um repositório git configurado com remoto. Falha silenciosamente (só
avisa) se não houver rede, remoto ou repositório — nunca derruba a coleta.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
_DOCS_INDEX = _RAIZ / "docs" / "index.html"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_RAIZ), *args],
        capture_output=True, text=True, timeout=30,
    )


def publicar(relatorio_html: Path) -> tuple[bool, str]:
    """Copia o relatório pra docs/index.html e publica via git push.

    Retorna (sucesso, mensagem) — sucesso=False com mensagem explicativa em
    qualquer caso que não impeça o resto do script de rodar normalmente.
    """
    if not (_RAIZ / ".git").is_dir():
        return False, "sem repositório git configurado, pulando publicação"

    try:
        _DOCS_INDEX.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(relatorio_html, _DOCS_INDEX)

        status = _git("status", "--porcelain", "--", "docs/index.html")
        if not status.stdout.strip():
            return False, "sem mudanças no relatório desde a última publicação"

        _git("add", "docs/index.html")
        commit = _git(
            "commit", "-m",
            "Atualiza relatório automático\n\nCo-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>",
        )
        if commit.returncode != 0:
            return False, f"falha ao commitar: {commit.stderr.strip()[:200]}"

        push = _git("push")
        if push.returncode != 0:
            return False, f"falha ao publicar (push): {push.stderr.strip()[:200]}"

        return True, "publicado no GitHub Pages"
    except Exception as exc:  # nunca derruba a coleta por causa da publicação
        return False, f"erro inesperado ao publicar: {exc}"
