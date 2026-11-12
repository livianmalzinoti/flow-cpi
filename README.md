# FLOW CPI — instalação e uso em qualquer plataforma

Guia para instalar e usar o **agent FLOW CPI** e a skill **geracao-iflow** em Cursor, Claude Code, Codex, OpenCode, Gemini CLI, VS Code Copilot e equivalentes.

O FLOW CPI gera **Integration Flows (iFlow)** para **SAP Cloud Integration / SAP Integration Suite**: conversa → proposta → pacote `.zip` validado para upload em um Integration Package.

---

## O que você precisa

| Item | Detalhe |
|---|---|
| Python | 3.10+ no `PATH` (`python` ou `python3`) |
| Pacote FLOW CPI | Pasta com o **prompt do agent** + a skill **geracao-iflow** |
| Rede | Acesso a [help.sap.com (Cloud Integration)](https://help.sap.com/docs/cloud-integration/sap-cloud-integration/) e, se possível, SAP Business Accelerator Hub / SAP Docs |
| Tenant CPI | Versões *About*: Cloud Integration + Runtime (o agent pede na 1ª mensagem) |

Não há dependência de npm/Java para gerar o zip. Os scripts usam apenas a biblioteca padrão do Python.

---

## Conteúdo do pacote

Estrutura mínima (nomes podem variar um pouco conforme o zip/pasta que você recebeu):

```text
flow-cpi/
├── prompt/
│   └── flow-cpi.md          # persona + protocolo do agent
└── geracao-iflow/           # skill (fonte da verdade)
    ├── SKILL.md
    ├── references/          # processors, adapters, padrões, entrega…
    ├── scripts/
    │   ├── generate_iflow.py
    │   ├── validate_iflow.py
    │   ├── package_iflow.py
    │   ├── scaffold_iflow.py
    │   └── iflw_builder.py
    └── templates/           # esqueleto do pacote iFlow + specs de exemplo
```

No **Cursor** instalado neste ambiente, os caminhos costumam ser:

- Agent: `~/.cursor/agents/flow-cpi.md` (Windows: `%USERPROFILE%\.cursor\agents\flow-cpi.md`)
- Skill: `~/.cursor/skills/geracao-iflow/`

Em outras plataformas, o importante é: o modelo **carrega o prompt** e consegue **ler a pasta da skill** (e rodar os scripts Python).

---

## Instalação por plataforma

### 1) Cursor

1. Copie `prompt/flow-cpi.md` para:
   - `%USERPROFILE%\.cursor\agents\flow-cpi.md` (Windows)
   - `~/.cursor/agents/flow-cpi.md` (macOS/Linux)
2. Copie a pasta `geracao-iflow/` para:
   - `%USERPROFILE%\.cursor\skills\geracao-iflow\`
   - `~/.cursor/skills/geracao-iflow/`
3. Abra o arquivo do agent e ajuste a linha **Raiz da skill** para o caminho absoluto real, por exemplo:
   ```text
   Raiz da skill: C:\Users\<voce>\.cursor\skills\geracao-iflow\
   ```
   ou, em macOS/Linux:
   ```text
   Raiz da skill: /Users/<voce>/.cursor/skills/geracao-iflow/
   ```
4. Reinicie o chat / Agent se necessário.
5. Inicie com `/flow-cpi` ou mencione “FLOW CPI” / “gerar iFlow CPI”.

O Cursor descobre agents em `.cursor/agents` e skills em `.cursor/skills` (frontmatter `name` / `description` no `SKILL.md`).

### 2) Claude Code (Anthropic)

1. Coloque a skill onde o Claude Code carrega skills do projeto ou do usuário, por exemplo:
   - `.claude/skills/geracao-iflow/` no repositório, **ou**
   - o diretório de skills do usuário da sua versão do Claude Code
2. Use o conteúdo de `prompt/flow-cpi.md` como:
   - **Custom instructions** / system prompt do projeto, **ou**
   - um agent/subcommand que aponte para essa skill
3. No prompt, fixe a raiz absoluta da skill.
4. Garanta que o agente pode executar shell (`python scripts/generate_iflow.py ...`) no diretório da skill.

### 3) OpenAI Codex (CLI / IDE)

1. Copie `geracao-iflow/` para o workspace (ex.: `skills/geracao-iflow/`).
2. Inclua `prompt/flow-cpi.md` nas instruções do agent (AGENTS.md, project instructions, ou system prompt da sessão).
3. Atualize “Raiz da skill” para o caminho no workspace.
4. Permita execução de comandos Python no sandbox/host.

### 4) OpenCode / outros CLIs de coding agent

Padrão genérico:

1. **System / agent prompt** = conteúdo de `prompt/flow-cpi.md` (com caminho da skill corrigido).
2. **Skill on disk** = pasta `geracao-iflow/` acessível por leitura de arquivos.
3. **Tools** necessários:
   - ler/escrever arquivos
   - terminal (Python)
   - busca web / fetch (Help SAP + Accelerator Hub) — o protocolo exige pesquisa antes de propor
4. Opcional: MCP SAP Docs, se a plataforma tiver e estiver autenticado.

### 5) VS Code Copilot / ChatGPT custom GPT / similares

- **Custom GPT / Agent**: cole o prompt FLOW CPI nas instructions; anexe ou hospede a skill como knowledge **e** mantenha os `scripts/` locais para geração real do zip (só knowledge sem scripts não empacota iFlow).
- **Copilot Chat com agent mode**: abra o workspace que contém `geracao-iflow/` e referencie o prompt nas instruções do repositório (`.github/copilot-instructions.md` ou equivalente).

---

## Configuração obrigatória do prompt

Antes do primeiro uso, edite o agent e confira:

1. **Raiz da skill** — caminho absoluto válido na máquina alvo.
2. Idioma — o FLOW CPI responde em **português**.
3. Escopo — só CPI / Integration Suite / iFlow; fora disso (ABAP, NiFi, etc.) deve recusar e redirecionar.

Trecho típico a ajustar:

```markdown
Raiz da skill: <CAMINHO_ABSOLUTO>/geracao-iflow/
```

---

## Como usar (fluxo da conversa)

O agent segue esta ordem; não pule etapas:

1. **Versão do tenant**  
   No Integration Suite: *About* → informe **Cloud Integration** e **Runtime**.
2. **Documentação funcional** (ou equivalente): sender, método, payload, destino, auth, erros.
3. **Pesquisa** (obrigatória no protocolo atual):
   - SAP Business Accelerator Hub / SAP Docs (contrato da API)
   - [SAP Cloud Integration Help](https://help.sap.com/docs/cloud-integration/sap-cloud-integration/) (Router, Content Modifier, JSON to XML, adapters)
4. **Proposta** (tabela de passos + params + Exception Subprocess) → só gera após o seu **ok**.
5. **Geração** do zip (via `generate_iflow.py` quando o padrão couber).
6. **Entrega** do caminho do `.zip` + parâmetros da aba Configure.

Exemplo de abertura:

```text
/flow-cpi
```

Depois:

```text
Cloud Integration 6.84.77
Runtime 8.48.27
```

Em seguida cole a documentação ou descreva o fluxo (GET/POST, URL, campos, auth).

---

## Geração manual dos scripts (sem o chat)

Útil para CI ou para validar um projeto já existente:

```bash
cd geracao-iflow

# A partir de uma spec JSON (ver templates/specs/)
python scripts/generate_iflow.py --spec caminho/para/spec.json --force

# Ou validar / empacotar um projeto já montado
python scripts/validate_iflow.py /caminho/do/projeto/IF_MeuFluxo
python scripts/package_iflow.py /caminho/do/projeto/IF_MeuFluxo --out /caminho/IF_MeuFluxo.zip
```

`generate_iflow.py` (com spec suportada) faz scaffold + `.iflw` + parâmetros + validate + zip no mesmo processo.

Nunca entregue zip com erros de `validate_iflow.py`.

---

## Regras que o agent (e a skill) devem respeitar

Resumo operacional (detalhes em `SKILL.md` e `references/`):

- Processor nativo primeiro; Groovy só com motivo (`ReadQueryParams`, `GravarResponseErro`, ou justificativa explícita).
- Externalizar URL, path, credencial, timeout, etc. (`{{Param}}` + `.prop` / `.propdef`).
- Exchange Property Type `expression` → Datatype **`java.lang.String`** (inclui `p_bodyOriginal`).
- JSON to XML (CI 6.84+ alinhado ao designer): `additionalRootElementName=root`, `useNamespaces=true`, `addXMLRootElement=true`; XPath em `/root/...`. Não usar `useNamespaceMapping` no lugar de `useNamespaces`.
- Router NonXML: operadores **`and`** / **`or`** (nunca `&&` / `||`). Comparar `${property.Campo}`.
- Exception Subprocess: Error Start → Groovy `responseErro` → CM HTTP 400 JSON → End Message **1.0**.
- Sandbox do API Business Accelerator Hub costuma ser **só GET**; POST/create em geral exige tenant S/4 real (+ CSRF quando aplicável).

---

## Checklist pós-instalação

- [ ] `python --version` ≥ 3.10  
- [ ] Pasta `geracao-iflow/SKILL.md` legível pelo agent  
- [ ] `prompt/flow-cpi.md` (ou `agents/flow-cpi.md`) com **Raiz da skill** correta  
- [ ] Agent consegue rodar `python scripts/validate_iflow.py --help` (ou o script sem erro de path)  
- [ ] Fetch/search habilitados para Help SAP  
- [ ] Teste: iniciar o agent → ele pede **Cloud Integration** e **Runtime** antes de desenhar  

---

## Solução rápida de problemas

| Sintoma | O que verificar |
|---|---|
| Agent não aparece (`/flow-cpi`) | Arquivo em `agents/` com frontmatter `name: flow-cpi`; reiniciar IDE |
| Gera proposta sem pedir versão | Prompt incompleto ou skill não carregada |
| `ModuleNotFound` / script não acha templates | Rodar os scripts com cwd = raiz de `geracao-iflow` |
| `Content is not allowed in prolog` no XPath | JSON to XML não converteu: `useNamespaces=true`, raiz `root`, XPath `/root/...` |
| `Token '&&' not supported` | Router NonXML deve usar `and` / `or` |
| Upload “Invalid artifact” | Empacotar com `package_iflow.py`; `MANIFEST.MF` em `META-INF/` |
| HTTP 405 no Sandbox em POST | Sandbox Hub costuma bloquear create; use S/4 real |

---

## Atualizar o pacote

1. Substitua `prompt/flow-cpi.md` e a pasta `geracao-iflow/` pela versão nova.  
2. Confira de novo a **Raiz da skill** no agent.  
3. Não misture `scripts/` antigos com `references/` novas.  
4. Em Cursor: sobrescreva `.cursor/agents/flow-cpi.md` e `.cursor/skills/geracao-iflow/`.

---

## Licença / uso

Uso interno para geração de artefatos SAP Cloud Integration. Revise o iFlow no Integration Suite (Configure, Deploy, teste) antes de produção. O agent acelera o desenho; a responsabilidade do deploy e dos dados sensíveis (API Key, credenciais) é do time.

---

## Referências

- Skill: `geracao-iflow/SKILL.md`  
- Prompt do agent: `prompt/flow-cpi.md`  
- Help CPI: https://help.sap.com/docs/cloud-integration/sap-cloud-integration/  
- Define Router: https://help.sap.com/docs/cloud-integration/sap-cloud-integration/define-router  
- SAP Business Accelerator Hub: https://api.sap.com/  
