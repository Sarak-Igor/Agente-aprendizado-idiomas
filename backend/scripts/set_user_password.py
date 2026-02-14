#!/usr/bin/env python3
"""
Script simples para definir senha de usuário (texto plano - MVP).
Uso: python backend/scripts/set_user_password.py

Este script usa as configurações de `app.database` para conectar ao banco.
"""
import sys
import logging

from backend.app.database import SessionLocal
from backend.app.models.database import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def set_password_for_email(email: str, password: str) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.error("Usuário não encontrado: %s", email)
            return False
        user.password = password
        db.add(user)
        db.commit()
        logger.info("Senha atualizada para usuário %s (id=%s)", email, user.id)
        return True
    except Exception as e:
        logger.exception("Erro ao atualizar senha: %s", e)
        db.rollback()
        return False
    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    # Valores solicitados
    target_email = "igorsarak@gmail.com"
    target_password = "Sarak1234"

    success = set_password_for_email(target_email, target_password)
    if not success:
        sys.exit(1)
    sys.exit(0)

