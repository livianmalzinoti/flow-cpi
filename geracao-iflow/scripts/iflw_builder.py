#!/usr/bin/env python3
"""Monta .iflw BPMN2 a partir de uma especificação curta (dict).

Usado por generate_iflow.py. Não inventa processors: só emite XML validado
para os blocos suportados (HTTPS sender, HTTP receiver, CM, Script, Request
Reply, Router NonXML, Exception Subprocess, End Message 1.0).
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any
from xml.sax.saxutils import escape


def _nonxml_condition(text: str) -> str:
    """Define Router: Non-XML usa as palavras and/or. && e || são recusados no runtime."""
    text = text.replace("&&", " and ").replace("||", " or ")
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


def _esc(text: str) -> str:
    # Não escapar apóstrofo: o designer/validator espera id='Value' no headerTable.
    return escape(text, {"\"": "&quot;"})


def _prop(key: str, value: str) -> str:
    return (
        f"        <ifl:property><key>{_esc(key)}</key>"
        f"<value>{_esc(value)}</value></ifl:property>"
    )


def _props(pairs: list[tuple[str, str]], indent: str = "        ") -> str:
    lines = []
    for key, value in pairs:
        lines.append(
            f"{indent}<ifl:property><key>{_esc(key)}</key>"
            f"<value>{_esc(value)}</value></ifl:property>"
        )
    return "\n".join(lines)


def header_rows(headers: list[tuple[str, str]]) -> str:
    """Lista (nome, valor) → XML de headerTable (sem escapar aspas simples)."""
    parts: list[str] = []
    for name, value in headers:
        # Só & < > — manter id='...' como no designer; _esc no property cuida do resto.
        v = html.escape(value, quote=False)
        n = html.escape(name, quote=False)
        parts.append(
            "<row><cell id='Action'>Create</cell><cell id='Type'>constant</cell>"
            f"<cell id='Value'>{v}</cell>"
            f"<cell id='Default'></cell><cell id='Name'>{n}</cell>"
            "<cell id='Datatype'></cell></row>"
        )
    return "".join(parts)


def property_rows(props: list[tuple[str, str, str]]) -> str:
    """Lista (nome, type, value) → propertyTable. type: constant|header|property|expression|xpath.

    Datatype: expression/constant/header/property → java.lang.String (texto).
    xpath → java.lang.String por padrão (texto); quem precisar de NodeList passa tipo no builder depois.
    """
    parts: list[str] = []
    text_types = {"expression", "constant", "header", "property", "xpath"}
    for name, ptype, value in props:
        dtype = "java.lang.String" if ptype in text_types else ""
        parts.append(
            "<row><cell id='Action'>Create</cell>"
            f"<cell id='Type'>{html.escape(ptype, quote=False)}</cell>"
            f"<cell id='Value'>{html.escape(value, quote=False)}</cell>"
            f"<cell id='Default'></cell><cell id='Name'>{html.escape(name, quote=False)}</cell>"
            f"<cell id='Datatype'>{dtype}</cell></row>"
        )
    return "".join(parts)


@dataclass
class Node:
    id: str
    kind: str  # start|end|cm|script|rr|router|subprocess_placeholder
    name: str
    xml: str
    width: float = 100.0
    height: float = 60.0


@dataclass
class Edge:
    id: str
    source: str
    target: str
    condition: str | None = None  # NonXML expression text or None
    is_default: bool = False


@dataclass
class Builder:
    call_n: int = 0
    service_n: int = 0
    seq_n: int = 0
    gw_n: int = 0
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    main_ids: list[str] = field(default_factory=list)  # ordem linear principal (sem subprocess)

    def _next_call(self) -> str:
        self.call_n += 1
        return f"CallActivity_{self.call_n}"

    def _next_service(self) -> str:
        self.service_n += 1
        return f"ServiceTask_{self.service_n}"

    def _next_seq(self) -> str:
        self.seq_n += 1
        return f"SequenceFlow_{self.seq_n}"

    def _next_gw(self) -> str:
        self.gw_n += 1
        return f"ExclusiveGateway_{self.gw_n}"

    def link(self, source: str, target: str, condition: str | None = None, is_default: bool = False) -> str:
        fid = self._next_seq()
        self.edges.append(Edge(fid, source, target, condition, is_default))
        return fid

    def add_start(self) -> str:
        nid = "StartEvent_2"
        xml = f"""    <bpmn2:startEvent id="{nid}" name="Start">
      <bpmn2:extensionElements>
{_props([
    ("componentVersion", "1.0"),
    ("cmdVariantUri", "ctype::FlowstepVariant/cname::MessageStartEvent/version::1.0.0"),
])}
      </bpmn2:extensionElements>
      <bpmn2:outgoing>__OUT__</bpmn2:outgoing>
      <bpmn2:messageEventDefinition/>
    </bpmn2:startEvent>"""
        self.nodes.append(Node(nid, "start", "Start", xml, 32, 32))
        self.main_ids.append(nid)
        return nid

    def add_end(self) -> str:
        nid = "EndEvent_2"
        xml = f"""    <bpmn2:endEvent id="{nid}" name="End">
      <bpmn2:extensionElements>
{_props([
    ("componentVersion", "1.0"),
    ("cmdVariantUri", "ctype::FlowstepVariant/cname::MessageEndEvent/version::1.0.0"),
])}
      </bpmn2:extensionElements>
      <bpmn2:incoming>__IN__</bpmn2:incoming>
      <bpmn2:messageEventDefinition/>
    </bpmn2:endEvent>"""
        self.nodes.append(Node(nid, "end", "End", xml, 32, 32))
        self.main_ids.append(nid)
        return nid

    def add_content_modifier(
        self,
        name: str,
        *,
        body: str | None = None,
        headers: list[tuple[str, str]] | None = None,
        properties: list[tuple[str, str, str]] | None = None,
        body_type: str | None = "expression",
    ) -> str:
        nid = self._next_call()
        body_val = body if body is not None else ""
        wrap_val = body_val
        # Passo só de header/property: bodyType vazio para não apagar body
        if body is None and body_type == "expression":
            bt = ""
            wrap_val = ""
        else:
            bt = body_type or ""
        pairs = [
            ("bodyType", bt),
            ("bodyContent", body_val),
            ("wrapContent", wrap_val if bt else ""),
            ("headerTable", header_rows(headers or [])),
            ("propertyTable", property_rows(properties or [])),
            ("componentVersion", "1.5"),
            ("activityType", "Enricher"),
            ("cmdVariantUri", "ctype::FlowstepVariant/cname::Enricher/version::1.5.0"),
        ]
        xml = f"""    <bpmn2:callActivity id="{nid}" name="{_esc(name)}">
      <bpmn2:extensionElements>
{_props(pairs)}
      </bpmn2:extensionElements>
      <bpmn2:incoming>__IN__</bpmn2:incoming>
      <bpmn2:outgoing>__OUT__</bpmn2:outgoing>
    </bpmn2:callActivity>"""
        self.nodes.append(Node(nid, "cm", name, xml))
        self.main_ids.append(nid)
        return nid

    def add_json_to_xml(self, name: str) -> str:
        """JSON to XML como o designer CI 6.84 exporta o passo que converte.

        additionalRootElementName=root, useNamespaces=true, addXMLRootElement=true.
        A chave useNamespaceMapping não faz este tenant converter (o body segue JSON e o
        XPath seguinte quebra com Content is not allowed in prolog).
        """
        nid = self._next_call()
        pairs = [
            ("additionalRootElementName", "root"),
            ("additionalRootElementNamespace", ""),
            ("jsonNamespaceMapping", ""),
            ("useNamespaces", "true"),
            ("jsonNamespaceSeparator", ":"),
            ("addXMLRootElement", "true"),
            ("componentVersion", "1.1"),
            ("activityType", "JsonToXmlConverter"),
            ("cmdVariantUri", "ctype::FlowstepVariant/cname::JsonToXmlConverter/version::1.1.2"),
        ]
        xml = f"""    <bpmn2:callActivity id="{nid}" name="{_esc(name)}">
      <bpmn2:extensionElements>
{_props(pairs)}
      </bpmn2:extensionElements>
      <bpmn2:incoming>__IN__</bpmn2:incoming>
      <bpmn2:outgoing>__OUT__</bpmn2:outgoing>
    </bpmn2:callActivity>"""
        self.nodes.append(Node(nid, "json_to_xml", name, xml))
        self.main_ids.append(nid)
        return nid

    def add_script(self, name: str, script: str) -> str:
        nid = self._next_call()
        pairs = [
            ("scriptFunction", "processData"),
            ("scriptBundleId", ""),
            ("script", script),
            ("subActivityType", "GroovyScript"),
            ("componentVersion", "1.1"),
            ("activityType", "Script"),
            ("cmdVariantUri", "ctype::FlowstepVariant/cname::GroovyScript/version::1.1.2"),
        ]
        xml = f"""    <bpmn2:callActivity id="{nid}" name="{_esc(name)}">
      <bpmn2:extensionElements>
{_props(pairs)}
      </bpmn2:extensionElements>
      <bpmn2:incoming>__IN__</bpmn2:incoming>
      <bpmn2:outgoing>__OUT__</bpmn2:outgoing>
    </bpmn2:callActivity>"""
        self.nodes.append(Node(nid, "script", name, xml))
        self.main_ids.append(nid)
        return nid

    def add_request_reply(self, name: str) -> str:
        nid = self._next_service()
        pairs = [
            ("componentVersion", "1.0"),
            ("activityType", "ExternalCall"),
            ("cmdVariantUri", "ctype::FlowstepVariant/cname::ExternalCall/version::1.0.4"),
        ]
        xml = f"""    <bpmn2:serviceTask id="{nid}" name="{_esc(name)}">
      <bpmn2:extensionElements>
{_props(pairs)}
      </bpmn2:extensionElements>
      <bpmn2:incoming>__IN__</bpmn2:incoming>
      <bpmn2:outgoing>__OUT__</bpmn2:outgoing>
    </bpmn2:serviceTask>"""
        self.nodes.append(Node(nid, "rr", name, xml))
        self.main_ids.append(nid)
        return nid

    def add_router(self, name: str, routes: list[dict[str, Any]], default_target: str) -> str:
        """routes: [{condition: NonXML, target: id}, ...]; default_target é id do nó default.

        Condição NonXML: palavras and/or. && e || são reescritos na emissão do sequence flow.
        """
        gid = self._next_gw()
        # edges criados depois pelo caller via link(); aqui só o gateway
        xml = f"""    <bpmn2:exclusiveGateway default="__DEFAULT__" id="{gid}" name="{_esc(name)}">
      <bpmn2:extensionElements>
{_props([
    ("componentVersion", "1.1"),
    ("activityType", "ExclusiveGateway"),
    ("cmdVariantUri", "ctype::FlowstepVariant/cname::ExclusiveGateway/version::1.1.0"),
    ("routingExpressionType", "NonXML"),
])}
      </bpmn2:extensionElements>
      <bpmn2:incoming>__IN__</bpmn2:incoming>
      <bpmn2:outgoing>__OUTS__</bpmn2:outgoing>
    </bpmn2:exclusiveGateway>"""
        self.nodes.append(Node(gid, "router", name, xml, 40, 40))
        self.main_ids.append(gid)
        # stash routes on node via name convention — store in edges after
        for route in routes:
            self.link(gid, route["target"], condition=route["condition"], is_default=False)
        self.link(gid, default_target, is_default=True)
        return gid

    def exception_subprocess_xml(self) -> str:
        """Bloco fixo validado: Error Start → Groovy → CM 400 JSON → End Message 1.0."""
        err_body = '{\n  "message": "${property.responseErro}"\n}'
        return f"""    <bpmn2:subProcess id="SubProcess_1" name="Exception Subprocess" triggeredByEvent="true">
      <bpmn2:extensionElements>
{_props([
    ("componentVersion", "1.0"),
    ("activityType", "ErrorEventSubProcessTemplate"),
    ("cmdVariantUri", "ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.0.0"),
])}
      </bpmn2:extensionElements>
      <bpmn2:startEvent id="StartEvent_3" name="Error Start">
        <bpmn2:extensionElements>
{_props([
    ("componentVersion", "1.0"),
    ("cmdVariantUri", "ctype::FlowstepVariant/cname::ErrorStartEvent/version::1.0.0"),
], "          ")}
        </bpmn2:extensionElements>
        <bpmn2:outgoing>SequenceFlow_E1</bpmn2:outgoing>
        <bpmn2:errorEventDefinition/>
      </bpmn2:startEvent>
      <bpmn2:callActivity id="CallActivity_E1" name="Gravar responseErro">
        <bpmn2:extensionElements>
{_props([
    ("scriptFunction", "processData"),
    ("scriptBundleId", ""),
    ("script", "GravarResponseErro.groovy"),
    ("subActivityType", "GroovyScript"),
    ("componentVersion", "1.1"),
    ("activityType", "Script"),
    ("cmdVariantUri", "ctype::FlowstepVariant/cname::GroovyScript/version::1.1.2"),
], "          ")}
        </bpmn2:extensionElements>
        <bpmn2:incoming>SequenceFlow_E1</bpmn2:incoming>
        <bpmn2:outgoing>SequenceFlow_E2</bpmn2:outgoing>
      </bpmn2:callActivity>
      <bpmn2:callActivity id="CallActivity_E2" name="Montar resposta de erro">
        <bpmn2:extensionElements>
{_props([
    ("bodyType", "expression"),
    ("bodyContent", err_body),
    ("wrapContent", err_body),
    ("headerTable", header_rows([("Content-Type", "application/json"), ("CamelHttpResponseCode", "400")])),
    ("propertyTable", ""),
    ("componentVersion", "1.5"),
    ("activityType", "Enricher"),
    ("cmdVariantUri", "ctype::FlowstepVariant/cname::Enricher/version::1.5.0"),
], "          ")}
        </bpmn2:extensionElements>
        <bpmn2:incoming>SequenceFlow_E2</bpmn2:incoming>
        <bpmn2:outgoing>SequenceFlow_E3</bpmn2:outgoing>
      </bpmn2:callActivity>
      <bpmn2:endEvent id="EndEvent_3" name="End">
        <bpmn2:extensionElements>
{_props([
    ("componentVersion", "1.0"),
    ("cmdVariantUri", "ctype::FlowstepVariant/cname::MessageEndEvent/version::1.0.0"),
], "          ")}
        </bpmn2:extensionElements>
        <bpmn2:incoming>SequenceFlow_E3</bpmn2:incoming>
        <bpmn2:messageEventDefinition/>
      </bpmn2:endEvent>
      <bpmn2:sequenceFlow id="SequenceFlow_E1" sourceRef="StartEvent_3" targetRef="CallActivity_E1" isImmediate="true"/>
      <bpmn2:sequenceFlow id="SequenceFlow_E2" sourceRef="CallActivity_E1" targetRef="CallActivity_E2" isImmediate="true"/>
      <bpmn2:sequenceFlow id="SequenceFlow_E3" sourceRef="CallActivity_E2" targetRef="EndEvent_3" isImmediate="true"/>
    </bpmn2:subProcess>"""


def https_sender_message_flow(start_id: str, path_expr: str = "{{Sender_Path}}") -> str:
    return f"""    <bpmn2:messageFlow id="MessageFlow_1" name="HTTPS" sourceRef="Participant_1" targetRef="{start_id}">
      <bpmn2:extensionElements>
{_props([
    ("ComponentType", "HTTPS"),
    ("Name", "HTTPS"),
    ("ComponentNS", "sap"),
    ("ComponentSWCVName", "external"),
    ("ComponentSWCVId", "1.5.1"),
    ("TransportProtocol", "HTTPS"),
    ("TransportProtocolVersion", "1.5.1"),
    ("MessageProtocol", "None"),
    ("MessageProtocolVersion", "1.5.1"),
    ("direction", "Sender"),
    ("system", "Sender"),
    ("urlPath", path_expr),
    ("senderAuthType", "RoleBased"),
    ("userRole", "ESBMessaging.send"),
    ("xsrfProtection", "false"),
    ("maximumBodySize", "40"),
    ("componentVersion", "1.5"),
    ("cmdVariantUri", "ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.1"),
])}
      </bpmn2:extensionElements>
    </bpmn2:messageFlow>"""


def http_receiver_message_flow(
    service_task_id: str,
    *,
    address: str,
    query: str = "",
    method: str = "GET",
    credential: str = "{{Externo_Credential}}",
    timeout: str = "{{Request_Timeout}}",
    auth_method: str = "Basic",
    send_body: bool = False,
) -> str:
    pairs = [
        ("ComponentType", "HTTP"),
        ("Name", "HTTP"),
        ("ComponentNS", "sap"),
        ("ComponentSWCVName", "external"),
        ("ComponentSWCVId", "1.14.0"),
        ("TransportProtocol", "HTTP"),
        ("TransportProtocolVersion", "1.14.0"),
        ("MessageProtocol", "None"),
        ("MessageProtocolVersion", "1.14.0"),
        ("direction", "Receiver"),
        ("system", "Receiver"),
        ("httpAddressWithoutQuery", address),
        ("httpAddressQuery", query),
        ("httpMethod", method),
        ("httpShouldSendBody", "true" if send_body else "false"),
        ("httpRequestTimeout", timeout),
        ("authenticationMethod", auth_method),
        ("credentialName", credential if auth_method != "None" else ""),
        ("proxyType", "default"),
        ("throwExceptionOnFailure", "true"),
        ("httpErrorResponseCodes", ""),
        ("componentVersion", "1.14"),
        ("cmdVariantUri", "ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.14.0"),
    ]
    return f"""    <bpmn2:messageFlow id="MessageFlow_2" name="HTTP" sourceRef="{service_task_id}" targetRef="Participant_2">
      <bpmn2:extensionElements>
{_props(pairs)}
      </bpmn2:extensionElements>
    </bpmn2:messageFlow>"""


def _wire_incomings_outgoings(b: Builder) -> None:
    incoming: dict[str, list[str]] = {n.id: [] for n in b.nodes}
    outgoing: dict[str, list[str]] = {n.id: [] for n in b.nodes}
    default_flow: dict[str, str] = {}
    for e in b.edges:
        outgoing.setdefault(e.source, []).append(e.id)
        incoming.setdefault(e.target, []).append(e.id)
        if e.is_default:
            default_flow[e.source] = e.id

    by_id = {n.id: n for n in b.nodes}
    for n in b.nodes:
        xml = n.xml
        outs = outgoing.get(n.id, [])
        ins = incoming.get(n.id, [])
        if n.kind == "router":
            xml = xml.replace("__DEFAULT__", default_flow.get(n.id, outs[-1] if outs else ""))
            out_xml = "\n".join(f"      <bpmn2:outgoing>{fid}</bpmn2:outgoing>" for fid in outs)
            xml = xml.replace("      <bpmn2:outgoing>__OUTS__</bpmn2:outgoing>", out_xml)
            if "__IN__" in xml:
                if len(ins) == 1:
                    xml = xml.replace("__IN__", ins[0])
                else:
                    in_xml = "\n".join(f"      <bpmn2:incoming>{fid}</bpmn2:incoming>" for fid in ins)
                    xml = xml.replace("      <bpmn2:incoming>__IN__</bpmn2:incoming>", in_xml)
        else:
            if "__OUT__" in xml:
                if len(outs) == 1:
                    xml = xml.replace("__OUT__", outs[0])
                else:
                    out_xml = "\n".join(f"      <bpmn2:outgoing>{fid}</bpmn2:outgoing>" for fid in outs)
                    xml = xml.replace("      <bpmn2:outgoing>__OUT__</bpmn2:outgoing>", out_xml)
            if "__IN__" in xml:
                if len(ins) == 1:
                    xml = xml.replace("__IN__", ins[0])
                else:
                    in_xml = "\n".join(f"      <bpmn2:incoming>{fid}</bpmn2:incoming>" for fid in ins)
                    xml = xml.replace("      <bpmn2:incoming>__IN__</bpmn2:incoming>", in_xml)
        n.xml = xml
        _ = by_id  # silence lint


def _sequence_flow_xml(e: Edge) -> str:
    if not e.condition:
        return (
            f'    <bpmn2:sequenceFlow id="{e.id}" sourceRef="{e.source}" '
            f'targetRef="{e.target}" isImmediate="true"/>'
        )
    ext = f"""
      <bpmn2:extensionElements>
{_props([("expressionType", "NonXML"), ("componentVersion", "1.0")])}
      </bpmn2:extensionElements>"""
    cond = (
        f'\n      <bpmn2:conditionExpression id="Condition_{e.id}" '
        f'xsi:type="bpmn2:tFormalExpression">{_esc(_nonxml_condition(e.condition))}</bpmn2:conditionExpression>'
    )
    return (
        f'    <bpmn2:sequenceFlow id="{e.id}" sourceRef="{e.source}" '
        f'targetRef="{e.target}" isImmediate="true">{ext}{cond}\n'
        f"    </bpmn2:sequenceFlow>"
    )


def _diagram(b: Builder, has_receiver: bool) -> str:
    # layout linear
    x0, y = 300.0, 142.0
    gap = 150.0
    positions: dict[str, tuple[float, float, float, float]] = {}
    x = x0
    for nid in b.main_ids:
        node = next(n for n in b.nodes if n.id == nid)
        w, h = node.width, node.height
        cy = y + (60 - h) / 2 if h < 60 else y
        positions[nid] = (x, cy, w, h)
        x += gap

    # exception subprocess shapes
    positions["SubProcess_1"] = (300.0, 300.0, 620.0, 180.0)
    positions["StartEvent_3"] = (320.0, 374.0, 32.0, 32.0)
    positions["CallActivity_E1"] = (400.0, 360.0, 100.0, 60.0)
    positions["CallActivity_E2"] = (560.0, 360.0, 100.0, 60.0)
    positions["EndEvent_3"] = (720.0, 374.0, 32.0, 32.0)

    process_w = max(1000.0, x - x0 + 200)
    shapes: list[str] = [
        '      <bpmndi:BPMNShape bpmnElement="Participant_1" id="BPMNShape_Participant_1">\n'
        '        <dc:Bounds height="140.0" width="100.0" x="40.0" y="100.0"/>\n'
        "      </bpmndi:BPMNShape>",
        '      <bpmndi:BPMNShape bpmnElement="Participant_Process_1" id="BPMNShape_Participant_Process_1">\n'
        f'        <dc:Bounds height="440.0" width="{process_w:.1f}" x="240.0" y="60.0"/>\n'
        "      </bpmndi:BPMNShape>",
    ]
    if has_receiver:
        shapes.append(
            '      <bpmndi:BPMNShape bpmnElement="Participant_2" id="BPMNShape_Participant_2">\n'
            '        <dc:Bounds height="140.0" width="100.0" x="830.0" y="560.0"/>\n'
            "      </bpmndi:BPMNShape>"
        )
    for eid, (px, py, w, h) in positions.items():
        shapes.append(
            f'      <bpmndi:BPMNShape bpmnElement="{eid}" id="BPMNShape_{eid}">\n'
            f'        <dc:Bounds height="{h:.1f}" width="{w:.1f}" x="{px:.1f}" y="{py:.1f}"/>\n'
            "      </bpmndi:BPMNShape>"
        )

    edges_xml: list[str] = []
    for e in b.edges:
        sx, sy, sw, sh = positions[e.source]
        tx, ty, tw, th = positions[e.target]
        x1, y1 = sx + sw, sy + sh / 2
        x2, y2 = tx, ty + th / 2
        edges_xml.append(
            f'      <bpmndi:BPMNEdge bpmnElement="{e.id}" id="BPMNEdge_{e.id}" '
            f'sourceElement="BPMNShape_{e.source}" targetElement="BPMNShape_{e.target}">\n'
            f'        <di:waypoint x="{x1:.1f}" xsi:type="dc:Point" y="{y1:.1f}"/>\n'
            f'        <di:waypoint x="{x2:.1f}" xsi:type="dc:Point" y="{y2:.1f}"/>\n'
            "      </bpmndi:BPMNEdge>"
        )
    # exception edges
    for fid, src, tgt in [
        ("SequenceFlow_E1", "StartEvent_3", "CallActivity_E1"),
        ("SequenceFlow_E2", "CallActivity_E1", "CallActivity_E2"),
        ("SequenceFlow_E3", "CallActivity_E2", "EndEvent_3"),
    ]:
        sx, sy, sw, sh = positions[src]
        tx, ty, tw, th = positions[tgt]
        edges_xml.append(
            f'      <bpmndi:BPMNEdge bpmnElement="{fid}" id="BPMNEdge_{fid}" '
            f'sourceElement="BPMNShape_{src}" targetElement="BPMNShape_{tgt}">\n'
            f'        <di:waypoint x="{sx + sw:.1f}" xsi:type="dc:Point" y="{sy + sh / 2:.1f}"/>\n'
            f'        <di:waypoint x="{tx:.1f}" xsi:type="dc:Point" y="{ty + th / 2:.1f}"/>\n'
            "      </bpmndi:BPMNEdge>"
        )
    # message flows
    start = positions["StartEvent_2"]
    edges_xml.append(
        '      <bpmndi:BPMNEdge bpmnElement="MessageFlow_1" id="BPMNEdge_MessageFlow_1" '
        'sourceElement="BPMNShape_Participant_1" targetElement="BPMNShape_StartEvent_2">\n'
        f'        <di:waypoint x="140.0" xsi:type="dc:Point" y="170.0"/>\n'
        f'        <di:waypoint x="{start[0]:.1f}" xsi:type="dc:Point" y="{start[1] + start[3] / 2:.1f}"/>\n'
        "      </bpmndi:BPMNEdge>"
    )
    rr = next((n for n in b.nodes if n.kind == "rr"), None)
    if rr and has_receiver:
        rx, ry, rw, rh = positions[rr.id]
        edges_xml.append(
            f'      <bpmndi:BPMNEdge bpmnElement="MessageFlow_2" id="BPMNEdge_MessageFlow_2" '
            f'sourceElement="BPMNShape_{rr.id}" targetElement="BPMNShape_Participant_2">\n'
            f'        <di:waypoint x="{rx + rw / 2:.1f}" xsi:type="dc:Point" y="{ry + rh:.1f}"/>\n'
            f'        <di:waypoint x="{rx + rw / 2:.1f}" xsi:type="dc:Point" y="560.0"/>\n'
            "      </bpmndi:BPMNEdge>"
        )

    return (
        '  <bpmndi:BPMNDiagram id="BPMNDiagram_1" name="Default Collaboration Diagram">\n'
        '    <bpmndi:BPMNPlane bpmnElement="Collaboration_1" id="BPMNPlane_1">\n'
        + "\n".join(shapes + edges_xml)
        + "\n    </bpmndi:BPMNPlane>\n  </bpmndi:BPMNDiagram>"
    )


def build_iflw(spec: dict[str, Any]) -> str:
    """Gera o XML completo do .iflw a partir da spec."""
    b = Builder()
    sender = spec.get("sender", {})
    receiver = spec.get("receiver")
    steps = spec.get("steps") or _default_steps_for_pattern(spec)

    start = b.add_start()
    prev = start
    rr_id: str | None = None

    for step in steps:
        stype = step["type"]
        name = step.get("name", stype)
        if stype in {"correlation_id", "cm_correlation"}:
            nid = b.add_content_modifier(
                name or "Guardar correlation id",
                body=None,
                body_type="",
                properties=[("p_correlationId", "header", "SAP_MessageProcessingLogID")],
            )
        elif stype == "content_modifier":
            headers = [(h["name"], h["value"]) for h in step.get("headers", [])]
            props = [
                (p["name"], p.get("value_type", "constant"), p["value"])
                for p in step.get("properties", [])
            ]
            nid = b.add_content_modifier(
                name,
                body=step.get("body"),
                headers=headers,
                properties=props,
                body_type=step.get("body_type", "expression" if step.get("body") is not None else ""),
            )
        elif stype in {"json_to_xml", "json_to_xml_converter"}:
            nid = b.add_json_to_xml(name or "JSON para XML")
        elif stype == "script":
            nid = b.add_script(name, step["script"])
        elif stype in {"request_reply", "external_call"}:
            nid = b.add_request_reply(name)
            rr_id = nid
        elif stype == "json_response":
            code = str(step.get("http_code", "200"))
            body = step.get("body", "${in.body}")
            nid = b.add_content_modifier(
                name or "Definir resposta",
                body=body,
                headers=[
                    ("Content-Type", "application/json"),
                    ("CamelHttpResponseCode", code),
                ],
            )
        else:
            raise ValueError(f"tipo de passo não suportado: {stype}")
        b.link(prev, nid)
        prev = nid

    end = b.add_end()
    b.link(prev, end)
    _wire_incomings_outgoings(b)

    receiver_name = (receiver or {}).get("name", "Receiver")
    participants = f"""    <bpmn2:participant id="Participant_1" ifl:type="EndpointSender" name="Sender">
      <bpmn2:extensionElements>
{_props([("enableBasicAuthentication", "false"), ("ifl:type", "EndpointSender")])}
      </bpmn2:extensionElements>
    </bpmn2:participant>"""
    if receiver:
        participants += f"""
    <bpmn2:participant id="Participant_2" ifl:type="EndpointRecevier" name="{_esc(receiver_name)}">
      <bpmn2:extensionElements>
{_props([("ifl:type", "EndpointRecevier")])}
      </bpmn2:extensionElements>
    </bpmn2:participant>"""
    participants += """
    <bpmn2:participant id="Participant_Process_1" ifl:type="IntegrationProcess" name="Integration Process" processRef="Process_1">
      <bpmn2:extensionElements>
        <ifl:property><key>ifl:type</key><value>IntegrationProcess</value></ifl:property>
      </bpmn2:extensionElements>
    </bpmn2:participant>"""

    path_expr = sender.get("url_path", "{{Sender_Path}}")
    mflows = https_sender_message_flow(start, path_expr)
    if receiver and rr_id:
        mflows += "\n" + http_receiver_message_flow(
            rr_id,
            address=receiver["address"],
            query=receiver.get("query", ""),
            method=receiver.get("method", "GET"),
            credential=receiver.get("credential", "{{Externo_Credential}}"),
            timeout=receiver.get("timeout", "{{Request_Timeout}}"),
            auth_method=receiver.get("auth", "Basic"),
            send_body=receiver.get("send_body", False),
        )

    process_body = "\n".join(n.xml for n in b.nodes)
    process_body += "\n" + b.exception_subprocess_xml()
    process_body += "\n" + "\n".join(_sequence_flow_xml(e) for e in b.edges)

    diagram = _diagram(b, has_receiver=bool(receiver))

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn2:definitions xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:ifl="http:///com.sap.ifl.model/Ifl.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="Definitions_1">
  <bpmn2:collaboration id="Collaboration_1" name="Default Collaboration">
    <bpmn2:extensionElements>
{_props([
    ("namespaceMapping", ""),
    ("allowedHeaderList", ""),
    ("httpSessionHandling", "None"),
    ("ServerTrace", "false"),
    ("returnExceptionToSender", "false"),
    ("log", "All events"),
    ("componentVersion", "1.1"),
    ("cmdVariantUri", "ctype::IFlowVariant/cname::IFlowConfiguration/version::1.1.17"),
])}
    </bpmn2:extensionElements>
{participants}
{mflows}
  </bpmn2:collaboration>
  <bpmn2:process id="Process_1" name="Integration Process">
    <bpmn2:extensionElements>
{_props([
    ("transactionTimeout", "30"),
    ("componentVersion", "1.2"),
    ("cmdVariantUri", "ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.1"),
    ("transactionalHandling", "Not Required"),
])}
    </bpmn2:extensionElements>
{process_body}
  </bpmn2:process>
{diagram}
</bpmn2:definitions>
"""


