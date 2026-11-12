# O arquivo `.iflw`

É BPMN 2.0 XML. Cada elemento carrega as configurações SAP dentro de
`bpmn2:extensionElements` como pares `ifl:property` (`key`/`value`). O designer lê a parte
`bpmndi:BPMNDiagram` para posicionar as formas; sem ela o fluxo abre vazio.

Exemplo completo e validado: `exemplos/IF_Consulta_API_Externa.iflw` (GET com query params →
Groovy de parsing → Content Modifier → Request Reply HTTP → Content Modifier → End, com
Exception Subprocess).

## Esqueleto

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn2:definitions xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL"
                   xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                   xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                   xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                   xmlns:ifl="http:///com.sap.ifl.model/Ifl.xsd"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                   id="Definitions_1">
  <bpmn2:collaboration id="Collaboration_1" name="Default Collaboration">
    <bpmn2:extensionElements> ... propriedades globais do iFlow ... </bpmn2:extensionElements>
    <bpmn2:participant id="Participant_1" ifl:type="EndpointSender" name="Sender"> ... </bpmn2:participant>
    <bpmn2:participant id="Participant_2" ifl:type="EndpointRecevier" name="Receiver"> ... </bpmn2:participant>
    <bpmn2:participant id="Participant_Process_1" ifl:type="IntegrationProcess" name="Integration Process" processRef="Process_1"/>
    <bpmn2:messageFlow id="MessageFlow_1" name="HTTPS" sourceRef="Participant_1" targetRef="StartEvent_2"> ... adapter sender ... </bpmn2:messageFlow>
    <bpmn2:messageFlow id="MessageFlow_2" name="HTTP"  sourceRef="ServiceTask_1" targetRef="Participant_2"> ... adapter receiver ... </bpmn2:messageFlow>
  </bpmn2:collaboration>

  <bpmn2:process id="Process_1" name="Integration Process">
    <bpmn2:extensionElements> ... </bpmn2:extensionElements>
    <bpmn2:startEvent .../>
    <bpmn2:callActivity .../>       <!-- Content Modifier, Script, Mapping, Converter, Filter... -->
    <bpmn2:serviceTask .../>        <!-- Request Reply, Send, Content Enricher -->
    <bpmn2:exclusiveGateway .../>   <!-- Router -->
    <bpmn2:subProcess .../>         <!-- Exception Subprocess, Local Integration Process -->
    <bpmn2:endEvent .../>
    <bpmn2:sequenceFlow id="SequenceFlow_1" sourceRef="StartEvent_2" targetRef="CallActivity_1"/>
  </bpmn2:process>

  <bpmndi:BPMNDiagram id="BPMNDiagram_1" name="Default Collaboration Diagram">
    <bpmndi:BPMNPlane bpmnElement="Collaboration_1" id="BPMNPlane_1">
      <bpmndi:BPMNShape bpmnElement="Participant_1" id="BPMNShape_Participant_1"><dc:Bounds height="140.0" width="100.0" x="40.0" y="100.0"/></bpmndi:BPMNShape>
      ... uma BPMNShape por participant, evento, atividade, gateway, subprocesso ...
      <bpmndi:BPMNEdge bpmnElement="SequenceFlow_1" id="BPMNEdge_SequenceFlow_1" sourceElement="BPMNShape_StartEvent_2" targetElement="BPMNShape_CallActivity_1">
        <di:waypoint x="..." xsi:type="dc:Point" y="..."/>
        <di:waypoint x="..." xsi:type="dc:Point" y="..."/>
      </bpmndi:BPMNEdge>
      ... uma BPMNEdge por sequenceFlow e por messageFlow ...
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn2:definitions>
```

Nota: `EndpointRecevier` (com o erro de grafia) é o valor que o designer usa. Não corrigir.

## Convenções de id

| Elemento | Prefixo |
|---|---|
| Participant | `Participant_1`, `Participant_2`, `Participant_Process_1` |
| Process | `Process_1`; locais `Process_2`, ... |
| Start/End | `StartEvent_2`, `EndEvent_2` (o designer começa em 2) |
| Content Modifier, Script, Mapping, Converter, Filter, Splitter... | `CallActivity_n` |
| Request Reply, Send, Content Enricher, Poll Enrich | `ServiceTask_n` |
| Router | `ExclusiveGateway_n`; Gather/Join `ParallelGateway_n` |
| Exception Subprocess / Local Integration Process | `SubProcess_n` |
| Sequence flow | `SequenceFlow_n` |
| Message flow (adapter) | `MessageFlow_n` |
| Shape / Edge | `BPMNShape_<id>` / `BPMNEdge_<id>` |

Ids únicos em todo o arquivo. O `name` é o texto exibido no designer: escrever o que o passo faz
("Montar request para API", "Ler parâmetros da query").

## Propriedades globais (collaboration)

```xml
<bpmn2:extensionElements>
  <ifl:property><key>namespaceMapping</key><value></value></ifl:property>
  <ifl:property><key>allowedHeaderList</key><value></value></ifl:property>
  <ifl:property><key>httpSessionHandling</key><value>None</value></ifl:property>
  <ifl:property><key>ServerTrace</key><value>false</value></ifl:property>
  <ifl:property><key>returnExceptionToSender</key><value>false</value></ifl:property>
  <ifl:property><key>log</key><value>All events</value></ifl:property>
  <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
  <ifl:property><key>cmdVariantUri</key><value>ctype::IFlowVariant/cname::IFlowConfiguration/version::1.1.17</value></ifl:property>
