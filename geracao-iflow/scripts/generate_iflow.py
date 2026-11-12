#!/usr/bin/env python3
"""Gera um iFlow completo a partir de uma especificação YAML/JSON curta.

Um único processo: scaffold → .iflw → parameters → validate → zip.
Passo json_to_xml emite o conversor do designer CI 6.84: raiz root, useNamespaces=true,
addXMLRootElement=true. XPath de validação usa /root/.... Não usa useNamespaceMapping.
Evita vários spawns de Python (lentos no Windows com antivírus).

Uso:
    python generate_iflow.py --spec caminho/spec.yaml
    python generate_iflow.py --spec caminho/spec.json --out D:/iflows --force

A spec mínima (padrão GET → API HTTP externa):

    id: IF_Consulta_CEP
    name: IF Consulta CEP
    description: Consulta CEP
    out: D:/iflows
    pattern: get_http_external
    required_params: [cep]
    sender:
      path_default: /cep
    receiver:
      name: ViaCEP
      address: "{{Externo_URL}}/ws/${property.qp_cep}/json"
      auth: None
      url_default: https://viacep.com.br
      credential_default: ""
      timeout_default: "60000"

Saída: <out>/<id>/ e <out>/<id>.zip (0 erros na validação).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
TEMPLATES = SKILL_DIR / "templates"
IFLW_REL = Path("src/main/resources/scenarioflows/integrationflow")
SCRIPT_REL = Path("src/main/resources/script")

sys.path.insert(0, str(SCRIPTS))
from iflw_builder import build_iflw, write_parameters  # noqa: E402
from validate_iflow import validate  # noqa: E402


def _load_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError:
            return _parse_minimal_yaml(text)
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise SystemExit("spec deve ser um objeto YAML/JSON")
    return data


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Parser YAML mínimo (mapas rasos + listas simples) para não depender de PyYAML."""
    # Preferência: se o usuário tiver PyYAML, usa. Senão, aceita JSON embutido ou
    # um subconjunto bem limitado — para specs complexas, use .json.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(0, root)]
    pending_key: str | None = None
    pending_indent = 0
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        cur = stack[-1][1]
        if line.startswith("- "):
            item = line[2:].strip()
            if pending_key is not None and not isinstance(cur, list):
                lst: list[Any] = []
                if isinstance(cur, dict):
                    cur[pending_key] = lst
                stack.append((pending_indent + 2, lst))
                cur = lst
                pending_key = None
            if not isinstance(cur, list):
                raise SystemExit(f"lista YAML inesperada: {line}")
            if ":" in item and not item.startswith("{"):
                # - type: foo
                key, _, val = item.partition(":")
                obj = {key.strip(): _scalar(val.strip())}
                cur.append(obj)
                stack.append((indent + 2, obj))
            else:
                cur.append(_scalar(item))
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if not isinstance(cur, dict):
                raise SystemExit(f"chave YAML fora de mapa: {line}")
            if val == "":
                # valor composto vem nas próximas linhas
                placeholder: dict[str, Any] = {}
                cur[key] = placeholder
                pending_key = key
                pending_indent = indent
                stack.append((indent + 2, placeholder))
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                cur[key] = [_scalar(x.strip()) for x in inner.split(",") if x.strip()] if inner else []
                pending_key = None
            else:
                cur[key] = _scalar(val)
                pending_key = None
            continue
        raise SystemExit(
            "YAML complexo demais para o parser embutido. "
            "Instale PyYAML (`pip install pyyaml`) ou salve a spec como .json."
        )
    return root


def _scalar(val: str) -> Any:
    if val.lower() in {"true", "yes"}:
        return True
    if val.lower() in {"false", "no"}:
        return False
    if val.lower() in {"null", "~", ""}:
        return "" if val == "" else None
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    return val


def _scaffold(target: Path, iflow_id: str, name: str, description: str, with_query: bool) -> None:
    query_script = SCRIPT_REL / "ReadQueryParams.groovy"
    for src in TEMPLATES.rglob("*"):
        if not src.is_file():
            continue
        # não copiar specs/ de exemplo para o projeto
        rel = src.relative_to(TEMPLATES)
        if rel.parts and rel.parts[0] == "specs":
            continue
        if rel == query_script and not with_query:
            continue
        # scripts de pattern não existem em templates raiz além de groovy
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        text = (
            text.replace("__IFLOW_ID__", iflow_id)
            .replace("__IFLOW_NAME__", name)
            .replace("__DESCRIPTION__", description)
        )
        dst.write_text(text, encoding="utf-8", newline="\n")
    (target / IFLW_REL).mkdir(parents=True, exist_ok=True)