def _default_steps_for_pattern(spec: dict[str, Any]) -> list[dict[str, Any]]:
    pattern = (spec.get("pattern") or "get_http_external").lower()
    required = spec.get("required_params") or []
    if pattern in {"get_http_external", "a", "pattern_a"}:
        steps: list[dict[str, Any]] = [
            {"type": "correlation_id", "name": "Guardar correlation id"},
        ]
        if required:
            steps.append(
                {
                    "type": "content_modifier",
                    "name": "Definir parâmetros obrigatórios",
                    "properties": [
                        {
                            "name": "p_requiredParams",
                            "value_type": "constant",
                            "value": "{{Required_Params}}",
                        }
                    ],
                }
            )
        steps.extend(
            [
                {
                    "type": "script",
                    "name": "Ler parâmetros da query",
                    "script": "ReadQueryParams.groovy",
                },
                {
                    "type": "content_modifier",
                    "name": "Montar request para API",
                    "headers": [{"name": "Accept", "value": "application/json"}],
                },
                {"type": "request_reply", "name": "Consultar API externa"},
                {"type": "json_response", "name": "Definir resposta", "http_code": "200"},
            ]
        )
        return steps
    raise ValueError(
        f"pattern desconhecido '{pattern}'. Use get_http_external ou liste steps[] explicitamente."
    )


