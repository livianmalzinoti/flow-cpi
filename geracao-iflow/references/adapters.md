# Adapters

Adapters são `bpmn2:messageFlow` dentro da `collaboration`:

- **Sender**: `sourceRef` = participant sender, `targetRef` = `StartEvent` do processo.
- **Receiver**: `sourceRef` = `serviceTask` (Request Reply/Send), `targetRef` = participant receiver.

Toda propriedade que muda entre DEV/QAS/PRD é `{{Param}}` (`externalizacao.md`). O validador
rejeita `http://`/`https://` fixo e `credentialName` fixo em adapter receiver.

Versões (`componentVersion`, `ComponentSWCVId`, `cmdVariantUri`) variam com a versão do tenant;
as abaixo funcionam em tenants 6.5x em diante. Para usar campos novos de uma versão específica,
confirmar no `help.sap.com` (*Configure the <X> Adapter*).

## HTTPS sender

Expõe o iFlow em `https://<tenant>.it-cpi.../http/<urlPath>`.

```xml
<bpmn2:messageFlow id="MessageFlow_1" name="HTTPS" sourceRef="Participant_1" targetRef="StartEvent_2">
  <bpmn2:extensionElements>
    <ifl:property><key>ComponentType</key><value>HTTPS</value></ifl:property>
    <ifl:property><key>Name</key><value>HTTPS</value></ifl:property>
    <ifl:property><key>ComponentNS</key><value>sap</value></ifl:property>
    <ifl:property><key>ComponentSWCVName</key><value>external</value></ifl:property>
    <ifl:property><key>ComponentSWCVId</key><value>1.5.1</value></ifl:property>
    <ifl:property><key>TransportProtocol</key><value>HTTPS</value></ifl:property>
    <ifl:property><key>TransportProtocolVersion</key><value>1.5.1</value></ifl:property>
    <ifl:property><key>MessageProtocol</key><value>None</value></ifl:property>
    <ifl:property><key>MessageProtocolVersion</key><value>1.5.1</value></ifl:property>
    <ifl:property><key>direction</key><value>Sender</value></ifl:property>
    <ifl:property><key>system</key><value>Sender</value></ifl:property>
    <ifl:property><key>urlPath</key><value>{{Sender_Path}}</value></ifl:property>
    <ifl:property><key>senderAuthType</key><value>RoleBased</value></ifl:property>
    <ifl:property><key>userRole</key><value>ESBMessaging.send</value></ifl:property>
    <ifl:property><key>xsrfProtection</key><value>false</value></ifl:property>
    <ifl:property><key>maximumBodySize</key><value>40</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.5</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.5.1</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:messageFlow>
```

- `urlPath` começa com `/`. Externalizar permite trocar o caminho sem editar o fluxo.
- `senderAuthType`: `RoleBased` (OAuth2 client credentials ou Basic com usuário técnico) ou
  `ClientCertificate`.
- `xsrfProtection` `false` para APIs chamadas por sistemas.
- Headers que chegam: `CamelHttpMethod`, `CamelHttpQuery`, `CamelHttpPath`, `CamelHttpUri`,
  `Content-Type`, mais os headers HTTP da requisição. Para repassá-los ao receiver é preciso
  listá-los em `allowedHeaderList` (collaboration).
- **GET não tem body** (não desenhar GET com JSON body). Os dados de consulta vêm em
  `CamelHttpQuery` e são lidos **sempre** com `ReadQueryParams.groovy` (ver `groovy.md` e
  Padrão A em `padroes-fluxo.md`).
- O `urlPath` do sender é **exato** (ex.: `/cep`). Chamadas como `/cep/01001000` em geral **não
  batem** neste iFlow. Por isso o padrão é `GET /cep?cep=01001000`, não path extra.

## HTTP receiver

Chamada REST a API externa ou interna.

