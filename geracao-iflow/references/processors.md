# Catálogo de processors nativos

Ordem de preferência ao desenhar um passo:

1. Content Modifier, Router, Filter, JSON to XML, XML to JSON, Request Reply, Send, Process Call.
2. Message Mapping (esquemas conhecidos dos dois lados) ou XSLT (transformação estrutural livre).
3. Splitter, Gather, Content Enricher, Looping Process Call, Data Store, Write Variables.
4. Groovy Script, somente com motivo escrito (`groovy.md`).

Os valores de `componentVersion`/`cmdVariantUri` abaixo são os de tenants 6.5x em diante. O
Integration Suite aceita versões anteriores à do tenant e oferece "upgrade" no designer; não
aceita versões que ainda não existem. Em dúvida, usar a versão indicada aqui ou confirmar no
`help.sap.com` para a versão informada pelo usuário.

Todo passo dentro de `bpmn2:process` segue este formato:

```xml
<bpmn2:callActivity id="CallActivity_n" name="O que o passo faz">
  <bpmn2:extensionElements>
    ... propriedades específicas ...
    <ifl:property><key>componentVersion</key><value>x.y</value></ifl:property>
    <ifl:property><key>activityType</key><value>Tipo</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::Tipo/version::x.y.z</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:incoming>SequenceFlow_a</bpmn2:incoming>
  <bpmn2:outgoing>SequenceFlow_b</bpmn2:outgoing>
</bpmn2:callActivity>
```

## Content Modifier (`Enricher`)

Define headers, exchange properties e body. Cobre: copiar header para property, montar JSON/XML
simples com `${...}`, definir `Content-Type`, `CamelHttpResponseCode`, guardar valores para uso
posterior. É o passo mais usado e substitui a maioria dos Groovy "de cola".

```xml
<bpmn2:callActivity id="CallActivity_2" name="Montar request para API">
  <bpmn2:extensionElements>
    <ifl:property><key>bodyType</key><value>expression</value></ifl:property>
    <ifl:property><key>bodyContent</key><value>{&quot;customerId&quot;:&quot;${property.qp_customerId}&quot;,&quot;from&quot;:&quot;${property.qp_from}&quot;}</value></ifl:property>
    <ifl:property><key>wrapContent</key><value>{&quot;customerId&quot;:&quot;${property.qp_customerId}&quot;,&quot;from&quot;:&quot;${property.qp_from}&quot;}</value></ifl:property>
    <ifl:property><key>headerTable</key><value>&lt;row&gt;&lt;cell id='Action'&gt;Create&lt;/cell&gt;&lt;cell id='Type'&gt;constant&lt;/cell&gt;&lt;cell id='Value'&gt;application/json&lt;/cell&gt;&lt;cell id='Default'&gt;&lt;/cell&gt;&lt;cell id='Name'&gt;Content-Type&lt;/cell&gt;&lt;cell id='Datatype'&gt;&lt;/cell&gt;&lt;/row&gt;</value></ifl:property>
    <ifl:property><key>propertyTable</key><value>&lt;row&gt;&lt;cell id='Action'&gt;Create&lt;/cell&gt;&lt;cell id='Type'&gt;header&lt;/cell&gt;&lt;cell id='Value'&gt;SAP_MessageProcessingLogID&lt;/cell&gt;&lt;cell id='Default'&gt;&lt;/cell&gt;&lt;cell id='Name'&gt;p_correlationId&lt;/cell&gt;&lt;cell id='Datatype'&gt;java.lang.String&lt;/cell&gt;&lt;/row&gt;</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.5</value></ifl:property>
    <ifl:property><key>activityType</key><value>Enricher</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::Enricher/version::1.5.0</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:incoming>SequenceFlow_2</bpmn2:incoming>
  <bpmn2:outgoing>SequenceFlow_3</bpmn2:outgoing>
</bpmn2:callActivity>
```

Regras das tabelas (`headerTable` e `propertyTable`): o valor é XML escapado dentro do `value`.
Uma `<row>` por linha, células na ordem `Action`, `Type`, `Value`, `Default`, `Name`, `Datatype`.

| Célula | Valores |
|---|---|
| `Action` | `Create`, `Delete` |
| `Type` | `constant`, `header`, `property`, `expression` (Camel Simple), `xpath`, `number range`, `local variable`, `global variable` |
| `Value` | O valor, nome do header/property de origem, expressão ou XPath. Pode conter `{{Param}}` quando `Type` é `constant`. |
| `Default` | Valor padrão quando a origem não existe (opcional). |
| `Name` | Nome do header/property criado. |
| `Datatype` | Ver regra abaixo. Nunca deixar vazio em `expression` na `propertyTable`. |

