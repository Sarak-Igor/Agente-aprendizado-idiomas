# Plano de Implementação Detalhado: Fábrica de Agentes MCP

Este documento consolida a arquitetura técnica, decisões de design e o roteiro passo-a-passo para a construção da Fábrica de Agentes Autônomos.

---

## 1. Arquitetura e Modularidade

O sistema evolui de um "Assistente de Idiomas" para uma **Plataforma de Orquestração de Agentes**. Para isso, definimos dois novos domínios core:

### 1.1 `integrations_hub` (Hub de Integração)
*   Responsável pela gestão de ferramentas externas (MCP).
*   Manutenção do registro de ferramentas (`tools_registry.json`).
*   Gerenciamento de processos de instalação (`npm/pip`) e execução de servidores MCP.

### 1.2 `agents_factory` (Fábrica de Agentes)
*   Responsável pela criação, edição, persistência e execução dos agentes.
*   Gerencia o ciclo de vida do "Blueprint" (o desenho do fluxo).
*   Orquestra a execução dos nós (Motor de Execução).

---

## 2. Estratégia de Dados: Isolamento Total

Para garantir que cada agente seja portável, seguro e independente, adotamos uma estratégia de isolamento rigoroso. Não existe um "banco de dados gigante" misturando dados de todos os agentes.

### 2.1 Estrutura de Arquivos
Cada agente reside em seu próprio diretório em `storage/agents/{agent_uuid}/`:

*   📄 **`blueprint.json`**: O "código-fonte" do agente. Define nós, conexões e configurações. Compatível com formato n8n.
*   🔒 **`config.env`**: Variáveis de ambiente sensíveis (API Keys, Tokens) exclusivas deste agente.
*   🧠 **`memory.sqlite`**: Banco de dados relacional e vetorial (via extensão ou arquivo separado) dedicado. Armazena apenas as memórias deste agente.
*   📝 **`run_logs/`**: Histórico detalhado de cada execução.

### 2.2 Decisão de Design
*   **O Sistema:** Mantém apenas metadados leves (`id`, `nome`, `caminho_storage`, `versão_atual`) para listar os agentes na dashboard.
*   **O Agente:** É autocontido. Se você copiar a pasta do agente para outro servidor, ele deve funcionar (desde que o runtime esteja instalado).

---

## 3. Motor de Execução (Execution Engine)

O backend não é apenas uma API CRUD; ele é um **Runner** que interpreta o `blueprint.json`.

### 3.1 Fluxo de Execução (`POST /api/v1/run/{agent_id}`)
1.  **Loader:** O processo worker carrega o `blueprint.json` e as variáveis de `config.env`.
2.  **Tool Initialization:** O Runner verifica as ferramentas listadas no blueprint.
    *   Inicia os servidores MCP necessários (ex: `mcp-server-stripe`).
    *   Estabelece conexões via stdio/SSE.
3.  **Graph Traversal:** O Runner percorre os nós definidos no JSON:
    *   **Trigger:** Recebe o input inicial.
    *   **Logic:** Avalia condições (`if input contains 'error'`).
    *   **Brain:** Monta o contexto, injeta as ferramentas ativas e chama a LLM.
    *   **Tool:** Executa uma ação direta se necessário.
4.  **Output:** Retorna o resultado final e persiste os logs na pasta do agente.

---

## 4. Ecossistema de Ferramentas e Templates

O poder do sistema reside na sua extensibilidade.

### 4.1 Registro de Ferramentas Dinâmico
*   **Built-in Registry:** Lista curada de ferramentas (Google Drive, Slack, GitHub).
*   **Custom Tools (Instalação Assistida):**
    *   O usuário pode solicitar via Chat: *"Instale uma ferramenta para manipular PDFs"*.
    *   O Sistema busca no NPM/PyPI ou sugere repositórios MCP compatíveis.
    *   **Ação de Instalação:** O sistema executa `npx` ou `pip` em um ambiente controlado para disponibilizar a ferramenta.

### 4.2 Biblioteca de Templates
*   Agentes pré-configurados para casos de uso comuns (Vendas, Suporte, Pesquisa).
*   Interface "One-Click Load" que substitui o blueprint atual pelo template.

---

## 5. O Arquiteto (Chat Builder Generativo)

O chat lateral deixa de ser passivo e torna-se um construtor ativo do fluxo.

### 5.1 Permissões e Segurança (Sandbox)
Para garantir a integridade do sistema, o Agente Arquiteto opera em uma **Sandbox Lógica**:
*   ✅ **Pode:** Adicionar nós, criar conexões, editar configurações do agente *atual*.
*   ✅ **Pode:** Instalar ferramentas *neste* agente.
*   🚫 **NÃO PODE:** Acessar arquivos fora da pasta do agente, alterar configurações do sistema global, ou modificar outros agentes.

### 5.2 Protocolo de Ação
O Arquiteto não "edita o código" diretamente. Ele emite **Intenções Estruturadas** que o Frontend valida e aplica:

```json
// Resposta do Arquiteto
{
  "message": "Adicionei um nó de verificação de e-mail e instalei a ferramenta do Gmail.",
  "actions": [
    { "type": "INSTALL_TOOL", "tool": "mcp-server-gmail" },
    { "type": "ADD_NODE", "node": { "type": "brain", "label": "Verificador de Email" } },
    { "type": "CONNECT", "from": "trigger", "to": "node-verificador" }
  ]
}
```

---

## 6. Roteiro de Implementação (Roadmap)

### ✅ Fase 1-6 (Concluídas)
*   Infraestrutura básica e UI do Canvas.
*   Sistema de Nós (Brain, Tool, Logic, Trigger).
*   Conexões visuais e manipulação (Drag & Drop, Remoção).
*   Exportação n8n e configurações locais.

### ✅ Fase 7: Backend Runner & Isolamento (Concluída)
1.  ✅ Implementar `AgentService` (AgentStorageService) para criar diretórios isolados.
2.  ✅ Implementar API para Salvar/Carregar `blueprint.json`.
3.  ✅ Criar `BlueprintRunner` para interpretar e executar o JSON.
4.  ✅ Configurar banco de dados SQLite individual (AgentDBService).

### ✅ Fase 8: Ferramentas Dinâmicas (Concluída)
1.  ✅ Criar `ToolManager` para gerenciar `package.json` do agente (Registro e Seed).
2.  ✅ Implementar API de "Custom Tool" e "Templates Load".
3.  ✅ Integrar busca de ferramentas (Via API, pronta para consumo do Chat).

### 🚧 Fase 9: Chat Builder (Generative UI - Em andamento)
1.  ✅ Refatorar prompt do sistema para focar em "Action Generation" (Estrutura JSON).
2.  Implementar middleware de segurança para validar escopo das ações.
3.  Implementar interpretador de ações no Frontend (React).

---
**Observação:** Este plano é vivo e deve ser atualizado conforme novas descobertas técnicas surgirem durante a implementação do Backend Runner.