```xml
<bpmn2:messageFlow id="MessageFlow_2" name="HTTP" sourceRef="ServiceTask_1" targetRef="Participant_2">
  <bpmn2:extensionElements>
    <ifl:property><key>ComponentType</key><value>HTTP</value></ifl:property>
    <ifl:property><key>Name</key><value>HTTP</value></ifl:property>
    <ifl:property><key>ComponentNS</key><value>sap</value></ifl:property>
    <ifl:property><key>ComponentSWCVName</key><value>external</value></ifl:property>
    <ifl:property><key>ComponentSWCVId</key><value>1.14.0</value></ifl:property>
    <ifl:property><key>TransportProtocol</key><value>HTTP</value></ifl:property>
    <ifl:property><key>TransportProtocolVersion</key><value>1.14.0</value></ifl:property>
    <ifl:property><key>MessageProtocol</key><value>None</value></ifl:property>
    <ifl:property><key>MessageProtocolVersion</key><value>1.14.0</value></ifl:property>
    <ifl:property><key>direction</key><value>Receiver</value></ifl:property>
    <ifl:property><key>system</key><value>Receiver</value></ifl:property>
    <ifl:property><key>httpAddressWithoutQuery</key><value>{{Receiver_URL}}</value></ifl:property>
    <ifl:property><key>httpAddressQuery</key><value></value></ifl:property>
    <ifl:property><key>httpMethod</key><value>GET</value></ifl:property>
    <ifl:property><key>httpShouldSendBody</key><value>false</value></ifl:property>
    <ifl:property><key>httpRequestTimeout</key><value>{{Request_Timeout}}</value></ifl:property>
    <ifl:property><key>authenticationMethod</key><value>Basic</value></ifl:property>
    <ifl:property><key>credentialName</key><value>{{Receiver_Credential}}</value></ifl:property>
    <ifl:property><key>proxyType</key><value>default</value></ifl:property>
    <ifl:property><key>throwExceptionOnFailure</key><value>true</value></ifl:property>
    <ifl:property><key>httpErrorResponseCodes</key><value></value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.14</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.14.0</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:messageFlow>
```

- `httpAddressWithoutQuery`: URL sem query string. Pode combinar parâmetro e property:
  `{{Receiver_URL}}/customers/${property.qp_customerId}`.
- `httpAddressQuery`: query string; aceita `${property.x}`. Para repassar a query recebida inteira:
  `${header.CamelHttpQuery}`.
- `httpMethod`: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, ou `Dynamic` (lê `CamelHttpMethod`).
- `httpShouldSendBody`: `true` em POST/PUT/PATCH.
- `authenticationMethod`: `None`, `Basic`, `ClientCertificate`, `OAuth2ClientCredentials`,
  `OAuth2SAMLBearerAssertion`, `OAuth2AuthorizationCode`. O `credentialName` é o nome do artefato
  em *Security Material*; o valor da senha nunca entra no pacote.
- `proxyType`: `default` (internet) ou `onPremise` (Cloud Connector; aí também `locationId`
  externalizado).
- `throwExceptionOnFailure` `true` para cair no Exception Subprocess em 4xx/5xx.
- Headers de request (ex.: `Content-Type`, `apikey`) são definidos num Content Modifier antes do
  Request Reply. Headers vindos do sender só chegam ao receiver se estiverem em
  `allowedHeaderList`.
- Após a chamada, `CamelHttpResponseCode` traz o código do receiver.

## SOAP receiver (SOAP 1.x) — API standard SAP

Para serviços SOAP de S/4HANA Cloud/on-premise (`_SRV`, `*_In`), SuccessFactors SOAP, etc.

