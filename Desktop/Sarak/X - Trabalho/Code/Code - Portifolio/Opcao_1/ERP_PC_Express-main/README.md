Integrantes Big 5:
1) Lucca Phelipe Masini RM 564121
2) Luiz Henrique Poss RM562177
3) Luis Fernando de Oliveira Salgado RM 561401
4) Igor Paixão Sarak RM 563726
5) Bernardo Braga Perobeli RM 56246

# PC-Express - Sistema de Gerenciamento de Inventário

Um sistema completo de gerenciamento de inventário desenvolvido com FastAPI (backend) e React (frontend), oferecendo uma interface moderna e intuitiva para controle de estoque, fornecedores, alertas e insights de negócio.

## 🚀 Características

- **Dashboard Interativo**: Visualização em tempo real de métricas importantes
- **Gerenciamento de Produtos**: CRUD completo com categorização e controle de estoque
- **Fornecedores**: Cadastro e gerenciamento de parceiros comerciais
- **Alertas de Estoque**: Notificações automáticas para itens com estoque baixo
- **Pedidos de Compra**: Sistema completo de pedidos de reabastecimento
- **Insights de Negócio**: Análises e recomendações baseadas em dados
- **Reabastecimento Automático**: Sistema inteligente de sugestões de reabastecimento
- **Tema Escuro/Claro**: Interface adaptável com suporte a múltiplos temas
- **Internacionalização**: Suporte completo a português e inglês
- **Autenticação Segura**: Sistema de login com JWT

