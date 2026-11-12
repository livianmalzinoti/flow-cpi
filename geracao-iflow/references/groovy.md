# Groovy: quando usar e como escrever

## Quando não usar

Não usar Groovy para: ler/montar JSON ou XML simples, copiar header para property, definir
`Content-Type` ou código HTTP, formatar a resposta de erro, rotear por valor de header, remover
envelope SOAP, converter JSON↔XML, mapear campos entre esquemas. Tudo isso é Content Modifier,
Router, Filter, converter, Message Mapping ou XSLT (`processors.md`).

Antes de qualquer validação: no Content Modifier que cria `p_bodyOriginal`, Type `expression`
e Datatype **`java.lang.String`**. Sem isso a property pode ser stream. Type
`header`/`property`/`constant` de texto na `propertyTable` também usam `java.lang.String`.
XPath de texto no Content Modifier usa o mesmo Datatype.

Validar campos de um POST/PUT/PATCH JSON **não é Groovy**. A sequência é JSON to XML no
processo principal, Content Modifier com Source Type `xpath` (Datatype `java.lang.String`)
e Router NonXML `${property.Campo} != '' and ${property.Outro} != ''` (palavras `and`/`or`, nunca `&&`/`||`). O XPath fica só no Content Modifier. Não criar
Content Modifier só para reescrever o body antes do conversor.

Motivos: Groovy consome mais runtime, quebra quando a versão da biblioteca do tenant muda
(JSON, XML, data), não aparece na leitura do fluxo e o editor do designer às vezes não abre script
importado (`undefined could not be loaded`).

## Quando usar

Só quando nenhum processor nativo cobre a regra — **com duas exceções de produto:**

### Exceção obrigatória: todo iFlow HTTPS GET

Sempre que o artefato expuser **API GET** (consulta), incluir **sempre**
`ReadQueryParams.groovy` no início do fluxo (após o Content Modifier do `p_correlationId`).
Não é opcional e não se troca por path/`CamelHttpPath` por “evitar Groovy”.

Motivo de produto (além do técnico): em GET os valores de consulta vêm em **query params**;
GET com body JSON é anti-padrão de API; path extra após o `urlPath` do sender HTTPS do CPI
costuma não rotear para o iFlow. Ver `padroes-fluxo.md` → Padrão A.

### Exceção obrigatória: Exception Subprocess

Todo fluxo síncrono inclui `GravarResponseErro.groovy` no Exception Subprocess, entre o Error
Start e o Content Modifier. O script lê `CamelExceptionCaught` e grava uma única property
`responseErro`. O Content Modifier monta `{"message":"${property.responseErro}"}`,
`Content-Type` `application/json` e `CamelHttpResponseCode` `400`. Não usar o script para
montar o JSON, definir o código HTTP ou classificar a exceção. Não colocar Router no subprocesso.

Motivo: não há processor nativo que leia a exceção capturada e grave o texto numa property.

Demais casos reais (Groovy só se nenhum nativo cobrir):

| Caso | Por que não há nativo |
|---|---|
| Quebrar a query string de um GET (`CamelHttpQuery`) em properties | O HTTPS sender entrega a query inteira num header; não existe processor que a divida em pares chave/valor. **Obrigatório em todo GET.** |
| Ler `CamelExceptionCaught` e gravar `responseErro` | Não há processor que copie o texto da exceção para uma property. **Obrigatório no Exception Subprocess.** O Content Modifier monta o JSON e o HTTP 400. |
| (não usar) validar campos de POST JSON no Router | Há processor nativo: JSON to XML, Content Modifier Source Type `xpath` e Router NonXML nas properties. Groovy não entra nesse caso. |
| Criptografia/hash não coberto por Encoder/Signer (HMAC específico, cifra custom) | Processors de segurança cobrem PGP, PKCS#7, XML Signature; não cobrem algoritmos arbitrários. |
| Cálculo de calendário (dias úteis, feriados, fuso) | Camel Simple só formata data. |
| Log customizado em anexo do MPL com condição | `messageLog.addAttachmentAsString` só existe em script. |
| Chamada a API Java específica do runtime (ex.: `SecureStoreService` para ler credencial no body) | Não há processor. |
| Parsing de formato proprietário (posicional complexo, EDI fora do adapter) | Converter CSV/EDI cobre só os formatos padrão. |

