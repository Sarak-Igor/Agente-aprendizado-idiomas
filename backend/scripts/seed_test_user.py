"""
Script para criar um usuário de teste (usuario@teste.com) se não existir.
Uso: python backend/scripts/seed_test_user.py
"""
import logging
import sys
import os

# Adiciona o diretório 'backend' ao path para que 'app' seja encontrado como módulo de topo
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.database import SessionLocal
from app.services.auth_service import get_user_by_email, create_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_test_user():
    db = SessionLocal()
    try:
        email = "usuario@teste.com"
        username = "usuario_teste"
        password = "Teste1234" # MVP: Plain text as per current auth_service implementation
        
        user = get_user_by_email(db, email)
        if user:
            logger.info(f"Usuário de teste já existe: {email}")
            return
            
        logger.info(f"Criando usuário de teste: {email}")
        create_user(
            db=db,
            email=email,
            username=username,
            password=password,
            native_language="pt",
            learning_language="en"
        )
        logger.info("Usuário criado com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao criar usuário de teste: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_user()
