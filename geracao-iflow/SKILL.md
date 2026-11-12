---
name: geracao-iflow
description: >-
  Geração de Integration Flows (iFlow) para SAP Cloud Integration / Integration Suite a partir de
  conversa com o usuário ou de documentação funcional, entregando o .zip pronto para importar em um
  Integration Package. Contém a estrutura e extensões do pacote, o XML do .iflw, o catálogo de
  processors nativos, os adapters, as regras de externalização e os padrões de fluxo mais comuns.
  Use sempre que o pedido envolver CPI, Cloud Integration, Integration Suite, iFlow, .iflw,
  adapters (HTTPS, HTTP, SOAP, OData, ProcessDirect), Content Modifier, Message Mapping, Groovy no CPI.
---

# Geração de iFlow (SAP Cloud Integration)

Esta skill define como o agente conduz a conversa, decide a arquitetura do fluxo e gera o pacote
`.zip` aceito pelo Integration Suite. O diretório desta skill é a raiz de todos os caminhos abaixo.

## FAST PATH / checklist curto (ler primeiro)

**Meta:** proposta ≤2 min; geração+validate+zip ≤3–5 min wall-clock (ideal ≤5 min total no Cursor).

### O que ler SEMPRE (1× por sessão)
1. Esta seção + **Regras invioláveis** abaixo.
2. `references/padroes-fluxo.md` (escolher A/B/C).

### O que ler SOB DEMANDA (trechos, não o arquivo inteiro)
| Situação | Arquivo |
|---|---|
| XML de processor específico | `references/processors.md` |
| Sender/receiver | `references/adapters.md` |
| Editar BPMN à mão (evitar) | `references/iflw-xml.md` |
| Groovy extra | `references/groovy.md` |
| Nomes de parâmetro | `references/externalizacao.md` |
| Estrutura do zip | `references/estrutura-pacote.md` |
| Entrega | `references/entrega.md` |
| Roteiro de perguntas | `references/fluxo-de-trabalho.md` |

**Não** ler todas as references de uma vez. **Não** reler esta skill inteira em loops de correção.

### Pesquisa obrigatória (antes de propor e de gerar)
Não inventar contrato de API nem sintaxe de processor.
- SAP Business Accelerator Hub e SAP Docs: campos, autenticação e URL.
- https://help.sap.com/docs/cloud-integration/sap-cloud-integration/ para cada processor e adapter (Router, Content Modifier, JSON to XML Converter, adapters). Router: Define Router. JSON to XML: alinhar as properties ao export do designer (CI 6.84: raiz `root`, `useNamespaces=true`, `addXMLRootElement=true`; XPath `/root/...`).
- WebFetch/WebSearch. MCP `user-sap-docs` só se já estiver autenticado.

### Geração rápida (obrigatória quando o padrão couber)
1. Escrever spec curta em JSON (preferir) ou YAML — modelo:
   `templates/specs/get_http_external.example.json`
2. **Uma** chamada (scaffold + iflw + validate + zip no mesmo processo):
   ```bash
   python scripts/generate_iflow.py --spec <spec.json> --force
   ```
3. Se 0 erros → entregar. Não rodar validate/package de novo “por garantia”.
4. Fallback manual: `scaffold_iflow.py` → editar → `validate_iflow.py` **1×** →
   `package_iflow.py --skip-validate` **1×**.

Scripts: `scripts/generate_iflow.py`, `scripts/iflw_builder.py`, `scripts/validate_iflow.py`,
`scripts/package_iflow.py`, `scripts/scaffold_iflow.py`.

## Arquivos de referência

| Arquivo | Quando ler |
|---|---|
| `references/padroes-fluxo.md` | Sempre (FAST PATH). |
| `references/fluxo-de-trabalho.md` | Se faltar info do usuário. |
| `references/estrutura-pacote.md` | Só se generate_iflow não for usado. |
| `references/iflw-xml.md` | Só edição manual do `.iflw`. |
| `references/processors.md` | Ao desenhar passo sem snippet no builder. |
| `references/adapters.md` | Adapter fora de HTTPS/HTTP padrão. |
| `references/externalizacao.md` | Dúvida de nome de parâmetro. |
| `references/groovy.md` | Antes de propor Groovy além dos 2 obrigatórios. |
| `references/entrega.md` | Ao entregar. |
| `templates/` | Base do pacote; `templates/specs/` = exemplos de spec. |