def write_parameters(spec: dict[str, Any]) -> tuple[str, str]:
    """Retorna (parameters.prop, parameters.propdef)."""
    params = list(spec.get("parameters") or [])
    # defaults para pattern A
    if not params and (spec.get("pattern") or "get_http_external").lower() in {
        "get_http_external",
        "a",
        "pattern_a",
    }:
        sender = spec.get("sender", {})
        receiver = spec.get("receiver", {})
        required = spec.get("required_params") or []
        params = [
            {
                "id": "Sender_Path",
                "type": "xsd:string",
                "value": sender.get("path_default", "/api"),
                "description": "Caminho do endpoint HTTPS do iFlow (apos /http)",
            },
            {
                "id": "Required_Params",
                "type": "xsd:string",
                "value": ",".join(required),
                "description": "Parametros de query obrigatorios, separados por virgula",
            },
            {
                "id": "Externo_URL",
                "type": "xsd:string",
                "value": receiver.get("url_default", "https://api.exemplo.com/v1"),
                "description": "URL base da API externa",
            },
            {
                "id": "Request_Timeout",
                "type": "xsd:integer",
                "value": str(receiver.get("timeout_default", "60000")),
                "description": "Timeout da chamada em milissegundos",
            },
        ]
        if (receiver.get("auth") or "Basic") != "None":
            params.insert(
                3,
                {
                    "id": "Externo_Credential",
                    "type": "xsd:string",
                    "value": receiver.get("credential_default", "CRED_API_EXEMPLO"),
                    "description": "Nome da credencial User Credentials",
                },
            )

    prop_lines = ["# generated by generate_iflow.py"]
    propdef_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        "<parameters>",
        "  <param_references/>",
    ]
    for p in params:
        pid = p["id"]
        ptype = p.get("type", "xsd:string")
        if not ptype.startswith("xsd:"):
            ptype = f"xsd:{ptype}"
        value = str(p.get("value", ""))
        desc = p.get("description", "")
        # parameters.prop: escape : and =
        prop_val = value.replace(":", "\\:")
        prop_lines.append(f"{pid}={prop_val}")
        propdef_parts.append(
            f'  <param id="{_esc(pid)}" isRequired="true" allowedValues="" '
            f'description="{_esc(desc)}" isHidden="false">\n'
            f"    <type>{_esc(ptype)}</type>\n"
            f"    <value>{_esc(value)}</value>\n"
            f"  </param>"
        )
    propdef_parts.append("</parameters>")
    return "\n".join(prop_lines) + "\n", "\n".join(propdef_parts) + "\n"