```xml
<bpmn2:messageFlow id="MessageFlow_2" name="SOAP" sourceRef="ServiceTask_1" targetRef="Participant_2">
  <bpmn2:extensionElements>
    <ifl:property><key>ComponentType</key><value>SOAP</value></ifl:property>
    <ifl:property><key>Name</key><value>SOAP</value></ifl:property>
    <ifl:property><key>ComponentNS</key><value>sap</value></ifl:property>
    <ifl:property><key>ComponentSWCVName</key><value>external</value></ifl:property>
    <ifl:property><key>ComponentSWCVId</key><value>1.10.0</value></ifl:property>
    <ifl:property><key>TransportProtocol</key><value>HTTP</value></ifl:property>
    <ifl:property><key>TransportProtocolVersion</key><value>1.10.0</value></ifl:property>
    <ifl:property><key>MessageProtocol</key><value>SOAP 1.x</value></ifl:property>
    <ifl:property><key>MessageProtocolVersion</key><value>1.10.0</value></ifl:property>
    <ifl:property><key>direction</key><value>Receiver</value></ifl:property>
    <ifl:property><key>system</key><value>Receiver</value></ifl:property>
    <ifl:property><key>address</key><value>{{SAP_Endpoint}}</value></ifl:property>
    <ifl:property><key>proxyType</key><value>default</value></ifl:property>
    <ifl:property><key>wsdlURL</key><value>/wsdl/SalesOrderCreateRequest.wsdl</value></ifl:property>
    <ifl:property><key>serviceName</key><value>{http://sap.com/xi/APPL/SE/Global}SalesOrderCreateRequestConfirmation_In</value></ifl:property>
    <ifl:property><key>portName</key><value>{http://sap.com/xi/APPL/SE/Global}HTTP_Port</value></ifl:property>
    <ifl:property><key>authenticationMethod</key><value>Basic</value></ifl:property>
    <ifl:property><key>credentialName</key><value>{{SAP_Credential}}</value></ifl:property>
    <ifl:property><key>requestTimeout</key><value>{{Request_Timeout}}</value></ifl:property>
    <ifl:property><key>allowChunking</key><value>1</value></ifl:property>
    <ifl:property><key>cleanupHeaders</key><value>1</value></ifl:property>
    <ifl:property><key>compressMessage</key><value>false</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.10</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:SOAP/tp::HTTP/mp::SOAP 1.x/direction::Receiver/version::1.10.0</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:messageFlow>
```

- `wsdlURL` aponta para o WSDL dentro do pacote (`/wsdl/<arquivo>.wsdl`), `serviceName` e
  `portName` em formato QName `{namespace}nome` (ler do WSDL).
- O body enviado deve ser o conteúdo do `soap:Body` (o adapter envelopa). Por isso o Message
  Mapping tem como destino a mensagem do WSDL, não o Envelope.
- A resposta volta sem envelope. Para transformar em JSON: XML to JSON direto, ou XSLT para
  remover namespaces antes.

## OData V2 receiver

```xml
<bpmn2:messageFlow id="MessageFlow_2" name="OData" sourceRef="ServiceTask_1" targetRef="Participant_2">
  <bpmn2:extensionElements>
    <ifl:property><key>ComponentType</key><value>HCIOData</value></ifl:property>
    <ifl:property><key>Name</key><value>OData</value></ifl:property>
    <ifl:property><key>ComponentNS</key><value>sap</value></ifl:property>
    <ifl:property><key>ComponentSWCVName</key><value>external</value></ifl:property>
    <ifl:property><key>ComponentSWCVId</key><value>1.25.0</value></ifl:property>
    <ifl:property><key>TransportProtocol</key><value>HTTP</value></ifl:property>
    <ifl:property><key>TransportProtocolVersion</key><value>1.25.0</value></ifl:property>
    <ifl:property><key>MessageProtocol</key><value>OData V2</value></ifl:property>
    <ifl:property><key>MessageProtocolVersion</key><value>1.25.0</value></ifl:property>
    <ifl:property><key>direction</key><value>Receiver</value></ifl:property>
    <ifl:property><key>system</key><value>Receiver</value></ifl:property>
    <ifl:property><key>address</key><value>{{OData_URL}}</value></ifl:property>
    <ifl:property><key>proxyType</key><value>default</value></ifl:property>
    <ifl:property><key>authenticationMethod</key><value>Basic</value></ifl:property>
    <ifl:property><key>credentialName</key><value>{{OData_Credential}}</value></ifl:property>
    <ifl:property><key>operation</key><value>Query(GET)</value></ifl:property>
    <ifl:property><key>resourcePath</key><value>A_BusinessPartner</value></ifl:property>
    <ifl:property><key>queryOptions</key><value>$select=BusinessPartner,BusinessPartnerName&amp;$filter=BusinessPartner eq '${property.qp_id}'</value></ifl:property>
    <ifl:property><key>contentType</key><value>application/atom+xml</value></ifl:property>
    <ifl:property><key>edmxPath</key><value>edmx/API_BUSINESS_PARTNER.edmx</value></ifl:property>
    <ifl:property><key>pageSize</key><value>{{OData_PageSize}}</value></ifl:property>
    <ifl:property><key>enableMPLAttachments</key><value>false</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.25</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:HCIOData/tp::HTTP/mp::OData V2/direction::Receiver/version::1.25.0</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:messageFlow>
```