## Sequência obrigatória

1. **Versão do tenant.** Primeira mensagem: *About* → Cloud Integration + Runtime. Não desenhar antes.
2. **Documentação ou informações do fluxo.** Se faltar, perguntas de `fluxo-de-trabalho.md` (uma rodada).
3. **Proposta** com processors nativos, adapters, params, Exception Subprocess. Groovy só com motivo.
4. **Pasta e nome** do iFlow (pode ir com a proposta).
5. **Gerar** com `generate_iflow.py` (preferência) ou scaffold + builder.
6. **Validar uma vez** (já incluso no generate). 0 erros.
7. **Empacotar uma vez** (já incluso no generate).
8. **Entregar** conforme `references/entrega.md`.

## Regras invioláveis

- **API HTTPS GET = query params + Groovy `ReadQueryParams`.** Sempre que o iFlow expuser um
  endpoint GET (consulta), os valores de filtro/chave vêm na query string
  (`GET /http/<path>?param=valor`). Incluir obrigatoriamente o script
  `templates/.../ReadQueryParams.groovy` no início do fluxo (após gravar `p_correlationId`),
  gravando `qp_<nome>`. Motivo fixo na proposta: não há processor nativo que divida
  `CamelHttpQuery`. **Proibido:** GET com body JSON (anti-padrão de API); **proibido** confiar
  só em path extra após o `urlPath` do sender (`/cep/01001000`) — o HTTPS sender do CPI casa o
  path exato e a chamada não chega no iFlow. Path param só se o usuário exigir por contrato já
  fechado e ciente dessa limitação; o padrão e a proposta default são sempre query + Groovy.
- **Processor nativo primeiro.** Content Modifier, Router, JSON to XML, XML to JSON, Message Mapping,
  XSLT, Request Reply, Splitter, Gather, Filter, Content Enricher, Process Call. Groovy é a última
  opção e sempre com justificativa de uma frase no passo e na proposta — **exceto** o
  `ReadQueryParams` em todo GET e o `GravarResponseErro` do Exception Subprocess, que são obrigatórios.
- **Um passo por ação, com nome do que faz.** Manutenção é ler o fluxo no designer, não abrir código.
- **Tudo que muda entre ambientes é externalizado.** URL/host, caminho, credencial, timeout, nome de
  fila, endpoint ProcessDirect, página do OData. Nada de `https://` fixo em adapter. Metade
  externalizada é erro: o desenvolvedor não consegue ajustar pela aba Configure.
- **Clean core.** Sem dependência externa em Groovy, sem biblioteca fora do runtime, sem lógica de
  negócio escondida em script.
- **Entrada e saída.** GET entra por query params. POST/PUT/PATCH entra por body JSON. Toda
  resposta ao requisitante (sucesso, warning e erro) sai em JSON: `Content-Type` `application/json`
  e Message Body preenchido. Erro funcional no fluxo principal no mínimo `{"message":"..."}`.
  Content Modifier que responde ao chamador (nome `Responder*` / `Montar resposta*`, ou que define
  `CamelHttpResponseCode`) tem Message Body **Type** `expression` e o texto nas propriedades
  `bodyContent` e `wrapContent`. As duas levam o mesmo JSON ou `${in.body}`. Headers sozinhos
  deixam a aba Body vazia e a resposta sai sem payload. Passo que só grava header ou property
  deixa `bodyType` vazio, para não apagar o body.
- **Exception Subprocess em todo fluxo síncrono, um único caminho.** `triggeredByEvent="true"`.
  Error Start → Groovy `GravarResponseErro.groovy` (grava qualquer erro na property `responseErro`)
  → Content Modifier com body `{"message":"${property.responseErro}"}`, header `Content-Type`
  `application/json` e header `CamelHttpResponseCode` `400` → **um único** End Message.
  Sem Router e sem vários cenários de exceção no subprocesso. O Groovy só lê
  `CamelExceptionCaught` e grava a property; o Content Modifier monta o JSON e os headers.
  Motivo do Groovy: não há processor nativo que leia a exceção capturada.
