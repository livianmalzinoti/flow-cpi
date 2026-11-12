#!/usr/bin/env python3
"""Empacota um projeto de iFlow em .zip para upload no Integration Suite.

Uso:
    python3 package_iflow.py <pasta-do-projeto> [--out /caminho/Nome.zip] [--skip-validate]

Roda validate_iflow.py antes (falha se houver erros). O zip não tem pasta raiz: .project,
META-INF/ e src/ ficam na raiz do arquivo, como o Integration Suite espera.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_iflow import validate  # noqa: E402

EXCLUDE_DIRS = {".git", "__pycache__", ".idea", ".vscode", "node_modules"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "README.md"}


def collect(project: Path) -> list[Path]:
    """Coleta só artefatos do iFlow (evita rglob na raiz inteira — lento com AV no Windows)."""
    files: list[Path] = []
    roots = [
        project / ".project",
        project / "metainfo.prop",
        project / "META-INF",
        project / "src" / "main" / "resources",
    ]
    seen: set[Path] = set()
    for root in roots:
        paths = [root] if root.is_file() else (root.rglob("*") if root.is_dir() else [])
        for path in paths:
            if not path.is_file():
                continue
            rel = path.relative_to(project)
            if rel in seen:
                continue
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            if rel.name in EXCLUDE_FILES or rel.suffix == ".zip":
                continue
            seen.add(rel)
            files.append(rel)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", help="pasta do projeto do iFlow")
    parser.add_argument("--out", help="caminho do .zip (padrão: <pasta-pai>/<NomeDoProjeto>.zip)")
    parser.add_argument("--skip-validate", action="store_true", help="não roda a validação (não recomendado)")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"ERRO: pasta não encontrada: {project}", file=sys.stderr)
        return 2

    if not args.skip_validate:
        rep = validate(project)
        for w in rep.warnings:
            print(f"AVISO: {w}")
        for e in rep.errors:
            print(f"ERRO:  {e}")
        if rep.errors:
            print(f"\n{len(rep.errors)} erro(s). Corrija antes de empacotar.")
            return 1

    out = Path(args.out).expanduser().resolve() if args.out else project.parent / f"{project.name}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    files = collect(project)
    # MANIFEST primeiro, como ferramentas de jar fazem
    files.sort(key=lambda p: (p.as_posix() != "META-INF/MANIFEST.MF", p.as_posix()))
    # ZIP_STORED: pacote pequeno; deflate custa CPU e dispara mais I/O do antivírus
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in files:
            zf.write(project / rel, rel.as_posix())

    print(f"\nZip gerado: {out}")
    print(f"{len(files)} arquivo(s):")
    for rel in files:
        print(f"  {rel.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