## 📋 Pré-requisitos

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Node.js 16+** - [Download](https://nodejs.org/)
- **npm** (incluído com Node.js)

> **💡 Dica:** O script de inicialização verifica automaticamente se estes pré-requisitos estão instalados.

## 🛠️ Instalação

### 1. Clone o repositório
```bash
git clone <url-do-repositorio>
cd PCexpress
```

### 2. Inicialização Automática (Recomendado)
```bash
.\start.bat
```

**O script fará automaticamente:**
- ✅ Verificação de pré-requisitos
- ✅ Criação do ambiente virtual Python
- ✅ Instalação de dependências
- ✅ Configuração do banco de dados
- ✅ Inicialização dos servidores

### 3. Configuração Manual (Opcional)

Se preferir configurar manualmente, siga os passos abaixo:

#### Backend
```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
Windows: .venv\\Scripts\\activate
Unix/macOS: source .venv/bin/activate

# Instalar dependências principais
pip install -r requirements.txt

# (Opcional) Instalar dependências de ML separadamente
pip install -r requirements-ml.txt

# Configurar banco
python scripts/setup_db.py
```

#### Frontend
```bash
cd frontend
npm install
cd ..
```

## 🚀 Executando o Projeto

### ⭐ **Inicialização Automática (Recomendado)**
```bash
.\start.bat
```

**O que o script faz automaticamente:**
- ✅ Verifica se Python e Node.js estão instalados
- ✅ Cria e ativa ambiente virtual Python
- ✅ Instala todas as dependências
- ✅ Configura banco de dados
- ✅ Inicia backend e frontend em janelas separadas

### ▶️ Como rodar com Docker (opcional)

Para validar a instalação de dependências em um ambiente isolado e rodar a API em container:

```bash
# Build da imagem (executar a partir da raiz do repositório)
docker build -t erp-pc-express:phase2-docker .

# Rodar container (exporá a porta 8000)
docker run --rm -p 8000:8000 erp-pc-express:phase2-docker

# Ou usando docker-compose
docker compose up --build

# Teste health (no host)
curl -i http://127.0.0.1:8000/health
```

As variáveis de ambiente podem ser passadas ao `docker run` com `-e VAR=value` ou definidas em um `.env` local.

### 🔧 **Execução Manual (Avançado)**

#### Terminal 1 - Backend
```bash
# Ative o ambiente virtual primeiro
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Execute o servidor FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

## 🌐 Acessando a Aplicação

Após a inicialização, acesse:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Documentação da API**: http://localhost:8000/docs

## 🔐 Credenciais Padrão

- **Email**: admin@pc-express.com
- **Senha**: admin123

## 🏗️ Arquitetura

### Backend
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Banco de Dados**: SQLite
- **Autenticação**: JWT com passlib[bcrypt]
- **Validação**: Pydantic

### Frontend
- **Framework**: React 18
- **UI Library**: Material-UI (MUI)
- **Build Tool**: Vite
- **Roteamento**: React Router DOM
- **Gráficos**: Recharts
- **Ícones**: Lucide React
- **Internacionalização**: React-i18next

## 📁 Estrutura do Projeto

```
PCexpress/
├── app/                    # Backend FastAPI
│   ├── routers/           # Rotas da API
│   ├── models.py          # Modelos do banco de dados
│   ├── schemas.py         # Schemas Pydantic
│   ├── auth.py            # Autenticação
│   ├── database.py        # Configuração do banco
│   └── main.py            # Aplicação principal
├── frontend/              # Frontend React
│   ├── src/
│   │   ├── components/    # Componentes React
│   │   ├── services/      # Serviços de API
│   │   ├── contexts/      # Contextos React
│   │   ├── locales/       # Arquivos de tradução
│   │   └── utils/         # Utilitários
│   ├── package.json
│   └── vite.config.js
├── scripts/               # Scripts de configuração
│   ├── setup_db.py        # Configuração inicial do banco
│   └── seed.py            # Dados de exemplo
├── requirements.txt       # Dependências Python (core)
├── requirements-ml.txt    # Dependências ML opcionais
├── requirements-dev.txt   # Dependências de desenvolvimento (opcional)
├── start.py              # Script de inicialização
└── README.md
```

## 🔧 Funcionalidades Principais

### Dashboard
- Métricas em tempo real
- Gráficos interativos
- Alertas de estoque
- Produtos em destaque

### Produtos
- Cadastro completo de produtos
- Controle de estoque
- Categorização
- Preços e códigos

### Fornecedores
- Cadastro de fornecedores
- Informações de contato
- Histórico de pedidos

### Alertas
- Monitoramento de estoque baixo
- Notificações automáticas
- Priorização de itens críticos

### Pedidos de Compra
- Criação de pedidos
- Acompanhamento de status
- Integração com fornecedores

### Insights
- Análises de vendas
- Recomendações de negócio
- Relatórios personalizados

### Reabastecimento Automático
- Sugestões inteligentes
- Cálculo de demanda
- Otimização de estoque

## 🎨 Temas e Personalização

O sistema suporta temas claro e escuro, com transições suaves e interface responsiva. Todos os componentes são adaptáveis e mantêm a consistência visual.

## 🌍 Internacionalização

O sistema oferece suporte completo a múltiplos idiomas:
- **Português**: Idioma nativo brasileiro
- **Inglês**: Idioma padrão do sistema
- **Seletor de Idioma**: Disponível na barra de navegação
- **Persistência**: Preferência salva automaticamente
- **Configurações**: Opção adicional no menu de configurações

Para mais detalhes sobre a implementação, consulte o arquivo `frontend/INTERNATIONALIZATION.md`.

## 🔒 Segurança

- Autenticação JWT
- Senhas criptografadas com bcrypt
- Isolamento de dados por usuário
- Validação de entrada com Pydantic
- CORS configurado adequadamente

## 📊 Banco de Dados

O sistema utiliza SQLite como banco de dados principal, com as seguintes tabelas:

- **users**: Usuários do sistema
- **suppliers**: Fornecedores
- **products**: Produtos
- **stock_movements**: Movimentações de estoque
- **sales**: Vendas
- **sale_items**: Itens de venda
- **purchase_orders**: Pedidos de compra
- **purchase_order_items**: Itens dos pedidos

## 🔄 Gerenciamento dos Servidores

### **Inicialização Automática**
```bash
.\start.bat
```

### **Parar Servidores**
- Feche as janelas "Backend" e "Frontend" que foram abertas
- Ou pressione `Ctrl+C` nas janelas dos servidores

### **Reiniciar**
```bash
.\start.bat
```

### **Execução Manual**
Se preferir executar manualmente:

#### Terminal 1 - Backend
```bash
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

## 🚀 Deploy

### Desenvolvimento
O projeto está configurado para desenvolvimento local com hot-reload tanto no backend quanto no frontend.

### Produção
Para deploy em produção, considere:
- Usar um banco de dados mais robusto (PostgreSQL, MySQL)
- Configurar um servidor web (Nginx, Apache)
- Implementar HTTPS
- Configurar variáveis de ambiente
- Usar um servidor WSGI para o FastAPI

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

Para suporte ou dúvidas, entre em contato através dos canais disponibilizados no projeto.

---

**PC-Express** - Transformando o gerenciamento de inventário em uma experiência simples e eficiente! 🚀
