# Plano de Implementação: Plataforma de Agentes e Integrações

Este documento serve como a base central para a evolução do sistema de um assistente de idiomas para uma plataforma completa de criação de agentes IA e orquestração de fluxos.

## Diretrizes de Arquitetura
Seguindo o documento `MODULARIDADE.md`, as novas funcionalidades serão isoladas em dois novos domínios:
- **`integrations_hub`**: Gestão de MCP e ferramentas externas.
- **`agents_factory`**: Fábrica de agentes, gestão de memória vetorial e orquestração de fluxos.

---

## 1. Chat Inteligente (Agente Especialista "On-Demand")
**Objetivo:** Criar chats onde cada conversa é um "especialista" independente que mantém coerência total a longo prazo.

### Fase 1: Memória Semântica e Histórico Personalizado
- **Captura de Contexto:** O sistema deve extrair informações relevantes de cada interação para criar um perfil de memória único para aquela conversa.
- **Diferencial de Coerência:** Independente do modelo (LLM) selecionado, a coerência é mantida via injeção de contexto recuperado do histórico e do RAG específico do usuário.
- **Gerenciamento de Contexto:** Uso de um Agente de Background para filtrar "ruído" e salvar apenas o "conhecimento útil" no banco vetorial.

### Fase 2: RAG do Usuário e Banco Vetorial
- **Contexto Especialista via Prompt:** O "chip" base (ex: professor de idiomas) define a persona inicial.
- **RAG de Informações Específicas:** O usuário pode fornecer documentos ou bases de dados que alimentam o banco vetorial exclusivo daquela conversa.
- **Atualização Dinâmica:** O banco vetorial é atualizado conforme o chat evolui, garantindo que o especialista "aprenda" com o usuário.

---

## 2. Agentes com Ferramentas MCP (Ação e Integração)
**Objetivo:** Interface visual para conectar agentes a ferramentas através do Model Context Protocol.

### Fase 1: Central de Criação e Categorias
- **Catálogo MCP:** Exibição de categorias (Produtividade, Busca, Dev, etc.) com menu expansível para listar ferramentas.
- **Atributos da Ferramenta:** Cada ferramenta exibirá nome, custo (free/pago), categoria e método de integração.
- **Fluxo de Conexão:** 
    - Se download: fornecer link.
    - Se comando: executar via sistema (solicitando autorização `Turbo`).
    - Se API Key: exibir campo de entrada seguro (padrão `core_llm`).

### Fase 2: Interface Visual e Diagramação
- **Visualização Premium:** Desenho do agente centralizado com ícones de ferramentas conectadas via linhas (Diagrama).
- **Componentes Clicáveis:** 
    - Clicar no **Agente** abre a edição do Prompt e a seleção da LLM.
    - Clicar na **Ferramenta** abre a configuração específica do MCP.
- **Criação Guiada:** Botão "Novo Agente" que abre o fluxo de seleção de categorias e escrita do prompt.

---

## 3. Fluxo e Grafos (Multi-Agentes & Workflow)
**Objetivo:** Orquestração complexa onde múltiplos agentes cooperam.

### Fase 1: Construtor Assistido (The Architect)
- **Chat de Arquitetura:** Uma LLM inteligente interage com o usuário para entender a necessidade e sugerir a estrutura do fluxo.
- **Seleção de Framework:** Opções para LangChain, LangGraph, Agno, CrewAI ou seleção Automática baseada no problema.
- **Formulário de Fluxos Pré-Prontos:** Templates configuráveis para tarefas comuns (Blueprints).

### Fase 2: O "Quebra-Cabeça" de Scripts
- **Peças Pré-Montadas:** O sistema mantém blocos de código (scripts base) para funções comuns (pesquisa, revisão, formatação).
- **Montagem On-Demand:** Com poucos prompts, o sistema combina as peças certas para montar o grafo final, reduzindo a necessidade de codificação manual.

---

## Segurança e Performance
- **Armazenamento:** Credenciais de ferramentas seguem o mesmo padrão de segurança das API Keys do sistema.
- **Inteligência Multinível:** Uso de modelos robustos (Sonnet/GPT-4) para a fase de **Arquitetura/Design** e modelos rápidos (Flash/Mini) para a **Execução** dos agentes.

## Verificação e Qualidade
- **Diagrama de Fluxo:** Validação visual do grafo antes da ativação.
- **Simulador de Custos:** Estimativa de consumo de tokens com base nas ferramentas e modelos selecionados.
