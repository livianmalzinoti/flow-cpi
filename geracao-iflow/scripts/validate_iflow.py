#!/usr/bin/env python3
"""Valida um projeto de iFlow antes do empacotamento.

Uso:
    python3 validate_iflow.py <pasta-do-projeto> [--strict]

Sai com código 1 se houver erros. --strict trata avisos como erros.

Verifica:
  - arquivos obrigatórios (.project, metainfo.prop, META-INF/MANIFEST.MF, parameters.prop/.propdef, um .iflw)
  - MANIFEST.MF: campos SAP, continuação de linhas, linha em branco final
  - .iflw bem formado, com collaboration/process/diagrama
  - sequenceFlow/messageFlow apontando para ids existentes; incoming/outgoing consistentes
  - todo passo com activityType/componentVersion/cmdVariantUri
  - scripts, mappings, xsl, wsdl referenciados existem no pacote
  - externalização: {{Param}} usados x declarados; URL/credencial fixa em adapter receiver
  - Exception Subprocess presente quando há sender HTTPS/SOAP/ProcessDirect (fluxo síncrono)
  - uma BPMNShape por elemento e uma BPMNEdge por flow
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    "bpmn2": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "ifl": "http:///com.sap.ifl.model/Ifl.xsd",
}
RES = Path("src/main/resources")
IFLW_DIR = RES / "scenarioflows" / "integrationflow"
PARAM_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*\}\}")
URL_RE = re.compile(r"^\s*https?://", re.IGNORECASE)

# chaves de adapter cujo valor é endereço de rede e precisa ser externalizado
ADDRESS_KEYS = {"httpAddressWithoutQuery", "address", "host", "url", "serverUrl", "baseUrl"}
CREDENTIAL_KEYS = {"credentialName", "privateKeyAlias", "clientCertificateAlias", "locationId"}
TIMEOUT_KEYS = {"httpRequestTimeout", "requestTimeout", "timeout"}
SYNC_SENDERS = {"HTTPS", "SOAP", "ProcessDirect", "HTTP", "IDOC", "XI", "AS2", "OData"}

STEP_TAGS = {
    "callActivity",
    "serviceTask",
    "exclusiveGateway",
    "parallelGateway",
    "subProcess",
    "startEvent",
    "endEvent",
}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def q(tag: str, prefix: str = "bpmn2") -> str:
    return f"{{{NS[prefix]}}}{tag}"


def props(elem: ET.Element) -> dict[str, str]:
    """Retorna as ifl:property de um elemento como dict key -> value."""
    out: dict[str, str] = {}
    ext = elem.find(q("extensionElements"))
    if ext is None:
        return out
    for p in ext.findall(q("property", "ifl")):
        key = p.findtext("key")
        value = p.findtext("value")
        if key is not None:
            out[key] = value or ""
    return out


def check_required_files(project: Path, rep: Report) -> Path | None:
    for rel in [".project", "metainfo.prop", "META-INF/MANIFEST.MF", RES / "parameters.prop", RES / "parameters.propdef"]:
        if not (project / rel).is_file():
            rep.error(f"arquivo obrigatório ausente: {rel}")
    iflw_dir = project / IFLW_DIR
    iflws = sorted(iflw_dir.glob("*.iflw")) if iflw_dir.is_dir() else []
    if not iflws:
        rep.error(f"nenhum .iflw em {IFLW_DIR}")
        return None
    if len(iflws) > 1:
        rep.error(f"mais de um .iflw em {IFLW_DIR}: {[p.name for p in iflws]}")
    return iflws[0]


def check_manifest(project: Path, iflw: Path | None, rep: Report) -> None:
    mf = project / "META-INF" / "MANIFEST.MF"
    if not mf.is_file():
        return
    raw = mf.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        rep.error("MANIFEST.MF com BOM")
    text = raw.decode("utf-8", errors="replace")
    if not text.endswith("\n"):
        rep.error("MANIFEST.MF deve terminar com quebra de linha")
    if "\r" in text:
        rep.warn("MANIFEST.MF com CRLF; preferir LF")
    for line in text.splitlines():
        if len(line.encode("utf-8")) > 72:
            rep.error(f"MANIFEST.MF: linha com mais de 72 bytes: {line[:40]}...")
            break
    # junta continuações
    joined = re.sub(r"\n ", "", text)
    fields = dict(re.findall(r"^([A-Za-z0-9-]+): (.*)$", joined, flags=re.M))
    for key, expected in {
        "SAP-BundleType": "IntegrationFlow",
        "SAP-NodeType": "IFLMAP",
        "SAP-RuntimeProfile": "iflmap",
    }.items():
        if fields.get(key) != expected:
            rep.error(f"MANIFEST.MF: {key} deve ser '{expected}' (atual: {fields.get(key)!r})")
    for key in ["Bundle-Name", "Bundle-SymbolicName", "Bundle-Version", "Import-Package", "Import-Service"]:
        if key not in fields:
            rep.error(f"MANIFEST.MF: campo {key} ausente")
    symbolic = fields.get("Bundle-SymbolicName", "").split(";")[0].strip()
    if symbolic:
        if "__IFLOW_ID__" in symbolic or " " in symbolic:
            rep.error(f"MANIFEST.MF: Bundle-SymbolicName inválido: {symbolic!r}")
        if iflw is not None and iflw.stem != symbolic:
            rep.warn(f"nome do .iflw ({iflw.stem}) difere do Bundle-SymbolicName ({symbolic})")
        project_name = re.search(r"<name>(.*?)</name>", (project / ".project").read_text(encoding="utf-8", errors="replace")) if (project / ".project").is_file() else None
        if project_name and project_name.group(1) != symbolic:
            rep.warn(f".project <name> ({project_name.group(1)}) difere do Bundle-SymbolicName ({symbolic})")
    for placeholder in ["__IFLOW_ID__", "__IFLOW_NAME__"]:
        if placeholder in text:
            rep.error(f"MANIFEST.MF ainda contém o placeholder {placeholder}")
    meta = project / "metainfo.prop"
    if meta.is_file() and "__DESCRIPTION__" in meta.read_text(encoding="utf-8", errors="replace"):
        rep.warn("metainfo.prop ainda contém __DESCRIPTION__")


def load_params(project: Path, rep: Report) -> tuple[set[str], set[str]]:
    declared: set[str] = set()
    valued: set[str] = set()
    propdef = project / RES / "parameters.propdef"
    if propdef.is_file():
        try:
            root = ET.parse(propdef).getroot()
            for p in root.iter("param"):
                pid = p.get("id", "").strip()
                if not pid:
                    rep.error("parameters.propdef: <param> sem id")
                    continue
                if pid in declared:
                    rep.error(f"parameters.propdef: parâmetro duplicado {pid}")
                declared.add(pid)
                if p.findtext("type") not in {"xsd:string", "xsd:integer", "xsd:boolean"}:
                    rep.warn(f"parameters.propdef: tipo incomum em {pid}: {p.findtext('type')!r}")
        except ET.ParseError as exc:
            rep.error(f"parameters.propdef mal formado: {exc}")
    prop = project / RES / "parameters.prop"
    if prop.is_file():
        for line in prop.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip() or line.lstrip().startswith(("#", "!")):
                continue
            m = re.match(r"^\s*((?:\\.|[^=:\s])+)\s*[=:]", line)
            if m:
                valued.add(m.group(1).replace("\\", ""))
    for pid in sorted(declared - valued):
        rep.error(f"parâmetro {pid} está em parameters.propdef mas não em parameters.prop")
    for pid in sorted(valued - declared):
        rep.error(f"parâmetro {pid} está em parameters.prop mas não em parameters.propdef")
    return declared, valued


def check_iflw(project: Path, iflw: Path, declared: set[str], rep: Report) -> None:
    raw = iflw.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        rep.error(f"{iflw.name} com BOM")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        rep.error(f"{iflw.name} mal formado: {exc}")
        return
    if root.tag != q("definitions"):
        rep.error(f"{iflw.name}: raiz deve ser bpmn2:definitions")
        return

    collab = root.find(q("collaboration"))
    processes = root.findall(q("process"))
    if collab is None:
        rep.error("bpmn2:collaboration ausente")
    if not processes:
        rep.error("bpmn2:process ausente")

    # índice de ids
    ids: dict[str, ET.Element] = {}
    for elem in root.iter():
        eid = elem.get("id")
        if eid:
            if eid in ids:
                rep.error(f"id duplicado: {eid}")
            ids[eid] = elem

    # participants / processRef
    participants = collab.findall(q("participant")) if collab is not None else []
    process_ids = {p.get("id") for p in processes}
    for part in participants:
        ref = part.get("processRef")
        if ref and ref not in process_ids:
            rep.error(f"participant {part.get('id')} referencia processo inexistente {ref}")

    # message flows (adapters)
    sender_types: list[str] = []
    for mf in collab.findall(q("messageFlow")) if collab is not None else []:
        mid = mf.get("id")
        p = props(mf)
        src, tgt = mf.get("sourceRef"), mf.get("targetRef")
        for ref in (src, tgt):
            if ref not in ids:
                rep.error(f"messageFlow {mid}: referência a id inexistente {ref}")
        direction = p.get("direction")
        ctype = p.get("ComponentType", "?")
        if direction not in {"Sender", "Receiver"}:
            rep.error(f"messageFlow {mid}: property 'direction' deve ser Sender ou Receiver")
        if direction == "Sender":
            sender_types.append(ctype)
            if tgt in ids and ids[tgt].tag != q("startEvent"):
                rep.error(f"messageFlow {mid} (sender {ctype}): targetRef deve ser um startEvent")
        if direction == "Receiver" and src in ids and ids[src].tag != q("serviceTask"):
            rep.error(f"messageFlow {mid} (receiver {ctype}): sourceRef deve ser um serviceTask (Request Reply/Send)")
        for key in ["ComponentType", "cmdVariantUri", "componentVersion"]:
            if key not in p:
                rep.error(f"messageFlow {mid}: property {key} ausente")
        # externalização
        for key, value in p.items():
            if key in ADDRESS_KEYS and direction == "Receiver":
                if URL_RE.match(value) or (value and "{{" not in value and re.search(r"[A-Za-z0-9-]+\.[A-Za-z]{2,}", value)):
                    rep.error(f"adapter {ctype} ({mid}): '{key}' com endereço fixo '{value}'. Externalizar como {{{{Param}}}}")
                elif value and "{{" not in value:
                    rep.warn(f"adapter {ctype} ({mid}): '{key}' sem parâmetro externalizado ('{value}')")
            if key in CREDENTIAL_KEYS and value and "{{" not in value:
                rep.error(f"adapter {ctype} ({mid}): '{key}' fixo '{value}'. Externalizar como {{{{Param}}}}")
            if key in TIMEOUT_KEYS and value and "{{" not in value:
                rep.warn(f"adapter {ctype} ({mid}): '{key}' fixo '{value}'. Considerar externalizar")
            if key == "urlPath" and value and "{{" not in value:
                rep.warn(f"adapter {ctype} ({mid}): 'urlPath' fixo '{value}'. Considerar externalizar")
            if key == "wsdlURL" and value:
                rel = value.lstrip("/")
                if not (project / RES / rel).is_file():
                    rep.error(f"adapter {ctype} ({mid}): wsdlURL aponta para arquivo inexistente {RES / rel}")

    # steps
    flows: dict[str, tuple[str, str]] = {}
    incoming: dict[str, set[str]] = {}
    outgoing: dict[str, set[str]] = {}
    has_exception_subprocess = False
    groovy_steps: list[str] = []

    for proc in processes:
        for elem in proc.iter():
            local = elem.tag.split("}")[-1]
            eid = elem.get("id", "?")
            if local == "sequenceFlow":
                src, tgt = elem.get("sourceRef"), elem.get("targetRef")
                flows[eid] = (src, tgt)
                for ref in (src, tgt):
                    if ref not in ids:
                        rep.error(f"sequenceFlow {eid}: referência a id inexistente {ref}")
                continue
            if local not in STEP_TAGS:
                continue
            p = props(elem)
            name = elem.get("name", "")
            if local in {"callActivity", "serviceTask", "exclusiveGateway", "parallelGateway", "subProcess"}:
                if "activityType" not in p:
                    rep.error(f"{local} {eid} ('{name}'): activityType ausente")
                if not name.strip():
                    rep.warn(f"{local} {eid}: sem nome. Dar nome do que o passo faz")
            if local != "subProcess" or p.get("activityType") in {"ErrorEventSubProcessTemplate", "Process"}:
                for key in ["componentVersion", "cmdVariantUri"]:
                    if key not in p:
                        rep.error(f"{local} {eid} ('{name}'): {key} ausente")
            incoming[eid] = {e.text.strip() for e in elem.findall(q("incoming")) if e.text}
            outgoing[eid] = {e.text.strip() for e in elem.findall(q("outgoing")) if e.text}

            atype = p.get("activityType")
            if atype == "ErrorEventSubProcessTemplate":
                has_exception_subprocess = True
            if atype == "Script":
                script = p.get("script", "")
                groovy_steps.append(f"{name or eid} → {script}")
                if not script:
                    rep.error(f"Script {eid} ('{name}'): property 'script' vazia")
                elif not (project / RES / "script" / script).is_file():
                    rep.error(f"Script {eid} ('{name}'): arquivo {RES / 'script' / script} não existe")
                else:
                    gpath = project / RES / "script" / script
                    gbytes = gpath.read_bytes()
                    if gbytes.startswith(b"\xef\xbb\xbf"):
                        rep.error(f"{script}: arquivo com BOM (causa 'undefined could not be loaded')")
                    gtext = gbytes.decode("utf-8", errors="replace")
                    func = p.get("scriptFunction", "processData")
                    if not re.search(rf"\b{re.escape(func)}\s*\(", gtext):
                        rep.error(f"{script}: função '{func}' não encontrada")
                    if "@Grab" in gtext:
                        rep.error(f"{script}: @Grab não é permitido (sem dependência externa)")
                    if re.search(r"\bprintln\b", gtext):
                        rep.warn(f"{script}: println não aparece em lugar nenhum no CPI; usar messageLog")
                    if not re.search(r"Motivo do Groovy", gtext, re.IGNORECASE):
                        rep.warn(f"{script}: sem comentário 'Motivo do Groovy: ...' explicando por que não é processor nativo")
            if atype in {"Mapping", "XSLTMapping"}:
                mpath = p.get("mappingpath", "")
                if not mpath:
                    rep.error(f"{atype} {eid} ('{name}'): mappingpath ausente")
                elif not (project / mpath).is_file():
                    level = rep.warn if atype == "Mapping" else rep.error
                    level(f"{atype} {eid} ('{name}'): arquivo {mpath} não existe" + (" (criar/ligar no designer)" if atype == "Mapping" else ""))
            if atype == "ProcessCallElement" or atype == "LoopingProcessCall":
                pid = p.get("processId", "")
                if pid not in process_ids:
                    rep.error(f"{atype} {eid} ('{name}'): processId {pid!r} não existe")

    # consistência incoming/outgoing
    for fid, (src, tgt) in flows.items():
        if src in outgoing and fid not in outgoing[src]:
            rep.error(f"{src}: falta <bpmn2:outgoing>{fid}</bpmn2:outgoing>")
        if tgt in incoming and fid not in incoming[tgt]:
            rep.error(f"{tgt}: falta <bpmn2:incoming>{fid}</bpmn2:incoming>")
    for eid, outs in outgoing.items():
        for fid in outs:
            if fid not in flows:
                rep.error(f"{eid}: outgoing {fid} não é um sequenceFlow existente")
    for eid, ins in incoming.items():
        for fid in ins:
            if fid not in flows:
                rep.error(f"{eid}: incoming {fid} não é um sequenceFlow existente")
    # nós soltos
    for eid, elem in ids.items():
        local = elem.tag.split("}")[-1]
        if local in {"callActivity", "serviceTask", "exclusiveGateway", "parallelGateway"}:
            if not incoming.get(eid) or not outgoing.get(eid):
                rep.error(f"{local} {eid} ('{elem.get('name', '')}') não está ligado (incoming/outgoing vazio)")

    # routers: rotas com condição ou default
    for gw in root.iter(q("exclusiveGateway")):
        default = gw.get("default")
        for fid in outgoing.get(gw.get("id"), set()):
            flow = ids.get(fid)
            if flow is None:
                continue
            has_cond = flow.find(q("conditionExpression")) is not None
            if fid != default and not has_cond:
                rep.error(f"Router {gw.get('id')}: rota {fid} sem condição e não é default")
        if default and default not in flows:
            rep.error(f"Router {gw.get('id')}: default {default} não existe")

    check_json_to_xml(root, rep)

    # Validação de campos: JSON to XML → CM (xpath → properties) → Router NonXML.
    # O Router não carrega XPath boolean no body (quebra com SAXParseException).
    for flow in root.iter(q("sequenceFlow")):
        if props(flow).get("expressionType") != "XML":
            continue
        cond = flow.find(q("conditionExpression"))
        text = ((cond.text or "") if cond is not None else "").strip()
        if "boolean(" in text or "string-length(" in text or text.startswith("/"):
            rep.error(
                f"{flow.get('id')}: Router não usa XPath no body. Extraia cada campo num Content "
                "Modifier (Source Type xpath, Datatype java.lang.String) e compare "
                "${property.Nome} no Router NonXML."
            )

    if any(t in SYNC_SENDERS for t in sender_types) and not has_exception_subprocess:
        rep.error("fluxo com sender síncrono sem Exception Subprocess")

    check_designer_contract(root, rep)

    # parâmetros externalizados
    text = raw.decode("utf-8", errors="replace")
    used = set(PARAM_RE.findall(text))
    for pid in sorted(used - declared):
        rep.error(f"parâmetro {{{{{pid}}}}} usado no .iflw mas não declarado em parameters.propdef")
    for pid in sorted(declared - used):
        rep.warn(f"parâmetro {pid} declarado mas não usado no .iflw")
    for m in re.finditer(r"\{\{([^}]*)\}\}", text):
        inner = m.group(1)
        if not re.fullmatch(r"\s*[A-Za-z0-9_.\-]+\s*", inner):
            rep.error(f"nome de parâmetro inválido: {{{{{inner}}}}}")
    if "__IFLOW_ID__" in text or "__IFLOW_NAME__" in text:
        rep.error(f"{iflw.name} ainda contém placeholder __IFLOW_*__")

    # diagrama
    diagram = root.find(q("BPMNDiagram", "bpmndi"))
    if diagram is None:
        rep.error("bpmndi:BPMNDiagram ausente (o designer abre o fluxo vazio)")
    else:
        shapes = {s.get("bpmnElement") for s in diagram.iter(q("BPMNShape", "bpmndi"))}
        edges = {e.get("bpmnElement") for e in diagram.iter(q("BPMNEdge", "bpmndi"))}
        for eid, elem in ids.items():
            local = elem.tag.split("}")[-1]
            if local in STEP_TAGS or local == "participant":
                if eid not in shapes:
                    rep.error(f"sem BPMNShape para {local} {eid}")
            if local in {"sequenceFlow", "messageFlow"} and eid not in edges:
                rep.error(f"sem BPMNEdge para {local} {eid}")
        for ref in shapes | edges:
            if ref not in ids:
                rep.error(f"diagrama referencia elemento inexistente {ref}")

    if groovy_steps:
        rep.warn("passos Groovy no fluxo (confirmar que não há processor nativo): " + "; ".join(groovy_steps))


# Par de aspas, sem atravessar o fechamento. `!= '' and ... != ''` é válido;
# espaço só é inválido dentro de um literal ('texto com espaço').
# Define Router: operadores lógicos são as palavras and/or. && e || são recusados.
_NONXML_QUOTED = re.compile(r"'([^']*)'")
_ERROR_HTTP = r"400|401|403|404|405|409|415|422|429|500|502|503|504"


_END_CNAME = re.compile(r"cname::(?:MessageEndEvent|ErrorEndEvent|EndEvent)/")


_MOD_ROW_RE = re.compile(r"<row>(.*?)</row>", re.DOTALL | re.IGNORECASE)
_MOD_CELL_RE = re.compile(r"<cell id=['\"](\w+)['\"]>(.*?)</cell>", re.DOTALL | re.IGNORECASE)
_PROP_TEXT_TYPES = {"expression", "constant", "header", "property"}


def parse_modifier_table(table: str) -> list[dict[str, str]]:
    """Parseia headerTable/propertyTable (XML já desescapado pelo ElementTree)."""
    rows: list[dict[str, str]] = []
    for m in _MOD_ROW_RE.finditer(table or ""):
        cells = {k: v.strip() for k, v in _MOD_CELL_RE.findall(m.group(1))}
        if cells:
            rows.append(cells)
    return rows


def check_designer_contract(root: ET.Element, rep: Report) -> None:
    """Regras que o designer do Integration Suite recusa e o script antigo deixava passar."""
    for end in root.iter(q("endEvent")):
        p = props(end)
        uri = p.get("cmdVariantUri", "")
        if _END_CNAME.search(uri) and ("/version::1.1" in uri or p.get("componentVersion") == "1.1"):
            rep.error(
                f"{end.get('id')}: End Event / End Message / Error End versão 1.1 não é suportada "
                "no profile Cloud Integration ('component EndEvent with version 1.1 is not supported'). "
                "Usar cmdVariantUri version::1.0.0 e componentVersion 1.0."
            )

    for proc in root.findall(q("process")):
        for elem in proc.iter(q("callActivity")):
            p = props(elem)
            if p.get("activityType") == "Enricher":
                headers = p.get("headerTable", "")
                body = (p.get("bodyContent") or "").strip()
                wrap = (p.get("wrapContent") or "").strip()
                body_type = (p.get("bodyType") or "").strip()
                name = elem.get("name") or ""
                answers_caller = bool(re.search(r"responder|montar resposta", name, re.I)) or (
                    "CamelHttpResponseCode" in headers
                )
                if answers_caller:
                    if body_type != "expression":
                        rep.error(
                            f"{elem.get('id')} ('{name}'): Message Body Type deve ser expression. "
                            "Constant vazio ou tipo ausente deixa a aba Body vazia."
                        )
                    if not body or not wrap:
                        rep.error(
                            f"{elem.get('id')} ('{name}'): Message Body vazio. "
                            "Preencher bodyContent e wrapContent com o JSON (ou ${in.body}). "
                            "Headers sozinhos não devolvem body ao requisitante."
                        )
                if "CamelHttpResponseCode" in headers and re.search(
                    rf"id='Value'>(?:{_ERROR_HTTP})<", headers
                ):
                    if "{" not in body or "message" not in body:
                        rep.error(
                            f"{elem.get('id')} ('{name}'): resposta de erro ao requisitante "
                            "sem body JSON. Obrigatório objeto com message, no mínimo "
                            '{"message":"..."}.'
                        )
                for row in parse_modifier_table(p.get("propertyTable", "")):
                    ptype = (row.get("Type") or "").strip().lower()
                    dtype = (row.get("Datatype") or "").strip()
                    pname = row.get("Name") or ""
                    if ptype == "expression" and dtype != "java.lang.String":
                        rep.error(
                            f"{elem.get('id')} ('{name}'): property '{pname}' Type expression "
                            "exige Datatype java.lang.String (ex.: p_bodyOriginal = ${in.body}). "
                            "Sem isso o runtime pode guardar stream e JSON to XML/XPath falham "
                            "com SAXParseException."
                        )
                    elif ptype in _PROP_TEXT_TYPES and dtype != "java.lang.String":
                        rep.error(
                            f"{elem.get('id')} ('{name}'): property '{pname}' Type {ptype} "
                            "que guarda texto exige Datatype java.lang.String."
                        )
                    elif ptype == "xpath" and not dtype:
                        rep.warn(
                            f"{elem.get('id')} ('{name}'): property '{pname}' Type xpath sem "
                            "Datatype. Use java.lang.String para texto ou org.w3c.dom.NodeList "
                            "para nós."
                        )

    for sub in root.iter(q("subProcess")):
        p = props(sub)
        if p.get("activityType") != "ErrorEventSubProcessTemplate":
            continue
        sid = sub.get("id")
        if sub.get("triggeredByEvent") != "true":
            rep.error(f"Exception Subprocess {sid}: falta triggeredByEvent=\"true\"")
        if list(sub.iter(q("exclusiveGateway"))):
            rep.error(
                f"Exception Subprocess {sid}: não criar Router com cenários de exceção. "
                "Um único caminho: Error Start → Groovy (property responseErro) → Content Modifier → End Message."
            )
        starts = [
            s for s in sub.iter(q("startEvent"))
            if "ErrorStartEvent" in props(s).get("cmdVariantUri", "")
        ]
        if not starts:
            rep.error(f"Exception Subprocess {sid}: deve começar com Error Start Event")
        scripts = [c for c in sub.iter(q("callActivity")) if props(c).get("activityType") == "Script"]
        if not scripts:
            rep.error(
                f"Exception Subprocess {sid}: falta o Groovy que grava a property responseErro "
                "(CamelExceptionCaught). Não há processor nativo para isso."
            )
        for elem in sub.iter(q("callActivity")):
            ep = props(elem)
            if ep.get("activityType") != "Enricher":
                continue
            body = ep.get("bodyContent", "")
            headers = ep.get("headerTable", "")
            if "responseErro" not in body:
                rep.error(
                    f"{elem.get('id')} ('{elem.get('name', '')}'): body do Exception Subprocess deve ser "
                    '{"message":"${property.responseErro}"}.'
                )
            if (
                "CamelHttpResponseCode" not in headers
                or "id='Value'>400<" not in headers
                or "application/json" not in headers
            ):
                rep.error(
                    f"{elem.get('id')} ('{elem.get('name', '')}'): Exception Subprocess deve devolver "
                    "CamelHttpResponseCode 400 e Content-Type application/json."
                )
        ends = list(sub.iter(q("endEvent")))
        if len(ends) != 1:
            rep.error(
                f"Exception Subprocess {sid}: deve terminar em um único End Message ou Error End "
                f"(encontrados {len(ends)})."
            )
        elif not any(token in props(ends[0]).get("cmdVariantUri", "") for token in ("MessageEndEvent", "ErrorEndEvent")):
            rep.error(f"Exception Subprocess {sid}: o único fim deve ser End Message ou Error End")

    for flow in root.iter(q("sequenceFlow")):
        expr_type = props(flow).get("expressionType")
        cond = flow.find(q("conditionExpression"))
        if expr_type != "NonXML" or cond is None or not cond.text:
            continue
        text = cond.text.strip()
        if "&&" in text or "||" in text:
            bad = "&&" if "&&" in text else "||"
            rep.error(
                f"{flow.get('id')}: Token '{bad}' not supported in NonXML condition. "
                "Expected tokens: [and, or]. "
                "Ex.: ${property.PurchaseOrderType} != '' and ${property.CompanyCode} != ''"
            )
            continue
        quoted_has_space = any(re.search(r"\s", q) for q in _NONXML_QUOTED.findall(text))
        if "|" in text or quoted_has_space:
            rep.error(
                f"{flow.get('id')}: condição NonXML inválida para o designer "
                f"('Invalid format of condition expression value'). Sem espaço dentro das aspas e sem '|'. "
                "Um token por rota; OR vira várias rotas. Texto com espaço vai para uma property."
            )


def check_json_to_xml(root: ET.Element, rep: Report) -> None:
    """CI 6.84 só converte com raiz root, useNamespaces=true e addXMLRootElement=true.

    useNamespaceMapping não substitui useNamespaces. Sem XML, o XPath seguinte vê JSON e
    quebra com Content is not allowed in prolog / InvalidXPathException.
    """
    for elem in root.iter(q("callActivity")):
        p = props(elem)
        if p.get("activityType") != "JsonToXmlConverter":
            continue
        eid = elem.get("id")
        label = f"{eid} ('{elem.get('name', '')}')"
        if p.get("additionalRootElementName") != "root":
            rep.error(
                f"{label}: JSON to XML additionalRootElementName deve ser 'root' "
                "(export do designer). Outro nome não converte; o XPath vê JSON "
                "(Content is not allowed in prolog)."
            )
        if p.get("useNamespaces") != "true":
            rep.error(
                f"{label}: JSON to XML precisa de useNamespaces=true. "
                "useNamespaceMapping não é a chave deste passo. Sem useNamespaces o "
                "conversor não gera XML (Content is not allowed in prolog)."
            )
        if p.get("addXMLRootElement") != "true":
            rep.error(f"{label}: JSON to XML addXMLRootElement deve ser true.")
    for elem in root.iter():
        table = props(elem).get("propertyTable") or ""
        if "xpath" not in table or "/Request" not in table:
            continue
        if re.search(r"/Request(?:/|\)|\[)", table):
            rep.error(
                f"{elem.get('id')}: XPath de validação usa /root/..., não /Request/. "
                "A raiz do JSON to XML é root."
            )


def validate(project: Path, strict: bool = False) -> Report:
    rep = Report()
    if not project.is_dir():
        rep.error(f"pasta não encontrada: {project}")
        return rep
    iflw = check_required_files(project, rep)
    check_manifest(project, iflw, rep)
    declared, _ = load_params(project, rep)
    if iflw is not None:
        check_iflw(project, iflw, declared, rep)
    if strict and rep.warnings:
        rep.errors.extend(f"[strict] {w}" for w in rep.warnings)
        rep.warnings.clear()
    return rep


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", help="pasta do projeto do iFlow (a que contém .project e src/)")
    parser.add_argument("--strict", action="store_true", help="avisos contam como erro")
    args = parser.parse_args()
    rep = validate(Path(args.project).expanduser().resolve(), args.strict)
    for w in rep.warnings:
        print(f"AVISO: {w}")
    for e in rep.errors:
        print(f"ERRO:  {e}")
    print(f"\n{len(rep.errors)} erro(s), {len(rep.warnings)} aviso(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