**Datatype na `propertyTable` (Exchange Property):**

| Type (Source Type) | Datatype obrigatório |
|---|---|
| `expression` | **Sempre** `java.lang.String` — inclusive `p_bodyOriginal` = `${in.body}` |
| `constant` | `java.lang.String` quando a property guarda texto |
| `header` | `java.lang.String` quando a property guarda texto (ex.: `p_correlationId` ← `SAP_MessageProcessingLogID`) |
| `property` | `java.lang.String` quando copia/guarda texto |
| `xpath` | `java.lang.String` se o valor for texto; `org.w3c.dom.NodeList` (ou outro tipo DOM) se for nó/lista — **não** forçar String em todo XPath |
| `number range`, `local variable`, `global variable` | Conforme o tipo do valor; não usar String às cegas |

Sem `java.lang.String` em Type `expression` (em especial `${in.body}`), o runtime pode materializar a property como stream/`SAXSource`. Reescrever essa property no body e chamar JSON to XML / Router XPath costuma falhar com `InvalidXPathException` + `SAXParseException`. Na `headerTable`, Datatype vazio em headers HTTP costuma ser aceitável; a regra rígida é da **propertyTable**.

`bodyType`: `expression` para o body da resposta (JSON ou `${in.body}`, `${property...}`,
`${header...}`) e `constant` para texto literal sem expressão. O texto vai nas duas propriedades,
com o mesmo valor: `bodyContent` e `wrapContent`. A aba Message Body do designer lê as duas;
deixar `wrapContent` vazio faz a aba aparecer vazia e o runtime devolver body vazio, mesmo com
`bodyContent` preenchido. Aspas do JSON vão escapadas (`&quot;`) dentro do `<value>`.

Passo que só cria header ou property deixa `bodyType` vazio e não declara `bodyContent` nem
`wrapContent`. `bodyType` `expression` com body vazio apaga o payload.

Content Modifier que informa a resposta ao requisitante (nome `Responder…` ou `Montar resposta…`,
ou que define `CamelHttpResponseCode`) sempre tem Type `expression` e Body preenchido. Header
`Content-Type` / código HTTP sem body não é resposta.

Usos típicos:

- **Correlation id do MPL**: no primeiro Content Modifier, property `p_correlationId`, `Type`
  `header`, `Value` `SAP_MessageProcessingLogID`. Header de saída com esse valor só se o
  contrato do receiver pedir.
- **Guardar entrada**: `property` `p_bodyOriginal`, Type `expression`, Value `${in.body}`,
  Datatype **`java.lang.String`**. Sem esse Datatype a property não fica como texto e quebra
  JSON to XML / Groovy / reescrita do body. Não gravar o body em anexo do MPL nem Data Store.
- **Código HTTP de resposta**: header `CamelHttpResponseCode` constante `201`.
- **Resposta de erro (Exception Subprocess)**: um único Content Modifier depois do Groovy
  `GravarResponseErro.groovy`. Type `expression`. `bodyContent` e `wrapContent` com o mesmo texto
  `{"message":"${property.responseErro}"}`. Headers `Content-Type`=`application/json` e
  `CamelHttpResponseCode`=`400`. Sem Router de cenários nesse subprocesso. O Groovy só grava a
  property; este passo monta o JSON.
- **Valor externalizado**: header `apikey` constante `{{API_Key_Header}}`.

## Router (`ExclusiveGateway`)

```xml
<bpmn2:exclusiveGateway default="SequenceFlow_9" id="ExclusiveGateway_1" name="Qual método?">
  <bpmn2:extensionElements>
    <ifl:property><key>throwException</key><value>false</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
    <ifl:property><key>activityType</key><value>ExclusiveGateway</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ExclusiveGateway/version::1.1.1</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:incoming>SequenceFlow_3</bpmn2:incoming>
  <bpmn2:outgoing>SequenceFlow_7</bpmn2:outgoing>
  <bpmn2:outgoing>SequenceFlow_9</bpmn2:outgoing>
</bpmn2:exclusiveGateway>
```

Condições ficam nos `sequenceFlow` de saída (`iflw-xml.md`). A rota `default` não tem condição.
`throwException=true` faz o Router lançar erro quando nenhuma rota casa e não há default.

