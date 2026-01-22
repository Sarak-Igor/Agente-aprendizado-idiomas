# Modularidade do Sistema

O sistema segue uma arquitetura modular dividida em domínios de responsabilidade, garantindo escalabilidade, facilidade de manutenção e reuso de componentes.

### 1. `core_llm` (Infraestrutura)
Responsável por toda a interface técnica com provedores de IA. É 100% agnóstico ao domínio de ensino de idiomas.
- **Função:** Orquestrar chamadas para Gemini, OpenRouter e Groq, gerenciar catálogo de modelos e monitorar uso de tokens.

### 2. `user_intelligence` (Inteligência Central)
Gerencia o estado, a memória e o perfil do usuário de forma genérica.
- **Função:** Persistir sessões de chat, histórico de mensagens e evolução do perfil do usuário através de múltiplos contextos.

### 3. `language_learning` (Domínio da Aplicação)
Contém toda a lógica de negócio específica para o aprendizado de idiomas.
- **Função:** Definir personificações de professores, gerenciar serviços de tradução externa, analisar erros gramaticais e processar conteúdo didático (YouTube).

### 4. `workflow_engine` (Orquestração de Processos)
Motor de execução que encadeia tarefas complexas entre os outros módulos.
- **Função:** Coordenar fluxos multi-etapas, como o recebimento de uma mensagem, sua tradução/análise interna e a geração de uma resposta contextualizada.