- **End Event, End Message e Error End na versão 1.0.** `cmdVariantUri` `version::1.0.0` e
  `componentVersion` `1.0`. Versão 1.1 desses fins é recusada pelo profile:
  `component EndEvent with version 1.1 is not supported in Cloud Integration profile.`
- **Router NonXML** ([Define Router](https://help.sap.com/docs/cloud-integration/sap-cloud-integration/define-router)).
  Operadores lógicos são as palavras **`and`** e **`or`**. Proibido `&&` e `||`: o runtime
  responde `Token '&&' not supported... Expected tokens: [and, or]`.
  Exemplo: `${property.PurchaseOrderType} != '' and ${property.CompanyCode} != ''`.
  Valor entre aspas é um token só: sem espaço e sem `|`. Texto com espaço vai para uma property.
  Isso não autoriza um Router dentro do Exception Subprocess.
- **POST JSON + validação por Router.** Sequência no processo principal: Content Modifier só
  grava `p_correlationId` e `p_bodyOriginal` (Type `expression` `${in.body}`, Datatype
  `java.lang.String`, **sem** reescrever o Message Body) → JSON to XML
  (`additionalRootElementName=root`, `useNamespaces=true`, `addXMLRootElement=true`;
  não usar `useNamespaceMapping` no lugar de `useNamespaces`) →
  Content Modifier lê o XML e cria Exchange Properties com Source Type `xpath` em `/root/...`
  e Datatype `java.lang.String` → Router **NonXML** compara `${property.NomeDoCampo}`.
  O body do sender HTTPS já é JSON; não criar Content Modifier só para reescrevê-lo antes do conversor.
  `Content is not allowed in prolog` no XPath seguinte significa que o conversor não gerou XML.
- **Router não avalia XPath.** Proibido `boolean(/root[string-length(...)])` no Router.
  O XPath fica só na coluna Value do Content Modifier. Condição NonXML junta properties com
  a palavra `and`: `${property.PurchaseOrderType} != '' and ${property.CompanyCode} != ''`
  (sem `&&`, sem `|`, sem espaço dentro das aspas). Rota default = inválido. Se o receiver
  precisa do JSON original, a rota válida restaura `${property.p_bodyOriginal}`.
- **Datatype em Exchange Property.** Type `expression`, `constant`, `header` e `property` de
  texto → Datatype **sempre** `java.lang.String`. Type `xpath` de texto → também
  `java.lang.String` (nó/lista só se o passo precisar de DOM: `org.w3c.dom.NodeList`).
- **Correlation id do MPL.** O primeiro Content Modifier grava a property `p_correlationId` a
  partir do header `SAP_MessageProcessingLogID`, Datatype `java.lang.String`. Header de saída
  com esse id só quando o contrato do receiver pede.
- **Idempotência quando houver retry ou JMS.** A proposta nomeia a chave (id de negócio ou
  `p_correlationId`) e como o receiver evita processar a mesma mensagem duas vezes. Retry
  reentrega.
- **Payload sensível fora do log produtivo.** Não gravar o body completo em anexo do MPL,
  script ou Data Store. `enableMPLAttachments` fica `false`. Trace no Monitor é ação manual
  e temporária; depois do teste, desligar.
- **ProcessDirect para lógica repetida entre iFlows.** A mesma sequência em mais de um iFlow
  vira um fluxo chamado por ProcessDirect, com o endereço externalizado. Dentro do mesmo
  iFlow, Local Integration Process + Process Call.
- **Nunca entregar zip não validado.**
- **Preferir spec + `generate_iflow.py` a BPMN manual.** Exception Subprocess, CM JSON, HTTPS
  sender e HTTP receiver já saem corretos do builder — não reinventar.
- Responder em português. Fora do escopo (ABAP, CDS, NiFi, documentação funcional), recusar e
  redirecionar.
