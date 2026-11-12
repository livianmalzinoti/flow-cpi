# Fluxo de trabalho da conversa

## 1. Versão do tenant (primeira mensagem, sempre)

Pedir exatamente isto, antes de qualquer outra pergunta:

> Antes de começar, me passe as versões do seu tenant. No Integration Suite, clique no ícone de
> perfil (canto superior direito) → **About**. Copie as linhas de **Cloud Integration** e
> **Cloud Integration Runtime**. Exemplo:
>
> ```
> Cloud Integration            6.83.108
> Cloud Integration Runtime    8.47.22
> ```

Guardar as duas versões. Elas definem:

- Quais processors e versões de componente existem no tenant (ex.: Content Modifier 1.5 vs 1.6,
  HTTP adapter 1.14 vs 1.17). Em dúvida, confirmar no `help.sap.com` (*What's New* do mês da versão).
- Quais features podem ser usadas (ex.: tipo `external parameter` direto no Content Modifier,
  JSON Schema no Message Mapping, Data Store Operations novas).
- Qual Groovy/Java está no runtime (afeta parsing de data, JSON e XML em scripts).

Se o usuário não souber onde achar, orientar. Não prosseguir sem as versões.

## 2. Documentação ou informações do fluxo

Pedir a documentação funcional (PDF, DOCX, MD, texto colado) ou, na falta dela, as informações
abaixo. Fazer as perguntas em uma rodada curta; só perguntar o que ainda não foi respondido.

| Pergunta | Por que importa |
|---|---|
| Quem chama o fluxo? (sistema externo via HTTPS, outro iFlow via ProcessDirect, timer, fila) | Define o sender adapter e o Start. |
| Método HTTP e como chegam os dados? (GET com query params, POST/PUT com JSON/XML) | **GET → sempre query params + Groovy `ReadQueryParams`** (nunca body JSON no GET; path extra após o sender não é o padrão). POST/PUT JSON a validar → JSON to XML, CM com properties xpath e Router NonXML nas properties. Sem XPath no Router. |
| Quais query params o GET recebe? (nomes, obrigatórios, exemplo) | Vira `qp_*` após o script; validação no Router; URL do receiver. |
| Exemplo do payload de entrada (só POST/PUT/PATCH) | Base para o XSD de origem do mapeamento e para o Content Modifier. GET não usa body. |
| Para onde vai? (API standard SAP SOAP/OData, API externa REST, S/4, SuccessFactors, SFTP) | Define o receiver adapter, autenticação e formato (WSDL/EDMX). |
| Tem WSDL/XSD/EDMX do destino? | Lado direito do Message Mapping. Sem ele, pedir ou buscar no SAP API Business Hub. |
| Exemplo da resposta esperada pelo chamador | Define o passo final (XML to JSON ou Content Modifier). |
| Autenticação no destino (Basic, OAuth2 client credentials, certificado) | Nome da credencial é externalizado; o tipo define o adapter. |
| Regras de transformação/validação (campos obrigatórios, conversões, enriquecimentos) | Decide Message Mapping vs XSLT vs Content Modifier; nunca Groovy por padrão. |
| Volume e tamanho (lote? paginação? chamadas por minuto?) | Splitter/Gather, paginação OData, timeout. |
| Há retry, JMS ou outra reentrega? | A proposta nomeia a chave de idempotência e como o receiver evita duplicar o efeito. |
| A mesma sequência já existe em outro iFlow? | Extrair para um iFlow chamado por ProcessDirect, endereço externalizado. |
| O que devolver em caso de erro | Exception Subprocess simples: Groovy grava `responseErro` e Content Modifier devolve HTTP 400 `{"message":"${property.responseErro}"}`. Sem Router de cenários. |

## 3. Pesquisa obrigatória (antes da proposta e da geração)

Não inventar contrato de API nem sintaxe de processor. Consultar:

- SAP Business Accelerator Hub e SAP Docs: campos, autenticação e URL da API.
- https://help.sap.com/docs/cloud-integration/sap-cloud-integration/ para cada processor e adapter
  (Router, Content Modifier, JSON to XML, adapters). Router: Define Router. NonXML usa as
  palavras `and` e `or`. `&&` e `||` são recusados (`Expected tokens: [and, or]`).
- JSON to XML Converter no mesmo Help, e conferir o export do designer do tenant. No CI 6.84
  o passo que converte usa `additionalRootElementName=root`, `useNamespaces=true` e
  `addXMLRootElement=true`. XPath em `/root/...`. A chave `useNamespaceMapping` não converte
  neste tenant (`Content is not allowed in prolog`).

Usar WebFetch/WebSearch. O MCP `user-sap-docs` entra só se já estiver autenticado.

## 4. Pensar antes de gerar: a proposta

Antes de escrever qualquer arquivo, apresentar ao usuário uma proposta neste formato e esperar o
"ok" (ou os ajustes):

```
## Proposta: <Nome do iFlow>

Sender: HTTPS, /caminho, método POST, autenticação Role-based (ESBMessaging.send)
Receiver: SOAP 1.x → API standard SAP <nome>, Basic (credencial externalizada)

| # | Passo (nome no designer)        | Processor         | Motivo / configuração                             |
|---|---------------------------------|-------------------|---------------------------------------------------|
| 1 | Guardar entrada                 | Content Modifier  | `p_correlationId` Type `header` + `p_bodyOriginal` Type `expression` `${in.body}`; ambos Datatype **`java.lang.String`** |
| 2 | JSON para XML                   | JSON to XML       | Processo principal. Raiz `root`, `useNamespaces=true`, `addXMLRootElement=true`. XPath `/root/...`. Sem CM de reescrita antes |
| 3 | Extrair campos                  | Content Modifier  | Source Type `xpath`, Datatype `java.lang.String`, Value = XPath de cada campo |
| 4 | Validar campos                  | Router NonXML     | `${property.Campo} != '' and ${property.Outro} != ''`. Palavras `and`/`or`; proibido `&&`/`||`. Default = inválido. Sem XPath boolean no Router |
| 5 | Mapear Request → <SAP>          | Message Mapping   | XSD origem (gerado do JSON) → WSDL destino. Só na rota válida |
| 6 | Chamar <API SAP>                | Request Reply     | SOAP receiver, URL {{SAP_Endpoint}}                |
| 7 | Resposta SOAP para JSON         | XML to JSON       | remove envelope via XPath no Filter antes          |
| E | Exception Subprocess            | Groovy + Content Modifier | `responseErro` + HTTP 400 `{"message":"${property.responseErro}"}`. Sem Router |

Groovy: `GravarResponseErro.groovy` — lê CamelExceptionCaught e grava `responseErro`; não há processor nativo para isso. Em GET, também `ReadQueryParams.groovy`.

Parâmetros externalizados (aba Configure):
- SAP_Endpoint (URL do serviço)
- SAP_Credential (nome da credencial no Security Material)
- Request_Timeout (ms, padrão 60000)
- Sender_Path (/caminho)

Pasta de destino e nome do iFlow: <confirmar>
```

Critérios ao decidir cada passo:

1. Existe processor nativo que faz isso? Usar. Ver `processors.md`.
2. É transformação estrutural com esquema conhecido dos dois lados? Message Mapping (XSD/WSDL).
3. É transformação estrutural sem esquema estável ou com lógica condicional pesada? XSLT.
4. É montar body/headers/properties com valores simples ou expressões Camel? Content Modifier.
5. É iFlow HTTPS **GET**? Incluir **sempre** `ReadQueryParams.groovy` (não negociar por path
   nem body). Ver `groovy.md` e `padroes-fluxo.md` Padrão A.
6. Só sobrou regra que nenhum dos anteriores cobre (criptografia, calendário complexo, API Java
   específica)? Groovy, com o motivo escrito. Ver `groovy.md`.
7. O primeiro Content Modifier grava `p_correlationId` a partir de `SAP_MessageProcessingLogID`.
   Com retry ou JMS, a proposta diz qual campo torna o receiver idempotente.
8. A mesma sequência em outro iFlow vai para ProcessDirect. Log de payload completo fica de fora
   do artefato; Trace é ligado só no teste e desligado em seguida.
9. Content Modifiers de erro (400/404/5xx) **sempre** com Message Body JSON preenchido — body
   vazio no designer gera resposta vazia no Postman.

Em dúvida sobre nome de propriedade, versão de componente ou comportamento de adapter, buscar em
`help.sap.com/docs/cloud-integration` (busca na web). Não resumir o fluxo em um script porque
"é mais rápido".

## 5. Pasta e nome

Perguntar (pode ir na proposta):

- Pasta onde salvar o projeto e o `.zip`.
- Nome do iFlow. Regras: sem espaço nem acento para o `Bundle-SymbolicName` (ex.: `IF_Pedido_Criar`);
  o `Bundle-Name` pode ter espaços (ex.: `IF Pedido Criar`).

## 6. Gerar, validar, empacotar

```
<pasta>/<Nome>/                   ← projeto expandido (fica para o desenvolvedor editar)
<pasta>/<Nome>.zip                ← arquivo para upload
```

Passos:

1. Copiar `templates/` para `<pasta>/<Nome>/` substituindo `__IFLOW_ID__`, `__IFLOW_NAME__`,
   `__DESCRIPTION__`.
2. Escrever `src/main/resources/scenarioflows/integrationflow/<Nome>.iflw` conforme `iflw-xml.md`.
3. Criar scripts (`script/`), mapeamentos (`mapping/`), esquemas (`xsd/`, `wsdl/`, `xsl/`, `edmx/`).
4. Declarar todos os `{{Parametros}}` em `parameters.propdef` e `parameters.prop`.
5. `python3 scripts/validate_iflow.py <pasta>/<Nome>` → corrigir até 0 erros.
6. `python3 scripts/package_iflow.py <pasta>/<Nome> --out <pasta>/<Nome>.zip`.

## 7. Entrega

Seguir `entrega.md`. Sempre listar: caminho do zip, passos do fluxo, scripts Groovy (com motivo),
parâmetros a conferir na aba Configure, o que precisa ser feito manualmente no designer (ex.:
ligar campos de um Message Mapping, rodar o wizard de OData).
