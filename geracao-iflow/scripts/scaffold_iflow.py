#!/usr/bin/env python3
"""Cria a estrutura base de um projeto de iFlow a partir de templates/.

Uso:
    python3 scaffold_iflow.py --id IF_Pedido_Criar --name "IF Pedido Criar" \
        --out /caminho/destino [--description "..."] [--with-query-script]

Gera <out>/<id>/ com .project, metainfo.prop, META-INF/MANIFEST.MF, parameters.prop/.propdef
e a pasta scenarioflows/integrationflow/ (o .iflw é escrito pelo agente em seguida).
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
IFLW_DIR = Path("src/main/resources/scenarioflows/integrationflow")
QUERY_SCRIPT = Path("src/main/resources/script/ReadQueryParams.groovy")


def valid_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", value):
        raise argparse.ArgumentTypeError(
            "id deve começar com letra e conter só letras, números, '_', '.' ou '-' (sem espaço/acento)"
        )
    return value


def render(text: str, iflow_id: str, name: str, description: str) -> str:
    return (
        text.replace("__IFLOW_ID__", iflow_id)
        .replace("__IFLOW_NAME__", name)
        .replace("__DESCRIPTION__", description)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--id", required=True, type=valid_id, help="Bundle-SymbolicName (sem espaço/acento)")
    parser.add_argument("--name", help="Bundle-Name legível (padrão: igual ao id)")
    parser.add_argument("--out", required=True, help="Pasta onde o projeto <id>/ será criado")
    parser.add_argument("--description", default="", help="Descrição do iFlow (metainfo.prop)")
    parser.add_argument(
        "--with-query-script",
        action="store_true",
        help="Inclui script/ReadQueryParams.groovy (GET com parâmetros de query)",
    )
    parser.add_argument("--force", action="store_true", help="Sobrescreve a pasta se já existir")
    args = parser.parse_args()

    name = args.name or args.id
    target = Path(args.out).expanduser().resolve() / args.id
    if target.exists():
        if not args.force:
            print(f"ERRO: {target} já existe (use --force para sobrescrever)", file=sys.stderr)
            return 2
        shutil.rmtree(target)

    for src in TEMPLATES.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(TEMPLATES)
        # specs/ são exemplos para o agente, não vão para o pacote do iFlow
        if rel.parts and rel.parts[0] == "specs":
            continue
        if rel == QUERY_SCRIPT and not args.with_query_script:
            continue
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        content = src.read_text(encoding="utf-8")
        dst.write_text(render(content, args.id, name, args.description), encoding="utf-8", newline="\n")

    (target / IFLW_DIR).mkdir(parents=True, exist_ok=True)

    print(f"Projeto criado em {target}")
    print(f"Próximo passo: escrever {target / IFLW_DIR / (args.id + '.iflw')}")
    if args.with_query_script:
        print("Script incluído: src/main/resources/script/ReadQueryParams.groovy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