- `operation`: `Query(GET)`, `Read(GET)`, `Create(POST)`, `Update(PUT)`, `Merge(MERGE)`,
  `Delete(DELETE)`, `Function Import`.
- O `.edmx` e o XSD de request/response normalmente são gerados pelo wizard *Model Operation* do
  designer, que se conecta ao serviço. O agente pode gerar o adapter com `address`, `operation`,
  `resourcePath` e `queryOptions`, incluir o EDMX se o usuário fornecer, e deixar claro na entrega
  que o wizard deve ser rodado uma vez para confirmar o modelo.
- Para `Create(POST)` o body deve ser XML no formato do EDMX (saída de um Message Mapping cujo
  destino é o EDMX).

## ProcessDirect

Comunicação entre iFlows do mesmo tenant, sem sair para a rede.

Receiver:

```xml
<bpmn2:messageFlow id="MessageFlow_3" name="ProcessDirect" sourceRef="ServiceTask_2" targetRef="Participant_3">
  <bpmn2:extensionElements>
    <ifl:property><key>ComponentType</key><value>ProcessDirect</value></ifl:property>
    <ifl:property><key>Name</key><value>ProcessDirect</value></ifl:property>
    <ifl:property><key>ComponentNS</key><value>sap</value></ifl:property>
    <ifl:property><key>ComponentSWCVName</key><value>external</value></ifl:property>
    <ifl:property><key>ComponentSWCVId</key><value>1.1.0</value></ifl:property>
    <ifl:property><key>TransportProtocol</key><value>Not Applicable</value></ifl:property>
    <ifl:property><key>TransportProtocolVersion</key><value>1.1.0</value></ifl:property>
    <ifl:property><key>MessageProtocol</key><value>Not Applicable</value></ifl:property>
    <ifl:property><key>MessageProtocolVersion</key><value>1.1.0</value></ifl:property>
    <ifl:property><key>direction</key><value>Receiver</value></ifl:property>
    <ifl:property><key>system</key><value>Receiver</value></ifl:property>
    <ifl:property><key>address</key><value>{{PD_Auditoria_Address}}</value></ifl:property>
    <ifl:property><key>componentVersion</key><value>1.1</value></ifl:property>
    <ifl:property><key>cmdVariantUri</key><value>ctype::AdapterVariant/cname::sap:ProcessDirect/tp::Not Applicable/mp::Not Applicable/direction::Receiver/version::1.1.0</value></ifl:property>
  </bpmn2:extensionElements>
</bpmn2:messageFlow>
```

Sender: mesmas propriedades com `direction` `Sender`, `system` `Sender`,
`cmdVariantUri ...direction::Sender/version::1.1.0`, `sourceRef` = participant sender,
`targetRef` = `StartEvent`.

Usar ProcessDirect quando a mesma sequência apareceria em mais de um iFlow, ou para separar
responsabilidades (ex.: iFlow de negócio chama iFlow de auditoria). O endereço é externalizado.
Dentro de um único iFlow, a repetição fica em Local Integration Process + Process Call.

## Outros adapters

Confirmar as propriedades no `help.sap.com` antes de gerar: SFTP (`ComponentType` `SFTP`,
`host`, `path`, `credentialName`, `fileName`), Mail, JMS (`QueueName`), AMQP, IDoc, RFC, JDBC,
SuccessFactors (`SuccessFactors`/`SOAP`/`OData V2`), Ariba, Kafka. Todos seguem a mesma forma de
`messageFlow`; mudam as chaves.

`enableMPLAttachments` fica `false`. Anexo de payload no MPL não entra no artefato gerado.

Sender JMS (ou qualquer retry que reentregue) exige chave de idempotência na proposta: id de
negócio ou `p_correlationId`, e o receiver trata a mesma chave como já processada.
`transactionalHandling` `Required for JMS` só nesse caso (`iflw-xml.md`).
