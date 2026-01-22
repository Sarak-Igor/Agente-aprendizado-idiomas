# Mapa de Navegação do Sistema (Backend)

Este guia ajuda a localizar rapidamente as responsabilidades e arquivos principais do backend.

## 🗺️ Visão Estrutural (`backend/app/modules/`)

### 1. `core_llm`
Localização: `app/modules/core_llm/`
- `models/models.py`: Catálogo de modelos (`ModelCatalog`), Tokens (`TokenUsage`), Keys (`ApiKey`).
- `services/orchestrator/`: Conectores para Gemini, OpenRouter, Groq.
- `services/catalog_service.py`: Sincronização automática com LMSYS Arena.
- `api/`: Rotas para gerenciamento técnico de modelos e uso.

### 2. `user_intelligence`
Localização: `app/modules/user_intelligence/`
- `models/models.py`: Perfil do Usuário (`UserProfile`), Sessões (`ChatSession`), Mensagens (`ChatMessage`).
- `services/chat_service.py`: Gerenciamento de persistência e histórico de conversas.
- `services/chat_router.py`: Lógica inteligente para escolha do melhor modelo para cada sessão.

### 3. `language_learning`
Localização: `app/modules/language_learning/`
- `providers/professor.py`: O "Cérebro" pedagógico (Prompts e regras de feedback).
- `services/translation/`: Fábrica de tradutores e adaptadores (Google, Argos, Libre).
- `services/message_analyzer.py`: Avaliação gramatical e de vocabulário.
- `services/youtube_service.py`: Processamento de URLs e legendas do YouTube.
- `api/`: Rotas de `practice.py` (Treino) e `video.py` (Tradução de vídeo).

### 4. `workflow_engine`
Localização: `app/modules/workflow_engine/`
- `services/base.py`: Classe base para orquestradores.
- `services/chat_workflow.py`: O fluxo principal da aplicação (Mensagem -> Processamento -> Resposta).
- `services/engine.py`: Registro centralizado de workflows.

---

## 🛠️ Pontos de Entrada Comuns

- **Adicionar novo Modelo/IA:** Modificar `core_llm/services/orchestrator/`.
- **Mudar comportamento do Professor:** Modificar `language_learning/providers/professor.py`.
- **Alterar fluxo de uma Mensagem:** Modificar `workflow_engine/services/chat_workflow.py`.
- **Novo serviço de Tradução:** Adicionar em `language_learning/services/` e registrar em `translation_factory.py`.

## 🗃️ Banco de Dados
- Todos os modelos estão centralizados/importados em `app/models/database.py` para compatibilidade com migrations (Alembic).
- Configurações de conexão em `app/database.py`.
