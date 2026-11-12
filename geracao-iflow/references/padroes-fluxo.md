# Padrões de fluxo

Três desenhos que cobrem a maioria dos pedidos. Adaptar nomes de passos e parâmetros ao caso.
Todo padrão síncrono começa com a property `p_correlationId` lida do header
`SAP_MessageProcessingLogID` e termina com Exception Subprocess simples: Error Start → Groovy
`GravarResponseErro.groovy` (property `responseErro`) → Content Modifier HTTP 400 e body
`{"message":"${property.responseErro}"}` → um End Message versão 1.0. Sem Router de cenários.

**FAST PATH:** para o padrão A, não montar o `.iflw` à mão — preencher
`templates/specs/get_http_external.example.json` e rodar
`python scripts/generate_iflow.py --spec <spec.json> --force` (validate+zip inclusos).

## Padrão A: GET com parâmetros → API externa via HTTP

**Padrão default de toda API GET neste skill.** Chamador faz
`GET /http/<path>?customerId=123&from=2025-01-01` (query params na aba Params do Postman).
O iFlow **sempre** começa lendo a query com Groovy; consulta a API REST externa e devolve JSON.

| # | Passo | Processor | Configuração |
|---|---|---|---|
| S | Sender | HTTPS | `urlPath` `{{Sender_Path}}` (path **fixo**, ex. `/cep`), RoleBased, método GET |
| 0 | Guardar correlation id | Content Modifier | `p_correlationId` ← `SAP_MessageProcessingLogID` |
| 1 | Ler parâmetros da query | Groovy `ReadQueryParams.groovy` | **Obrigatório em todo GET.** Motivo: não há processor nativo que divida `CamelHttpQuery` em properties. Grava `qp_customerId`, `qp_from`, etc. |
| 2 | Validar parâmetros | Router + Content Modifier | Regex/obrigatórios nas `qp_*`; rota inválida → HTTP 400 com **Message Body JSON** preenchido |
| 3 | Montar request para API | Content Modifier | header `Accept`=`application/json` |
| 4 | Consultar API externa | Request Reply + HTTP | `httpAddressWithoutQuery` com `${property.qp_...}`; `httpAddressQuery` se preciso; `GET`; credencial/timeout externalizados |
| 5 | Montar resposta | Content Modifier / converters | `Content-Type`=`application/json`, `CamelHttpResponseCode`=`200`. Reformatar com XSLT/Message Mapping + XmlToJson (versão do perfil), não Groovy. |
| E | End Message | | |
| X | Exception Subprocess | Groovy + Content Modifier | `responseErro` + HTTP 400 + `{"message":"${property.responseErro}"}`. Sem Router |

Exemplo completo: `exemplos/IF_Consulta_API_Externa/`.

### Regras do GET (obrigatórias)

- Valores de consulta = **query string** (`?cep=01001000`). No Postman: URL base + aba **Params**.
- **Nunca** GET com body JSON (anti-padrão de API REST; não desenhar nem sugerir).
- **Nunca** defaultar para path extra após o sender (`/http/cep/01001000`): o HTTPS sender do CPI
  casa o `urlPath` exato; segmentos a mais frequentemente **não disparam** o iFlow.
- Não oferecer “variante sem Groovy via `CamelHttpPath`” como padrão. Path param só se o
  usuário exigir contrato fechado e aceitar o risco de roteamento; mesmo assim documentar o
  limite do sender.

Body JSON, path de recurso rico e payloads grandes = métodos **POST/PUT/PATCH**, não GET.

## Padrão B: POST JSON → API standard SAP (SOAP)

Chamador faz `POST` com JSON; o iFlow converte para XML, mapeia para a mensagem do serviço SOAP
SAP (ex.: `SalesOrderCreateRequestConfirmation_In`), chama o S/4 e devolve JSON.

| # | Passo | Processor | Configuração |
|---|---|---|---|
| S | Sender | HTTPS | `{{Sender_Path}}`, RoleBased |
| 1 | Guardar entrada | Content Modifier | `p_correlationId` (Type `header`, Datatype `java.lang.String`) e `p_bodyOriginal` (Type `expression` `${in.body}`, Datatype `java.lang.String`). Não reescreve o Message Body |
| 2 | JSON para XML | JSON to XML | Processo principal. `additionalRootElementName=root`, `useNamespaces=true`, `addXMLRootElement=true`. XPath seguinte em `/root/...`. Sem CM de reescrita antes. Sem a chave `useNamespaceMapping` no lugar de `useNamespaces` |
| 3 | Extrair campos | Content Modifier | Source Type `xpath`, Datatype `java.lang.String`, um property por campo. XPath só aqui |
| 4 | Validar campos | Router NonXML | `${property.Campo} != '' and ${property.Outro} != ''`. Palavras `and`/`or`. Proibido `&&` e `||`. Sem XPath no Router. Default = inválido |
| 5 | Mapear Request → SalesOrder | Message Mapping | Só na rota válida. Esquerda `xsd/Request.xsd`, direita `wsdl/SalesOrderCreateRequestConfirmation_In.wsdl` |
| 6 | Criar pedido no SAP | Request Reply + SOAP 1.x | `address` `{{SAP_Endpoint}}`, `wsdlURL` `/wsdl/...`, Basic `{{SAP_Credential}}`, `{{Request_Timeout}}` |
| 7 | Extrair confirmação | Filter | `//*[local-name()='SalesOrderCreateConfirmation']` (ajustar ao WSDL) |
| 8 | XML para JSON | XML to JSON | `suppressJsonRoot` `false` |
| 9 | Definir resposta | Content Modifier | `Content-Type`=`application/json`, `CamelHttpResponseCode`=`201` |
| E | End Message | | |
| X | Exception Subprocess | Groovy + Content Modifier | Qualquer falha técnica vira `responseErro` e HTTP 400 `{"message":"${property.responseErro}"}`. Sem Router |