Expressões úteis (NonXML, [Define Router](https://help.sap.com/docs/cloud-integration/sap-cloud-integration/define-router)):
`${header.CamelHttpMethod} = 'POST'`, `${property.p_total} > 100`,
`${header.SenderId} = '1' and ${header.ReceiverId} = '2'`,
`${header.SenderId} = '1' or ${header.ReceiverId} = '2'`.
Operadores lógicos são as palavras `and` e `or`. `&&` e `||` quebram com
`Token '&&' not supported... Expected tokens: [and, or]`.
O valor entre aspas é um token: sem espaço e sem `|`. Texto com espaço: gravar em property e comparar
`${property.a} contains ${property.b}`.

## Filter (`Filter`)

Reduz o body a um nó/lista via XPath. Útil para tirar o envelope SOAP da resposta antes de
converter para JSON.

```xml
<bpmn2:callActivity id="CallActivity_6" name="Extrair corpo da resposta SOAP">
  <bpmn2:extensionElements>
    <ifl:property><key>xpathType</key><value>Node</value></ifl:property>
    <ifl:property><key>xpath</key><value>//*[local-name()='Body']/*[1]</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
    <ifl:property><key>activityType</key><value>Filter</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::Filter/version::1.1.1</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:callActivity>
```

`xpathType`: `Node`, `Nodelist`, `String`, `Integer`, `Boolean`.

## JSON to XML (`JsonToXmlConverter`)

Obrigatório antes de Message Mapping/XSLT quando a entrada é JSON. Definir sempre um root
element, porque JSON não tem raiz.

Consultar o Help [Define JSON to XML Converter](https://help.sap.com/docs/cloud-integration/sap-cloud-integration/define-json-to-xml-converter) e alinhar as chaves ao export do designer do tenant. No CI 6.84 o passo que converte exporta `additionalRootElementName=root`, `useNamespaces=true` e `addXMLRootElement=true`. A chave antiga `useNamespaceMapping` não substitui `useNamespaces`: o body continua JSON e o XPath seguinte quebra com `Content is not allowed in prolog` / `InvalidXPathException`.

```xml
<bpmn2:callActivity id="CallActivity_3" name="JSON para XML">
  <bpmn2:extensionElements>
    <ifl:property><key>additionalRootElementName</key><value>root</value></ifl:property>
    <ifl:property><key>additionalRootElementNamespace</key><value></value></ifl:property>
    <ifl:property><key>jsonNamespaceMapping</key><value></value></ifl:property>
    <ifl:property><key>useNamespaces</key><value>true</value></ifl:property>
    <ifl:property><key>jsonNamespaceSeparator</key><value>:</value></ifl:property>
    <ifl:property><key>addXMLRootElement</key><value>true</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
    <ifl:property><key>activityType</key><value>JsonToXmlConverter</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::JsonToXmlConverter/version::1.1.2</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:callActivity>
```

O XSD de origem do mapping é derivado da saída deste passo: raiz `root`, arrays JSON viram
elementos repetidos com o nome da chave (às vezes um wrapper com o mesmo nome,
`_PurchaseOrderItem/_PurchaseOrderItem`). Nome com underscore é XML válido. Números e booleanos
viram texto. XPath de item deve aceitar as duas formas:
`(_PurchaseOrderItem|_PurchaseOrderItem/_PurchaseOrderItem)[...]`.

O body do sender HTTPS já chega em JSON. Não inserir um Content Modifier só para reescrever o
body antes deste conversor. O conversor fica no processo principal (não num Local Integration
Process). Um CM anterior pode só gravar properties (`p_bodyOriginal` Type `expression`,
Datatype `java.lang.String`) e deve deixar o Message Body intacto.

Para validar campos, o passo seguinte é um Content Modifier com Source Type `xpath` e Datatype
`java.lang.String` em cada property (Value = XPath, ex. `normalize-space(/root/PurchaseOrderType)`).
O Router é NonXML e compara `${property.PurchaseOrderType} != '' and ${property.CompanyCode} != ''`
(palavra `and`/`or`; nunca `&&`/`||`). Não colocar
`boolean(/root[string-length(...)])` no Router: o Camel avalia isso no body e quebra com
`InvalidXPathException` + `SAXParseException`. Array JSON vira elemento repetido; o XPath do
item aceita também o wrapper `/root/_PurchaseOrderItem/_PurchaseOrderItem/...`.
`Content is not allowed in prolog` nesse XPath significa que o conversor não gerou XML:
conferir `useNamespaces=true` e raiz `root`.

## XML to JSON (`XmlToJsonConverter`)

```xml
<bpmn2:callActivity id="CallActivity_7" name="XML para JSON">
  <bpmn2:extensionElements>
    <ifl:property><key>suppressJsonRoot</key><value>true</value></ifl:property>
    <ifl:property><key>jsonOutputEncoding</key><value>UTF-8</value></ifl:property>
    <ifl:property><key>useNamespaceMapping</key><value>false</value></ifl:property>
    <ifl:property><key>jsonNamespaceMapping</key><value></value></ifl:property>
    <ifl:property><key>jsonNamespaceSeparator</key><value>:</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
    <ifl:property><key>activityType</key><value>XmlToJsonConverter</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::XmlToJsonConverter/version::1.1.2</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:callActivity>
```

Namespaces no XML viram prefixo na chave JSON; se a resposta SOAP tiver namespaces, passar antes
por um XSLT que os remova ou ativar `useNamespaceMapping` com o mapeamento. A opção de converter
elementos específicos em array é configurada no designer (campo *JSON Array*); avisar o
desenvolvedor quando a resposta tiver listas com um único item.

## Message Mapping (`Mapping`)

Transformação estrutural entre dois esquemas: XSD/WSDL/EDMX de origem à esquerda, destino à
direita. Padrão para entrar em API standard SAP: esquerda = XSD gerado do JSON de entrada, direita
= WSDL (SOAP) ou EDMX (OData) do serviço SAP.

```xml
<bpmn2:callActivity id="CallActivity_4" name="Mapear Pedido para SAP">
  <bpmn2:extensionElements>
    <ifl:property><key>mappinguri</key><value>dir://mmap/src/main/resources/mapping/MM_Pedido_para_SAP.mmap</value></ifl:property>
    <ifl:property><key>mappingname</key><value>MM_Pedido_para_SAP</value></ifl:property>
    <ifl:property><key>mappingType</key><value>MessageMapping</value></ifl:property>
    <ifl:property><key>mappingpath</key><value>src/main/resources/mapping/MM_Pedido_para_SAP.mmap</value></ifl:property>
    <ifl:property><key>mappingReference</key><value>static</value></ifl:property>
    <ifl:property><key>mappingSourceValue</key><value></value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.3</value></ifl:property>
    <ifl:property><key>activityType</key><value>Mapping</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::MessageMapping/version::1.3.1</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:callActivity>
```

O `.mmap` é um formato proprietário do editor gráfico. O que o agente entrega:

1. O XSD de origem em `src/main/resources/xsd/` (gerado a partir do exemplo JSON/XML da
   documentação).
2. O WSDL/XSD/EDMX de destino em `wsdl/`, `xsd/` ou `edmx/` (fornecido pelo usuário ou baixado
   do SAP Business Accelerator Hub / do próprio sistema).
3. O passo Message Mapping configurado apontando para `mapping/<Nome>.mmap`.
4. A tabela campo-a-campo (origem → destino, regra) na proposta e na entrega.

Se o agente não conseguir gerar um `.mmap` válido com as ligações, deve dizer isso e orientar:
abrir o passo no designer → *Create* → selecionar origem e destino → ligar os campos conforme a
tabela entregue. Não substituir o mapping por Groovy. Alternativa aceitável quando a regra for
simples e determinística: XSLT, com o `.xsl` completo gerado pelo agente.

## XSLT Mapping (`XSLTMapping`)

```xml
<bpmn2:callActivity id="CallActivity_5" name="Remover namespaces da resposta">
  <bpmn2:extensionElements>
    <ifl:property><key>mappinguri</key><value>dir://xsl/src/main/resources/xsl/RemoveNamespaces.xsl</value></ifl:property>
    <ifl:property><key>mappingname</key><value>RemoveNamespaces</value></ifl:property>
    <ifl:property><key>mappingpath</key><value>src/main/resources/xsl/RemoveNamespaces.xsl</value></ifl:property>
    <ifl:property><key>mappingSourceValue</key><value></value></ifl:property>
    <ifl:property><key>mappingHeaderValue</key><value></value></ifl:property>
    <ifl:property><key>outputFormat</key><value>Bytes</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.2</value></ifl:property>
    <ifl:property><key>activityType</key><value>XSLTMapping</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::XSLTMapping/version::1.2.0</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:callActivity>
```

XSLT 2.0/3.0 (Saxon). Headers e properties ficam disponíveis como `<xsl:param name="nome"/>`.

## Request Reply (`ExternalCall`) e Send (`Send`)

Chamada síncrona (espera resposta) ou assíncrona. O adapter fica no `messageFlow` que sai do
`serviceTask` para o participant receiver (`adapters.md`).

```xml
<bpmn2:serviceTask id="ServiceTask_1" name="Consultar API externa">
  <bpmn2:extensionElements>
    <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
    <ifl:property><key>activityType</key><value>ExternalCall</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ExternalCall/version::1.0.4</value></ifl:property>
  </bpmn2:extensionElements>
  <bpmn2:incoming>SequenceFlow_3</bpmn2:incoming>
  <bpmn2:outgoing>SequenceFlow_4</bpmn2:outgoing>
</bpmn2:serviceTask>
```

Send: `activityType` `Send`, `cmdVariantUri` `ctype::FlowstepVariant/cname::Send/version::1.0.1`.

## Process Call (`ProcessCallElement`)

```xml
<bpmn2:callActivity id="CallActivity_8" name="Chamar bloco de auditoria">
  <bpmn2:extensionElements>
    <ifl:property><key>processId</key><value>Process_2</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.0</value></ifl:property>
    <ifl:property><key>activityType</key><value>ProcessCallElement</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::ProcessCallElement/version::1.0.1</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:callActivity>
```

Looping Process Call: mesmo elemento com `activityType` `LoopingProcessCall`, mais `loopCondition`
(ex.: `${property.p_hasNext} = 'true'`), `expressionType` `NonXML`, `maxIterations`.

## Groovy Script (`Script`)

```xml
<bpmn2:callActivity id="CallActivity_1" name="Ler parâmetros da query">
  <bpmn2:extensionElements>
    <ifl:property><key>scriptFunction</key><value>processData</value></ifl:property>
    <ifl:property><key>scriptBundleId</key><value></value></ifl:property>
    <ifl:property><key>script</key><value>ReadQueryParams.groovy</value></ifl:property>
    <ifl:property><key>subActivityType</key><value>GroovyScript</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
    <ifl:property><key>activityType</key><value>Script</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::FlowstepVariant/cname::GroovyScript/version::1.1.2</value></ifl:property>
  </bpmn2:extensionElements>
  ...
</bpmn2:callActivity>
```

O arquivo fica em `src/main/resources/script/ReadQueryParams.groovy`. **Obrigatório em todo
iFlow HTTPS GET** (query params → `qp_*`). Critérios e template em `groovy.md`; padrão em
`padroes-fluxo.md` Padrão A.

## Outros processors (resumo)

Confirmar propriedades no `help.sap.com` (ou exportando um exemplo do designer) antes de usar.

| Processor | `activityType` | Uso |
|---|---|---|
| General Splitter / Iterating Splitter | `Splitter` | Quebrar lote em mensagens (XPath, linha, token). Combinar com Gather. |
| Gather / Join | `Gather` / `Join` (parallelGateway) | Reagrupar após Splitter ou Multicast. |
| Multicast | `ParallelGateway`/`SequentialMulticast` | Enviar a mesma mensagem a vários receivers. |
| Content Enricher | `PollEnrich`/`Enricher` com `aggregationAlgorithm` | Buscar dado externo e combinar com o body atual. |
| Data Store Write/Get/Select/Delete | `DBstorage` + `operation` | Persistência temporária entre execuções. |
| Write Variables | `WriteVariables` | Guardar valor global/local (ex.: último timestamp). |
| Persist | `Persist` | Guardar snapshot da mensagem. |
| ID Mapping | `IdMapping` | Garantir id único por mensagem de origem. |
| Encoder/Decoder | `Encoder` / `Decoder` | Base64, GZIP, ZIP, MIME. |
| XML Validator | `XmlValidator` | Validar body contra XSD. |
| Timer Start | `StartTimerEvent` (startEvent) | Agendamento. |

## Expressões Camel Simple mais usadas

| Expressão | Significado |
|---|---|
| `${header.CamelHttpMethod}` | GET/POST/... da chamada recebida |
| `${header.CamelHttpQuery}` | Query string crua (`a=1&b=2`) |
| `${header.CamelHttpPath}` | Caminho após o endpoint do iFlow |
| `${header.CamelHttpResponseCode}` | Código da resposta do receiver (após Request Reply) ou a ser devolvido |
| `${property.p_x}` | Exchange property |
| `${in.body}` | Body atual |
| `${property.responseErro}` | Texto da exceção, gravado pelo Groovy do Exception Subprocess |
| `${date:now:yyyy-MM-dd'T'HH:mm:ss}` | Data/hora |
| `${camelId}` / `${exchangeId}` | Ids técnicos |
