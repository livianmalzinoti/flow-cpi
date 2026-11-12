# Entrega e upload

## Antes de entregar

- Preferência: `scripts/generate_iflow.py --spec <spec.json>` já validou e gerou o `.zip`
  (0 erros). Não revalidar/reempacotar sem necessidade.
- Fallback: `validate_iflow.py` **1×** com `0 erro(s)` e `package_iflow.py --skip-validate` **1×**.
- Avisos do validador foram lidos; os relevantes aparecem na mensagem de entrega.

## Mensagem de entrega (formato)

```
## <Nome do iFlow> gerado

Arquivos:
- <pasta>/<Nome>.zip            → upload no Integration Suite
- <pasta>/<Nome>/               → projeto expandido (para edição/versionamento)

Fluxo (<n> passos):
1. <Passo> — <processor>
2. ...
X. Exception Subprocess — Groovy `GravarResponseErro` + Content Modifier (400, `{"message":"${property.responseErro}"}`)

Groovy: <nenhum | lista: arquivo — motivo>

Parâmetros (aba Configure):
| Parâmetro | O que é | Padrão | Onde obter |
|---|---|---|---|

Ações manuais no designer (se houver):
- Ligar campos do Message Mapping <nome> conforme a tabela abaixo
- Rodar "Model Operation" no adapter OData para gerar o EDMX
- Cadastrar credencial <nome> em Monitor → Security Material

Como importar e testar: (seção abaixo resumida)
```

## Importar no Integration Suite

1. **Design → Integrations and APIs** → abrir o Integration Package de destino (ou criar um).
2. **Edit → Artifacts → Add → Integration Flow → Upload**. Selecionar o `.zip`. Nome e ID são
   lidos do `MANIFEST.MF`; podem ser ajustados na tela.
3. Abrir o iFlow. Conferir que o designer renderiza todos os passos e que não há ícone de erro.
   Se um passo pedir "upgrade" de versão, aceitar.
4. **Configure** (botão no canto superior direito): revisar cada parâmetro. Sender: caminho.
   Receiver: URL, credencial, timeout. More: parâmetros funcionais.
5. **Security Material** (Monitor → Manage Security → Security Material): cadastrar as
   credenciais com os nomes informados nos parâmetros (`User Credentials`, `OAuth2 Client
   Credentials`, etc.).
6. **Save → Deploy**. Acompanhar em *Monitor → Manage Integration Content*; status deve ficar
   `Started`. Copiar o endpoint.

## Testar

Endpoint: `https://<tenant>.it-cpi0xx-rt.cfapps.<region>.hana.ondemand.com/http/<Sender_Path>`.

Autenticação: OAuth2 client credentials da instância de processo (role `ESBMessaging.send`) ou
Basic com usuário técnico que tenha a role.

```bash
# GET com parâmetros (padrão — query string; NÃO usar body nem /path/valor extra)
curl -s -u "$CPI_USER:$CPI_PASS" \
  "https://<runtime>/http/<path>?customerId=123&from=2025-01-01"

# POST JSON (escrita/criação — body permitido)
curl -s -u "$CPI_USER:$CPI_PASS" -H "Content-Type: application/json" \
  -d @request.json "https://<runtime>/http/<path>"
```

No Postman para GET: método GET, URL `.../http/<path>`, aba **Params** (`cep`=`01001000`),
sem Body. Path tipo `.../http/cep/01001000` não é o contrato padrão deste skill.

Verificar em *Monitor → Monitor Message Processing*: status `Completed`. O `correlationId`
devolvido no erro é o `SAP_MessageProcessingLogID`; buscar o MPL por ele. Para ver o payload,
ligar *Trace* no iFlow (Manage Integration Content → Log Configuration → Trace), repetir o
teste e voltar o log para o nível anterior. Trace e anexo de payload ficam desligados no
tenant produtivo.

## Problemas comuns na importação

| Sintoma | Causa | Correção |
|---|---|---|
| "Invalid artifact" no upload | zip com pasta raiz, `MANIFEST.MF` fora de `META-INF/` ou sem linha em branco final | Reempacotar com `package_iflow.py` |
| Router: `InvalidXPathException` + `SAXParseException` | A condição do Router é XPath no body (`boolean(/root[...])`) | Tirar o XPath do Router. JSON to XML → Content Modifier Source Type `xpath` (Datatype `java.lang.String`, `/root/...`) → Router NonXML `${property.Campo} != '' and ${property.Outro} != ''` |
| XPath após JSON to XML: `Content is not allowed in prolog` | O conversor não gerou XML. Causa típica: raiz diferente de `root` ou chave `useNamespaceMapping` em vez de `useNamespaces=true` | Alinhar ao export do designer: `additionalRootElementName=root`, `useNamespaces=true`, `addXMLRootElement=true`. XPath em `/root/...` |
| Router: `Token '&&' not supported... Expected tokens: [and, or]` | Condição NonXML usou `&&` ou `||` | Trocar pelas palavras `and` e `or` ([Define Router](https://help.sap.com/docs/cloud-integration/sap-cloud-integration/define-router)) |
| Fluxo abre vazio | falta `bpmndi:BPMNDiagram` ou shapes | Conferir `iflw-xml.md` → Diagrama |
| Passo com ícone de erro "version not supported" | `componentVersion` maior que a do tenant | Usar a versão indicada em `processors.md`/`adapters.md` ou menor |
| Script "undefined could not be loaded" | BOM/encoding ou arquivo não está em `script/` | Regravar UTF-8 sem BOM |
| Parâmetro não aparece na aba Configure | não está no `.propdef` ou nome diferente do `{{}}` | Validador acusa; corrigir |
| 401 ao testar | credencial sem role `ESBMessaging.send` | Ajustar no BTP cockpit |
| Erro de certificado ao chamar receiver | CA não está no keystore do tenant | Importar em Security Material → Keystore |