Arquivos gerados pelo agente:

- `xsd/Request.xsd`: derivado do XML do conversor (elemento raiz `root`, arrays como
  `maxOccurs="unbounded"`).
- `wsdl/<serviço>.wsdl`: fornecido pelo usuário ou baixado do SAP Business Accelerator Hub
  (`api.sap.com`) / do próprio S/4 (`/sap/bc/srt/wsdl/...`).
- `mapping/MM_Request_para_SalesOrder.mmap`: se não for possível gerar um `.mmap` válido com as
  ligações, entregar o passo configurado + a tabela campo-a-campo e orientar a ligação no
  designer. Nunca trocar o mapping por Groovy.

Variante OData: trocar SOAP por OData V2 `Create(POST)` com `resourcePath` `A_SalesOrder` e
destino do mapping = EDMX; a resposta já pode ir para XML to JSON.

## Padrão C: GET → OData SAP (consulta)

Chamador faz `GET` com filtros; o iFlow consulta `API_BUSINESS_PARTNER` (ou similar) e devolve
JSON.

| # | Passo | Processor | Configuração |
|---|---|---|---|
| S | Sender | HTTPS | `{{Sender_Path}}` |
| 1 | Ler parâmetros da query | Groovy `ReadQueryParams.groovy` | mesmo motivo do padrão A |
| 2 | Consultar Business Partner | Request Reply + OData V2 | `Query(GET)`, `resourcePath` `A_BusinessPartner`, `queryOptions` `$select=...&$filter=BusinessPartner eq '${property.qp_id}'`, `{{OData_URL}}`, `{{OData_Credential}}`, `{{OData_PageSize}}` |
| 3 | XML para JSON | XML to JSON | `suppressJsonRoot` `true` |
| 4 | Definir resposta | Content Modifier | `Content-Type`, `CamelHttpResponseCode` 200 |
| X | Exception Subprocess | Groovy + Content Modifier | `responseErro` + HTTP 400 + `{"message":"${property.responseErro}"}`. Sem Router |

Na entrega, avisar que o wizard *Model Operation* do adapter OData deve ser executado uma vez
no designer para gerar/confirmar o EDMX, caso não tenha sido fornecido.

## Decisões recorrentes

| Situação | Decisão |
|---|---|
| iFlow HTTPS GET (qualquer consulta) | Query params + `ReadQueryParams.groovy` (obrigatório); sem body; sem path extra no sender |
| Entrada JSON e destino com esquema (WSDL/XSD/EDMX) | JSON to XML → Message Mapping (métodos POST/PUT/PATCH) |
| Entrada JSON e saída JSON com campos renomeados | JSON to XML → XSLT (ou Message Mapping com XSD dos dois lados) → XML to JSON. Não Groovy. |
| Só repassar o body e trocar headers | Content Modifier |
| Vários destinos a partir de um lote | Splitter → (passos) → Gather; uma chamada por item só se a API não aceitar lote |
| API aceita o lote inteiro | Uma chamada, sem Splitter |
| Mesma lógica usada em dois pontos do mesmo fluxo | Local Integration Process + Process Call |
| Mesma lógica em mais de um iFlow, ou negócio vs auditoria | iFlow compartilhado chamado por ProcessDirect, endereço externalizado |
| Retry, JMS ou outra reentrega | Chave de idempotência na proposta (`p_correlationId` ou id de negócio); o receiver não aplica o efeito duas vezes |
| Payload de negócio ou dado sensível | Não anexar no MPL, script nem Data Store; `enableMPLAttachments` `false` |
| Código HTTP diferente por resultado | Router por `${header.CamelHttpResponseCode}` com token sem espaço e sem pipe (`regex '^2.*'`, `regex '^4.*'`). Cada rota de erro tem body JSON |
| Resposta ao chamador | Sempre JSON: sucesso, warning e erro. `Content-Type` `application/json` e Message Body preenchido |
| Content Modifier property Type `expression` | Datatype **sempre** `java.lang.String` (`p_bodyOriginal`). Também String em Type `header`/`property`/`constant` de texto. XPath: String ou NodeList conforme o retorno |
| POST JSON com validação por Router | JSON to XML → CM xpath properties (Datatype String) → Router NonXML `${property.Campo} != '' and ${property.Outro} != ''`. Palavras `and`/`or`; proibido `&&`/`||`. Sem CM que só reescreve o body. Sem XPath boolean no Router. Pass-through restaura `p_bodyOriginal` na rota válida |
| JSON to XML depois de sender HTTPS | No processo principal, direto no body JSON do sender. CM anterior só grava properties e não apaga o body |