</bpmn2:extensionElements>
```

- `allowedHeaderList`: headers de entrada que podem atravessar o fluxo e ir ao receiver, separados
  por `|` (ex.: `Authorization|X-Correlation-Id`). Só listar os necessários.
- `namespaceMapping`: prefixos para XPath no Router/Filter/Content Modifier, formato
  `xmlns:ns0=http://...;xmlns:ns1=...`.
- `returnExceptionToSender`: `false` quando há Exception Subprocess montando a resposta.

## Participants

```xml
<bpmn2:participant id="Participant_1" ifl:type="EndpointSender" name="Sender">
  <bpmn2:extensionElements>
    <ifl:property><key>enableBasicAuthentication</key><value>false</value></ifl:property>
    <ifl:property><key>ifl:type</key><value>EndpointSender</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:participant>
<bpmn2:participant id="Participant_2" ifl:type="EndpointRecevier" name="Receiver">
  <bpmn2:extensionElements>
    <ifl:property><key>ifl:type</key><value>EndpointRecevier</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:participant>
<bpmn2:participant id="Participant_Process_1" ifl:type="IntegrationProcess" name="Integration Process" processRef="Process_1">
  <bpmn2:extensionElements>
    <ifl:property><key>ifl:type</key><value>IntegrationProcess</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:participant>
```

Dar ao receiver o nome do sistema real (`SAP_S4`, `API_Externa`), um participant por sistema.

## Process

```xml
<bpmn2:process id="Process_1" name="Integration Process">
  <bpmn2:extensionElements>
    <ifl:property><key>transactionTimeout</key><value>30</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.2</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowElementVariant/cname::IntegrationProcess/version::1.2.1</value></ifl:property>
    <ifl:property><key>transactionalHandling</key><value>Not Required</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:process>
```

`transactionalHandling`: `Not Required` para fluxos HTTP síncronos; `Required for JMS` /
`Required for JDBC` só quando houver fila/banco.

## Start e End

```xml
<bpmn2:startEvent id="StartEvent_2" name="Start">
  <bpmn2:extensionElements>
    <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::MessageStartEvent/version::1.0.0</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:outgoing>SequenceFlow_1</bpmn2:outgoing>
  <bpmn2:messageEventDefinition/>
</bpmn2:startEvent>

<bpmn2:endEvent id="EndEvent_2" name="End">
  <bpmn2:extensionElements>
    <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::MessageEndEvent/version::1.0.0</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:incoming>SequenceFlow_5</bpmn2:incoming>
  <bpmn2:messageEventDefinition/>
</bpmn2:endEvent>
```

