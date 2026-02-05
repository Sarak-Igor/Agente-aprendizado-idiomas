# Sarak - Plataforma de Agentes e Aprendizado de Idiomas

Este projeto é uma plataforma modular para agentes de IA e aprendizado de idiomas, utilizando FastAPI (Python) no backend e Vite (React) no frontend.

## 🚀 Como instalar em um novo computador

### 1. Pré-requisitos
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL** instalado e rodando.

### 2. Configuração do Banco de Dados
1. Crie um banco de dados no PostgreSQL chamado `Agente_traducao`.
2. Certifique-se de que o serviço do PostgreSQL está ativo.

### 3. Configuração do Backend
1. Entre na pasta `backend`:
   ```bash
   cd backend
   ```
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   # No Windows:
   .\.venv\Scripts\activate
   # No Linux/Mac:
   source .venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure o arquivo `.env`:
   - Copie o `env.example` da raiz para a pasta `backend/` e renomeie-o para `.env`.
   - Ajuste as credenciais do banco de dados em `DATABASE_URL`.
5. Inicialize as tabelas do banco:
   ```bash
   python init_db.py
   ```
6. (Opcional) Popule dados iniciais:
   ```bash
   python seed_canonical_names.py
   ```

### 4. Configuração do Frontend
1. Na raiz do projeto, instale as dependências do Node:
   ```bash
   npm install
   ```
2. (Se houver uma pasta `frontend` separada):
   ```bash
   cd frontend
   npm install
   ```

## 🛠️ Como executar o projeto

### Executar Backend
```bash
cd backend
.\.venv\Scripts\activate
python -m uvicorn app.main:app --reload
```

### Executar Frontend
```bash
# Na raiz ou na pasta frontend
npm run dev
```

---

## 🏗️ Estrutura do Sistema
Consulte o arquivo [MAPA_SISTEMA.md](file:///c:/Users/Igor/Desktop/Sarak/X%20-%20Trabalho/Code/Agentes/agente-aprendizado-idiomas/MAPA_SISTEMA.md) para detalhes técnicos da arquitetura do backend.
