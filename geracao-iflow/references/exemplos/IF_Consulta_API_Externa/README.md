# Exemplo: IF_Consulta_API_Externa

Padrão A de `padroes-fluxo.md` (default de toda API GET):  
`GET /http/consulta-cliente?customerId=123&from=2025-01-01`  
consulta `{{Externo_URL}}/customers/123?from=2025-01-01` e devolve o JSON da API.  
Sem body no GET; sem path extra tipo `/consulta-cliente/123`.

Passos:

1. Definir parâmetros obrigatórios — Content Modifier (`p_requiredParams` = `{{Required_Params}}`)
2. Ler parâmetros da query — Groovy `ReadQueryParams.groovy` (**obrigatório em GET**;
   não há processor que divida `CamelHttpQuery` em properties)
3. Montar request para API — Content Modifier (`Accept: application/json`)
4. Consultar API externa — Request Reply + HTTP receiver
5. Definir resposta — Content Modifier (`Content-Type`, `CamelHttpResponseCode` 200)
6. Exception Subprocess — Groovy `GravarResponseErro.groovy` + Content Modifier
   (HTTP 400, `{"message":"${property.responseErro}"}`, sem Router)

Parâmetros: `Sender_Path`, `Required_Params`, `Externo_URL`, `Externo_Credential`,
`Request_Timeout`.

Esta pasta guarda só o que é específico do exemplo (`.iflw`, `parameters.prop`, `parameters.propdef`).
Os arquivos base (`.project`, `metainfo.prop`, `META-INF/MANIFEST.MF`, script) vêm de `templates/`.
Para montar o projeto completo, validar e empacotar (a partir da raiz da skill):

```bash
python3 scripts/scaffold_iflow.py --id IF_Consulta_API_Externa --name "IF Consulta API Externa" \
  --description "Consulta cliente em API externa" --out /tmp/iflows --with-query-script
cp -r references/exemplos/IF_Consulta_API_Externa/src /tmp/iflows/IF_Consulta_API_Externa/
python3 scripts/validate_iflow.py /tmp/iflows/IF_Consulta_API_Externa
python3 scripts/package_iflow.py /tmp/iflows/IF_Consulta_API_Externa --out /tmp/iflows/IF_Consulta_API_Externa.zip
```

Resultado esperado: `0 erro(s), 1 aviso(s)` (o aviso lista o Groovy para confirmação).
