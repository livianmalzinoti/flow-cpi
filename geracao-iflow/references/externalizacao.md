# Externalização de parâmetros

Parâmetro externalizado é o que aparece na aba **Configure** do iFlow no Integration Suite. É o
único jeito de o desenvolvedor ajustar URL, credencial, caminho ou timeout em DEV/QAS/PRD sem
editar e re-salvar o fluxo. Externalizar só metade das URLs é pior do que não externalizar: o
desenvolvedor acha que configurou tudo e a outra metade continua apontando para o ambiente errado.

## Regra

Toda configuração que **pode variar entre ambientes ou com o tempo** é `{{Nome}}`:

| Sempre externalizar | Nunca externalizar |
|---|---|
| URL/host/endereço de qualquer receiver (`httpAddressWithoutQuery`, `address`, `host`) | Senhas, tokens, client secrets (ficam no Security Material; só o **nome** da credencial é externalizado) |
| Nome da credencial (`credentialName`), alias de certificado, `locationId` do Cloud Connector | `activityType`, `componentVersion`, `cmdVariantUri` |
| Caminho do sender (`urlPath`, `address` do ProcessDirect) | Nomes de headers/properties técnicos |
| Timeout (`httpRequestTimeout`, `requestTimeout`) | Expressões Camel e XPath |
| Página/tamanho de lote (`pageSize`), nome de fila, diretório SFTP, padrão de arquivo | Caminhos internos do pacote (`script`, `mappingpath`, `wsdlURL`) |
| Endereço ProcessDirect de receiver | |
| Valores funcionais que o negócio pode mudar: código de empresa, tipo de documento, e-mail de alerta, flag de simulação | |

Valores dentro de Content Modifier (`Type` `constant`) também aceitam `{{Param}}`. É assim que um
header fixo como `apikey` ou um código de empresa vira configurável.

## Sintaxe

- No `.iflw`: `{{Nome_Do_Parametro}}`. Pode aparecer sozinho ou dentro de texto:
  `{{Receiver_URL}}/v2/orders`.
- Nome: `PascalCase_Com_Underscore`, prefixo pelo sistema ou papel:
  `Sender_Path`, `SAP_Endpoint`, `SAP_Credential`, `Externo_URL`, `Externo_Credential`,
  `Request_Timeout`, `OData_PageSize`, `PD_Auditoria_Address`.
- Sem acento, sem espaço, sem hífen.

## Declaração

Todo parâmetro usado precisa existir em dois arquivos (`estrutura-pacote.md`):

- `src/main/resources/parameters.propdef`: id, tipo, obrigatório, descrição, valor padrão.
- `src/main/resources/parameters.prop`: valor padrão (o que aparece preenchido na aba Configure).

Os dois têm que ter exatamente o mesmo conjunto de ids. O validador falha se:

- um `{{X}}` do `.iflw` não está no `.propdef`;
- um id do `.propdef` não está no `.prop` (ou vice-versa);
- um adapter receiver tem `http://`/`https://` ou `credentialName` fixo.

E avisa quando um parâmetro está declarado e não é usado.

## Descrição do parâmetro

O campo `description` do `.propdef` aparece como tooltip na aba Configure. Escrever o que é e de
onde vem o valor: `URL base da API de pedidos (ex.: https://api.cliente.com/v1)`,
`Nome da credencial User Credentials cadastrada em Security Material`.

## Aba Configure na entrega

Na mensagem final, listar os parâmetros em tabela: nome, o que é, valor padrão, onde obter o valor
em cada ambiente. É a lista que o desenvolvedor segue ao implantar.