Todo nó de processo declara `bpmn2:incoming`/`bpmn2:outgoing` com os ids dos sequence flows que
chegam/saem. O validador confere a consistência com `sourceRef`/`targetRef`.

## Sequence flow

```xml
<bpmn2:sequenceFlow id="SequenceFlow_1" sourceRef="StartEvent_2" targetRef="CallActivity_1" isImmediate="true"/>
```

Com condição (saída de Router):

```xml
<bpmn2:sequenceFlow id="SequenceFlow_7" name="É GET" sourceRef="ExclusiveGateway_1" targetRef="CallActivity_3" isImmediate="true">
  <bpmn2:extensionElements>
    <ifl:property><key>expressionType</key><value>NonXML</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:conditionExpression id="FormalExpression_7" xsi:type="bpmn2:tFormalExpression">${header.CamelHttpMethod} = 'GET'</bpmn2:conditionExpression>
</bpmn2:sequenceFlow>
```

`expressionType`: `NonXML` para Camel Simple (`${header.x}`, `${property.y}`), `XML` para XPath
(`/Order/Type = 'A'`). A rota default é indicada em `default="SequenceFlow_n"` no gateway e não
tem condição.

Condição NonXML ([Define Router](https://help.sap.com/docs/cloud-integration/sap-cloud-integration/define-router)):
operadores lógicos são as palavras `and` e `or`.
`${property.PurchaseOrderType} != '' and ${property.CompanyCode} != ''` passa.
`&&` e `||` caem em `Token '&&' not supported... Expected tokens: [and, or]`.
Valor entre aspas sem espaço e sem `|`.
`${exception.message} regex '.*(A|B|malformed JSON).*'` cai em
`Invalid format of condition expression value`. Texto com espaço vai para uma property e a
condição fica `${property.a} contains ${property.b}`.

## Exception Subprocess

```xml
<bpmn2:subProcess id="SubProcess_1" name="Exception Subprocess" triggeredByEvent="true">
  <bpmn2:extensionElements>
    <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
    <ifl:property><key>activityType</key><value>ErrorEventSubProcessTemplate</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.0.0</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:startEvent id="StartEvent_3" name="Error Start">
    <bpmn2:extensionElements>
      <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
      <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ErrorStartEvent/version::1.0.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:outgoing>SequenceFlow_20</bpmn2:outgoing>
    <bpmn2:errorEventDefinition/>
  </bpmn2:startEvent>
  <!-- Groovy "Gravar responseErro" → Content Modifier "Montar resposta de erro" (ver processors.md) -->
  <bpmn2:endEvent id="EndEvent_3" name="End">
    <bpmn2:extensionElements>
      <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
      <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::MessageEndEvent/version::1.0.0</value></ifl:property>
    </bpmn2:extensionElements>
    <bpmn2:incoming>SequenceFlow_22</bpmn2:incoming>
    <bpmn2:messageEventDefinition/>
  </bpmn2:endEvent>
  <bpmn2:sequenceFlow id="SequenceFlow_20" sourceRef="StartEvent_3" targetRef="CallActivity_9"/>
  <bpmn2:sequenceFlow id="SequenceFlow_21" sourceRef="CallActivity_9" targetRef="CallActivity_10"/>
  <bpmn2:sequenceFlow id="SequenceFlow_22" sourceRef="CallActivity_10" targetRef="EndEvent_3"/>
</bpmn2:subProcess>
```

Cadeia única, sem Router: Error Start → Groovy `GravarResponseErro.groovy` (property `responseErro`)
→ Content Modifier (body `{"message":"${property.responseErro}"}`, `Content-Type` `application/json`,
`CamelHttpResponseCode` `400`) → um End Message. O End Message devolve essa resposta ao chamador.

`triggeredByEvent="true"`, Error Start e **um único** fim (End Message). Dois fins no mesmo
Exception Subprocess geram `Exception Subprocess should start with an Error Start Event and end
with either End Message or Error End`. Não modelar cenários de exceção (JSON inválido, timeout,
5xx) como rotas dentro do subprocesso: o Groovy pega qualquer erro.

End Event (`cname::EndEvent`), End Message (`MessageEndEvent`) e Error End (`ErrorEndEvent`) usam
`version::1.0.0` e `componentVersion` `1.0`. Versão 1.1 desses componentes é recusada:
`component EndEvent with version 1.1 is not supported in Cloud Integration profile.`

## Local Integration Process

É um `bpmn2:process` separado (`processType` `directCall`,
`cmdVariantUri` `ctype::FlowElementVariant/cname::LocalIntegrationProcess/version::1.1.3`),
com participant `processRef` apontando para ele. Start `StartEvent` (não Message Start) e um
End Message na versão 1.0 (`MessageEndEvent/version::1.0.0`), não End Event 1.1. É chamado por
Process Call (`processId` = id desse process). Usar para bloco repetido e para o corpo de um
Looping Process Call. Não criar processo local só para afastar o JSON to XML do sender
HTTPS, nem só para esconder um script. A validação de POST JSON fica no processo principal:
JSON to XML (`additionalRootElementName=root`, `useNamespaces=true`, `addXMLRootElement=true`;
não usar `useNamespaceMapping` no lugar de `useNamespaces`), Content Modifier com properties
Source Type `xpath` em `/root/...` (Datatype `java.lang.String`)
e Router NonXML `${property.Campo}`. O XPath não vai no Router.
`Content is not allowed in prolog` no XPath depois do conversor significa que o body ainda é JSON.
Na `propertyTable`, Type `expression` (ex.: `p_bodyOriginal`) tem Datatype `java.lang.String`;
Type `header`/`property`/`constant` de texto e xpath de texto idem.
`InvalidXPathException` + `SAXParseException` no Router significa condição XPath no gateway.

## Diagrama

Tamanhos usados pelo designer:

| Elemento | width × height |
|---|---|
| Participant sender/receiver | 100 × 140 |
| Participant do processo | largura suficiente para os passos; altura ≥ 300 |
| Start/End | 32 × 32 |
| callActivity / serviceTask | 100 × 60 |
| Gateway | 40 × 40 |
| Exception Subprocess | largura dos passos internos + 60; altura 180 |

Layout simples que funciona: processo em `x=240,y=60`; passos em sequência a cada 150 px na
mesma linha `y=142` (atividades) e `y=156` (eventos, para centralizar). Waypoints: saída no meio
da borda direita do source, entrada no meio da borda esquerda do target. Message flows: sender
para o Start (vertical) e serviceTask para o receiver (vertical para baixo).

O designer reposiciona ao salvar; o importante é cada elemento ter uma shape e cada flow uma edge.

## Checklist antes de validar

- [ ] Um `participant` por sistema, `processRef` apontando para o `process`.
- [ ] Todo `messageFlow` referencia um Start (sender) ou um `serviceTask` (receiver).
- [ ] Todo passo tem `activityType`, `componentVersion`, `cmdVariantUri`.
- [ ] `incoming`/`outgoing` batem com `sourceRef`/`targetRef`.
- [ ] Todo script/mapping/xsl referenciado existe em `src/main/resources/...`.
- [ ] Nenhuma URL, host, credencial ou timeout fixo em adapter: sempre `{{Param}}`.
- [ ] Todo `{{Param}}` declarado em `parameters.propdef` e `parameters.prop`.
- [ ] Exception Subprocess presente em fluxo síncrono: Error Start → Groovy `responseErro` → Content Modifier 400 JSON → um End Message 1.0, sem Router.
- [ ] Nenhum End Event / End Message / Error End em versão 1.1.
- [ ] Shape para cada elemento, edge para cada flow.
