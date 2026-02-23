"""
Serviço de autenticação com JWT e hash de senha
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.database import User, UserProfile
from app.config import settings
import secrets
import logging
import hashlib

logger = logging.getLogger(__name__)

# Patch para incompatibilidade entre passlib e bcrypt 4.0.0+
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        bcrypt.__about__ = type('about', (), {'__version__': bcrypt.__version__})
except ImportError:
    pass


# Configuração de hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuração JWT - usar chave secreta do .env ou gerar uma
SECRET_KEY = getattr(settings, 'jwt_secret_key', None) or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias


def _pre_hash_password(password: str) -> str:
    """
    Faz pré-hash da senha usando SHA-256 antes de passar para bcrypt.
    Isso resolve o problema de senhas maiores que 72 bytes, pois:
    - SHA-256 sempre produz 32 bytes (256 bits)
    - Bcrypt aceita até 72 bytes, então 32 bytes está dentro do limite
    - Isso permite senhas de qualquer tamanho sem truncamento
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha está correta.
    Usa pré-hash SHA-256 para evitar problemas com senhas > 72 bytes.
    """
    try:
        pre_hashed = _pre_hash_password(plain_password)
        # Verifica usando bcrypt direto se possível, fallback para pwd_context
        # Transformamos strings em bytes para o bcrypt
        return bcrypt.checkpw(
            pre_hashed.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Erro ao verificar senha: {e}")
        # Fallback para passlib se o hash estiver num formato que o bcrypt puro não entenda
        return pwd_context.verify(_pre_hash_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    """
    Gera hash da senha usando bcrypt direto.
    Usa pré-hash SHA-256 para evitar problemas com senhas > 72 bytes.
    """
    try:
        pre_hashed = _pre_hash_password(password)
        # Gera sal e hash
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pre_hashed.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao fazer hash da senha com bcrypt direto: {e}")
        # Se falhar, tenta via passlib (com o patch já aplicado no topo do arquivo)
        pre_hashed = _pre_hash_password(password)
        return pwd_context.hash(pre_hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verifica e decodifica token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Busca usuário por email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Busca usuário por username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Busca usuário por ID"""
    from uuid import UUID
    try:
        return db.query(User).filter(User.id == UUID(user_id)).first()
    except (ValueError, TypeError):
        return None


def create_user(
    db: Session,
    email: str,
    username: str,
    native_language: str = "pt",
    learning_language: str = "en",
    password: str = None
) -> User:
    """Cria novo usuário com perfil"""
    # Verifica se email ou username já existem
    if get_user_by_email(db, email):
        raise ValueError("Email já está em uso")
    if get_user_by_username(db, username):
        raise ValueError("Username já está em uso")
    
    # Cria usuário com senha hasheada
    user = User(
        email=email,
        username=username,
        password=get_password_hash(password) if password else None
    )
    db.add(user)
    db.flush()  # Para obter o ID do usuário
    
    # Cria perfil
    profile = UserProfile(
        user_id=user.id,
        native_language=native_language,
        learning_language=learning_language,
        proficiency_level="beginner"
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    
    logger.info(f"Usuário criado: {username} ({email})")
    return user


def authenticate_user(db: Session, email: str, password: Optional[str] = None) -> Optional[User]:
    """
    Autentica usuário por email e senha.
    - Se `password` for fornecida, compara diretamente (texto simples - MVP).
    - Se não for fornecida, retorna o usuário (compatibilidade com chamadas anteriores).
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not user.is_active:
        return None

    if password is None:
        # Compatibilidade: somente verificação por email
        return user

    stored = getattr(user, "password", None)
    if stored is None:
        return None
    
    # Verifica hash bcrypt (compatibilidade garantida via migration)
    if not verify_password(password, stored):
        # Fallback provisório: se a senha bater em texto simples, migramos na hora
        if stored == password:
            user.password = get_password_hash(password)
            db.commit()
            return user
        return None
        
    return user
