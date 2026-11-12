# Estrutura do pacote de um iFlow

O artefato importado no Integration Suite é um `.zip` cujo conteúdo é um projeto Eclipse/OSGi.
O zip **não** tem pasta raiz: os arquivos abaixo ficam na raiz do zip.

```
<Nome>.zip
├── .project                                  obrigatório. Descritor Eclipse com as natures do iFlow.
├── metainfo.prop                             obrigatório. Descrição do artefato.
├── META-INF/
│   └── MANIFEST.MF                           obrigatório. Bundle OSGi (nome, id, versão, imports).
└── src/main/resources/
    ├── parameters.prop                       obrigatório. Valores dos parâmetros externalizados.
    ├── parameters.propdef                    obrigatório. Definição (tipo, obrigatoriedade) dos parâmetros.
    ├── scenarioflows/integrationflow/
    │   └── <Nome>.iflw                       obrigatório. O fluxo em si (BPMN2 + extensões ifl).
    ├── script/
    │   └── *.groovy | *.js                   scripts referenciados por passos Script.
    ├── mapping/
    │   └── *.mmap                            Message Mappings.
    ├── xsd/
    │   └── *.xsd                             esquemas de origem/destino de mapeamento.
    ├── wsdl/
    │   └── *.wsdl                            WSDL de serviços SOAP (lado SAP de um mapping / adapter SOAP).
    ├── xsl/
    │   └── *.xsl | *.xslt                    XSLT Mappings.
    ├── edmx/
    │   └── *.edmx                            metadata OData (gerado pelo wizard do adapter OData).
    ├── scenarioflows/                         (outros fluxos locais não são usados aqui)
    └── mapping/ … opmap/                      Operation Mapping (raro).
```

Regras:

- Só um `.iflw` por pacote, e o nome do arquivo igual ao `Bundle-SymbolicName`.
- Nomes de arquivo sem espaço, sem acento. O designer referencia os arquivos por caminho relativo
  a `src/main/resources/`.
- Pastas vazias não são necessárias; crie só as que têm conteúdo.
- Codificação UTF-8 em tudo. Quebras de linha `\n`.

## Arquivos obrigatórios

### `.project`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
	<name>__IFLOW_ID__</name>
	<comment></comment>
	<projects>
	</projects>
	<buildSpec>
		<buildCommand>
			<name>org.eclipse.jdt.core.javabuilder</name>
			<arguments>
			</arguments>
		</buildCommand>
	</buildSpec>
	<natures>
		<nature>org.eclipse.jdt.core.javanature</nature>
		<nature>com.sap.ide.ifl.project.support.project.nature</nature>
		<nature>com.sap.ide.ifl.bsn</nature>
	</natures>
</projectDescription>
```

### `metainfo.prop`

```
#Store metainfo properties
#Wed Oct 22 00:00:00 UTC 2026
description=__DESCRIPTION__
```

### `META-INF/MANIFEST.MF`

O arquivo está em `templates/META-INF/MANIFEST.MF`. Os campos a trocar:

| Campo | Valor |
|---|---|
| `Bundle-Name` | Nome legível (pode ter espaço). Aparece no pacote. |
| `Bundle-SymbolicName` | Id técnico, `; singleton:=true` no fim. Sem espaço/acento. |
| `Origin-Bundle-Name` / `Origin-Bundle-SymbolicName` | Mesmos valores acima. |
| `Bundle-Version` | `1.0.0` na primeira entrega. |
| `SAP-BundleType` | `IntegrationFlow` (fixo). |
| `SAP-NodeType` | `IFLMAP` (fixo). |
| `SAP-RuntimeProfile` | `iflmap` (fixo). |
| `Import-Package` / `Import-Service` | Manter como no template. Linhas de continuação começam com um espaço. |

Formato MANIFEST: linhas com no máximo 72 bytes; continuação em linha seguinte iniciada com um
espaço; arquivo termina com linha em branco.

### `src/main/resources/parameters.propdef`

Define cada parâmetro externalizado usado no `.iflw` como `{{Nome}}`.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<parameters>
  <param_references/>
  <param id="Receiver_URL" isRequired="true" allowedValues="" description="URL base da API externa" isHidden="false">
    <type>xsd:string</type>
    <value>https://api.exemplo.com/v1</value>
  </param>
  <param id="Receiver_Credential" isRequired="true" allowedValues="" description="Nome da credencial (Security Material)" isHidden="false">
    <type>xsd:string</type>
    <value>CRED_API_EXEMPLO</value>
  </param>
  <param id="Request_Timeout" isRequired="false" allowedValues="" description="Timeout da chamada em ms" isHidden="false">
    <type>xsd:integer</type>
    <value>60000</value>
  </param>
</parameters>
```

Tipos aceitos: `xsd:string`, `xsd:integer`, `xsd:boolean`. `allowedValues` aceita lista separada
por `|` para virar dropdown na aba Configure (ex.: `GET|POST`).

### `src/main/resources/parameters.prop`

Valor padrão de cada parâmetro, formato Java properties. Deve conter exatamente os mesmos ids do
`.propdef`.

```
#Wed Oct 22 00:00:00 UTC 2026
Receiver_URL=https\://api.exemplo.com/v1
Receiver_Credential=CRED_API_EXEMPLO
Request_Timeout=60000
```

Atenção ao escape: `:` em properties Java vira `\:` quando aparece na chave; no valor o escape é
opcional mas o designer exporta com `\:`. O validador aceita os dois.

### `src/main/resources/scenarioflows/integrationflow/<Nome>.iflw`

Ver `iflw-xml.md`.

## Extensões e para que servem

| Extensão | Conteúdo | Referenciado por |
|---|---|---|
| `.iflw` | BPMN2 XML com namespace `ifl` para propriedades SAP | pacote |
| `.groovy` | Groovy Script; função `Message processData(Message message)` | passo Script, property `script` |
| `.js` | JavaScript (Nashorn/GraalJS). Evitar; Groovy é o padrão | passo Script |
| `.mmap` | Message Mapping (XML proprietário do designer) | passo Message Mapping, `mappingpath` |
| `.xsd` | XML Schema. Origem/destino de mapping | `.mmap` |
| `.wsdl` | WSDL. Destino de mapping e definição do adapter SOAP | `.mmap`, adapter SOAP `wsdlURL` |
| `.xsl`/`.xslt` | XSLT 2.0/3.0 (Saxon) | passo XSLT Mapping, `mappingpath` |
| `.edmx` | Metadata OData V2/V4 | adapter OData, mapping |
| `.prop`/`.propdef` | Parâmetros externalizados | aba Configure |

## Nome do zip

`<Bundle-SymbolicName>.zip`. O Integration Suite aceita qualquer nome, mas o padrão evita confusão
ao versionar.
