"""
Publicação automática do relatório no GitHub Pages.

Copia o relatório mais recente (HTML + dados.js) e os arquivos estáticos de
frontend/ (CSS/JS) para docs/ e faz commit + push, se houver um repositório
git configurado com remoto. Falha silenciosamente (só avisa) se não houver
rede, remoto ou repositório — nunca derruba a coleta.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from src.report import _ARQUIVOS_ESTATICOS

_RAIZ = Path(__file__).resolve().parent.parent
_DOCS = _RAIZ / "docs"
_FRONTEND = _RAIZ / "frontend"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_RAIZ), *args],
        capture_output=True, text=True, timeout=30,
    )


def publicar(relatorio_html: Path) -> tuple[bool, str]:
    """Copia o relatório (e os arquivos irmãos dados.js/salvos.html) pra docs/
    e publica via git push.

    Retorna (sucesso, mensagem) — sucesso=False com mensagem explicativa em
    qualquer caso que não impeça o resto do script de rodar normalmente.
    """
    if not (_RAIZ / ".git").is_dir():
        return False, "sem repositório git configurado, pulando publicação"

    try:
        _DOCS.mkdir(parents=True, exist_ok=True)
        origem = Path(relatorio_html)
        pares = [
            (origem, _DOCS / "index.html"),
            (origem.parent / "noticias.html", _DOCS / "noticias.html"),
            (origem.parent / "agenda.html", _DOCS / "agenda.html"),
            (origem.parent / "salvos.html", _DOCS / "salvos.html"),
            (origem.parent / "dados.js", _DOCS / "dados.js"),
        ]
        for src, dst in pares:
            if src.exists():
                shutil.copy(src, dst)

        for nome in _ARQUIVOS_ESTATICOS:
            shutil.copy(_FRONTEND / nome, _DOCS / nome)

        publicados = {dst.name for _, dst in pares} | set(_ARQUIVOS_ESTATICOS)

        # Página/script que saiu da geração (o hub de países e pais.html, por
        # exemplo, quando o painel virou só-Brasil) continuaria servido em
        # docs/ para sempre — o copy acima só acrescenta. Remover o que não é
        # mais gerado evita deixar versão velha no ar.
        obsoletos = []
        for antigo in _DOCS.iterdir():
            if antigo.is_file() and antigo.suffix in {".html", ".js", ".css"} and antigo.name not in publicados:
                antigo.unlink()
                obsoletos.append(f"docs/{antigo.name}")

        arquivos_rel = [f"docs/{nome}" for nome in sorted(publicados)] + obsoletos
        status = _git("status", "--porcelain", "--", *arquivos_rel)
        if not status.stdout.strip():
            return False, "sem mudanças no relatório desde a última publicação"

        _git("add", *arquivos_rel)
        # `commit -- <paths>` em vez de `commit` puro: sem os paths o git leva
        # junto qualquer outra coisa que já estivesse no index, e esta função
        # roda sozinha ao fim de toda coleta — não pode arrastar trabalho em
        # andamento pro commit automático.
        commit = _git(
            "commit", "-m",
            "Atualiza relatório automático\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>",
            "--", *arquivos_rel,
        )
        if commit.returncode != 0:
            return False, f"falha ao commitar: {commit.stderr.strip()[:200]}"

        push = _git("push")
        if push.returncode != 0:
            return False, f"falha ao publicar (push): {push.stderr.strip()[:200]}"

        return True, "publicado no GitHub Pages"
    except Exception as exc:  # nunca derruba a coleta por causa da publicação
        return False, f"erro inesperado ao publicar: {exc}"