def _package(project: Path, out_zip: Path) -> int:
    exclude_dirs = {".git", "__pycache__", ".idea", ".vscode", "node_modules"}
    exclude_files = {".DS_Store", "Thumbs.db", "README.md"}
    files: list[Path] = []
    # Varredura direta das pastas conhecidas (evita rglob lento com AV)
    candidates = [
        project / ".project",
        project / "metainfo.prop",
        project / "META-INF" / "MANIFEST.MF",
    ]
    res = project / "src" / "main" / "resources"
    if res.is_dir():
        for path in res.rglob("*"):
            if path.is_file():
                candidates.append(path)
    for path in candidates:
        if not path.is_file():
            continue
        rel = path.relative_to(project)
        if any(part in exclude_dirs for part in rel.parts):
            continue
        if rel.name in exclude_files or rel.suffix == ".zip":
            continue
        files.append(rel)
    files.sort(key=lambda p: (p.as_posix() != "META-INF/MANIFEST.MF", p.as_posix()))
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    # ZIP_STORED: arquivos do iFlow são pequenos; evita CPU/AV em deflate
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in files:
            zf.write(project / rel, rel.as_posix())
    return len(files)


def generate(spec: dict[str, Any], *, force: bool = False, timing: bool = False) -> int:
    t0 = time.perf_counter()
    marks: list[tuple[str, float]] = []

    def mark(label: str) -> None:
        marks.append((label, time.perf_counter() - t0))

    iflow_id = spec["id"]
    name = spec.get("name") or iflow_id
    description = spec.get("description") or ""
    out_root = Path(spec.get("out") or ".").expanduser().resolve()
    target = out_root / iflow_id
    pattern = (spec.get("pattern") or "").lower()
    with_query = pattern in {"get_http_external", "a", "pattern_a", "get_odata"} or any(
        s.get("script") == "ReadQueryParams.groovy" for s in (spec.get("steps") or [])
    )
    # GET pattern sempre inclui query script
    if not spec.get("steps") and pattern in {"", "get_http_external", "a", "pattern_a"}:
        with_query = True
        spec.setdefault("pattern", "get_http_external")

    if target.exists():
        if not force:
            print(f"ERRO: {target} já existe (use --force)", file=sys.stderr)
            return 2
        shutil.rmtree(target)

    _scaffold(target, iflow_id, name, description, with_query)
    mark("scaffold")

    # receiver default address se pattern A
    if "receiver" not in spec and (spec.get("pattern") or "get_http_external").lower() in {
        "get_http_external",
        "a",
        "pattern_a",
    }:
        raise SystemExit("spec precisa de receiver.address para pattern get_http_external")

    iflw_xml = build_iflw(spec)
    iflw_path = target / IFLW_REL / f"{iflow_id}.iflw"
    iflw_path.write_text(iflw_xml, encoding="utf-8", newline="\n")
    mark("iflw")

    prop, propdef = write_parameters(spec)
    (target / "src/main/resources/parameters.prop").write_text(prop, encoding="utf-8", newline="\n")
    (target / "src/main/resources/parameters.propdef").write_text(propdef, encoding="utf-8", newline="\n")
    mark("params")

    rep = validate(target)
    for w in rep.warnings:
        print(f"AVISO: {w}")
    for e in rep.errors:
        print(f"ERRO:  {e}")
    mark("validate")
    if rep.errors:
        print(f"\n{len(rep.errors)} erro(s). Zip NÃO gerado. Projeto em {target}")
        return 1

    out_zip = Path(spec["zip"]).expanduser().resolve() if spec.get("zip") else out_root / f"{iflow_id}.zip"
    nfiles = _package(target, out_zip)
    mark("package")

    print(f"\nProjeto: {target}")
    print(f"Zip:     {out_zip} ({nfiles} arquivos)")
    print(f"{len(rep.errors)} erro(s), {len(rep.warnings)} aviso(s)")
    if timing or True:
        prev = 0.0
        print("Tempos:")
        for label, elapsed in marks:
            print(f"  {label}: {(elapsed - prev) * 1000:.0f} ms")
            prev = elapsed
        print(f"  total: {marks[-1][1] * 1000:.0f} ms")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True, help="caminho do YAML ou JSON de especificação")
    parser.add_argument("--out", help="sobrescreve spec.out")
    parser.add_argument("--force", action="store_true", help="sobrescreve pasta existente")
    parser.add_argument("--timing", action="store_true", help="imprime tempos por etapa (sempre ativo)")
    args = parser.parse_args()
    spec_path = Path(args.spec).expanduser().resolve()
    if not spec_path.is_file():
        print(f"ERRO: spec não encontrada: {spec_path}", file=sys.stderr)
        return 2
    spec = _load_spec(spec_path)
    if args.out:
        spec["out"] = args.out
    if "id" not in spec:
        print("ERRO: spec precisa do campo id", file=sys.stderr)
        return 2
    return generate(spec, force=args.force, timing=args.timing)


if __name__ == "__main__":
    sys.exit(main())