Na proposta e na entrega, cada script vem com uma frase: "Groovy porque <regra> não é coberta
por <processor mais próximo>".

## Regras de escrita

- Um script, uma responsabilidade. Nome do arquivo diz o que faz: `ReadQueryParams.groovy`,
  `CalcDiasUteis.groovy`.
- Função de entrada `Message processData(Message message)`; `scriptFunction` no passo =
  `processData`.
- Só APIs do runtime: `com.sap.gateway.ip.core.customdev.util.Message`, `groovy.json.*`,
  `groovy.xml.*`, `java.*`. Nenhuma biblioteca externa, nenhum `@Grab`.
- Entrada e saída por headers/properties/body; nada de estado estático.
- Null-safe: `message.getHeaders().get("X") as String ?: ""`.
- Sem `println`. Não gravar o body completo nem campo sensível (credencial, token, documento,
  payload de negócio) em anexo do MPL. `addAttachmentAsString` só com property `p_debug` e só
  para diagnóstico pontual; o padrão do artefato é não anexar payload.
- Arquivo UTF-8 sem BOM, quebras `\n`. BOM e encoding errado são a causa típica de
  `undefined could not be loaded` no editor.
- Lançar erro com mensagem útil: `throw new IllegalArgumentException("Parâmetro customerId é obrigatório")`
  cai no Exception Subprocess. O Groovy de lá copia `getMessage()` para a property `responseErro`.

## Template

```groovy
import com.sap.gateway.ip.core.customdev.util.Message

/*
 * <O que o script faz em uma linha>
 * Motivo do Groovy: <qual regra nenhum processor nativo cobre>
 * Entrada : <headers/properties/body lidos>
 * Saída   : <headers/properties/body gravados>
 */
Message processData(Message message) {
    // implementação
    return message
}
```

## Script padrão: qualquer erro do Exception Subprocess (obrigatório)

Arquivo: `templates/src/main/resources/script/GravarResponseErro.groovy`. Lê a property
`CamelExceptionCaught`, usa `getMessage()` (ou `Erro inesperado`), escapa `\`, `"`, quebra de
linha e `${`, e grava `responseErro`. O Content Modifier seguinte devolve
`{"message":"${property.responseErro}"}` com HTTP 400.

**Quando gerar iFlow síncrono:** copiar este template para `script/` e ligar o passo Groovy no
Exception Subprocess. Na proposta e na entrega, o motivo é a frase acima.

## Script padrão: parâmetros de query de um GET (obrigatório)

Arquivo: `templates/src/main/resources/script/ReadQueryParams.groovy`. Lê `CamelHttpQuery`
(`customerId=123&from=2025-01-01` ou `cep=01001000`) e grava uma property `qp_<nome>` por
parâmetro, decodificando URL encoding. Opcionalmente valida obrigatórios a partir da property
`p_requiredParams` (lista separada por vírgula, definida num Content Modifier antes do script,
externalizável).

**Quando gerar iFlow GET:** copiar este template para `script/`, criar o passo Groovy no `.iflw`,
e na proposta/entrega listar o script com o motivo fixo acima. Contrato de teste:
`GET https://<runtime>/http/<Sender_Path>?param=valor` (Postman → Params), **sem** body.

Uso típico depois do script: Router valida `${property.qp_cep}`; Content Modifier / HTTP
receiver montam URL com `${property.qp_...}`.

## Passo no `.iflw`

Ver `processors.md` → Groovy Script. O arquivo vai em `src/main/resources/script/`.
