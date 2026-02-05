# Dockerfile para validar deps e rodar app
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Dependências do SO necessárias para builds e curl para instalar rust
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    git \
 && rm -rf /var/lib/apt/lists/*

# Instalar Rust (para compilar pydantic-core se necessário)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copiar somente requirements para aproveitar cache do docker
COPY requirements.txt requirements-ml.txt requirements-dev.txt ./

# Atualizar pip/setuptools/wheel e instalar dependências
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Porta exposta
EXPOSE 8000

# Comando default: iniciar uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

