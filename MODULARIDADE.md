# Diretrizes de Modularidade e Qualidade

Este documento define as regras fundamentais para a manutenção e evolução da arquitetura do projeto. Qualquer nova implementação deve seguir rigorosamente estas diretrizes.

## 1. Os 4 Pilares da Arquitetura

O sistema é dividido em domínios isolados. Jamais misture lógicas de domínio diferentes em um único módulo.

- **`core_llm` (Infraestrutura)**: Camada puramente técnica para interação com IAs.
  - *Regra:* Proibido referências a "idiomas", "alunos" ou "professores". Deve ser 100% agnóstico.
- **`user_intelligence` (Cérebro)**: Gestão de perfil e memória de interações.
  - *Regra:* Foca em persistência e inteligência de usuário genérica.
- **`language_learning` (Domínio)**: Regras de negócio do app de idiomas.
  - *Regra:* Aqui reside a "personalidade" do sistema.
- **`workflow_engine` (Orquestração)**: Onde a mágica acontece sem poluir os serviços.
  - *Regra:* Serviços básicos (CRUD) não devem conter fluxos complexos. Use Workflows.

---

## 2. Regras de Ouro para Desenvolvimento (AI Principles)

### 2.1. Independência Total (Agnosticismo)
O núcleo (`core_llm`) deve funcionar em qualquer projeto (ex: suporte, vendas, jogos). Se você precisar de uma funcionalidade LLM que dependa de uma regra de idioma, ela deve ser injetada via interface ou fornecida pelo módulo de domínio.

### 2.2. Proibição de Dependências Circulares
Um módulo não pode depender de outro que dependa dele. 
- Fluxo correto: `Workflow` -> `Serviços` -> `Core/Models`.
- Jamais faça: `core_llm` importar algo de `language_learning`.

### 2.3. Separação de Preocupações (SoC)
- **Modelos:** Apenas definições de dados (SQLAlchemy/Pydantic). Sem lógica de negócio.
- **Serviços:** Lógica atômica e persistência.
- **Workflows:** Orquestração de múltiplos serviços.
- **Routes:** Apenas entrada/saída de dados e validação de permissões.

### 2.4. Injeção de Dependência
Sempre que um serviço de nível inferior precisar de uma regra de nível superior, use injeção de dependência no construtor. Não use imports diretos para "subir" na hierarquia de módulos.

### 2.5. Código Autodocumentado
- Use nomes significativos (ex: `normalize_for_storage` em vez de `clean_text`).
- Guard Clauses no início das funções para evitar aninhamento excessivo.

---

## 3. Protocolo para a IDE/Agente

Ao modificar este projeto, você **DEVE**:
1. Verificar se a funcionalidade pertence ao módulo correto.
2. Manter serviços leves e delegar orquestrações complexas ao `workflow_engine`.
3. Proativamente remover código morto ou redundante ao refatorar.
4. Seguir o padrão de nomes existente (Snake Case para funções, Pascal Case para Classes).

> [!IMPORTANT]
> A modularização não é apenas organização, é a defesa contra o débito técnico. Se quebrar a modularidade, você quebra a manutenibilidade do sistema.
