"""
Script de migração para adicionar campos topics e analysis_metadata à tabela chat_messages
Execute: python migrate_add_analysis_fields.py
"""
from app.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_column_exists(connection, table_name: str, column_name: str) -> bool:
    """Verifica se uma coluna existe na tabela"""
    query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name 
        AND column_name = :column_name
    """)
    result = connection.execute(query, {"table_name": table_name, "column_name": column_name})
    return result.fetchone() is not None


def add_column_if_not_exists(connection, table_name: str, column_name: str, column_type: str):
    """Adiciona coluna se ela não existir"""
    if not check_column_exists(connection, table_name, column_name):
        logger.info(f"Adicionando coluna {column_name} à tabela {table_name}...")
        alter_query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        connection.execute(alter_query)
        connection.commit()
        logger.info(f"Coluna {column_name} adicionada com sucesso!")
    else:
        logger.info(f"Coluna {column_name} já existe na tabela {table_name}")


def main():
    """Executa migração"""
    logger.info("Iniciando migração: adicionando campos topics e analysis_metadata...")
    
    try:
        with engine.connect() as connection:
            # Adiciona coluna topics (JSONB, nullable)
            add_column_if_not_exists(
                connection,
                "chat_messages",
                "topics",
                "JSONB"
            )
            
            # Adiciona coluna analysis_metadata (JSONB, nullable)
            add_column_if_not_exists(
                connection,
                "chat_messages",
                "analysis_metadata",
                "JSONB"
            )
            
            connection.commit()
            logger.info("Migração concluída com sucesso!")
            
    except Exception as e:
        logger.error(f"Erro durante migração: {e}")
        raise


if __name__ == "__main__":
    main()
