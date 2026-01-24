import os
import uuid
import logging
from typing import List, Optional
from uuid import UUID
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

logger = logging.getLogger(__name__)

class RAGService:
    """
    Serviço de Retrieval-Augmented Generation (RAG) profissional.
    Utiliza ChromaDB para busca vetorial semântica.
    """
    
    def __init__(self, db: Optional[any] = None, persist_directory: Optional[str] = None):
        if persist_directory is None:
            # Caminho absoluto relativo ao backend (5 níveis acima de services/rag_service.py)
            # 1: services, 2: agents_factory, 3: modules, 4: app, 5: backend
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            self.persist_directory = os.path.join(base_dir, "chroma_db")
        else:
            self.persist_directory = persist_directory
            
        print(f"DEBUG RAG: ChromaDB persistindo em: {self.persist_directory}")
        self.client = None
        
        if CHROMA_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=self.persist_directory)
                logger.info("✅ ChromaDB inicializado com sucesso.")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar ChromaDB: {e}")
        else:
            logger.warning("⚠️ ChromaDB não está instalado. RAG estará desativado.")

    async def ingest_file(self, session_id: UUID, file_path: str, user_id: UUID) -> bool:
        """Extrai texto e indexa no ChromaDB."""
        if not self.client:
            logger.error("ChromaDB não disponível para ingestão.")
            return False
            
        try:
            text = ""
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == ".pdf":
                if not PDF_AVAILABLE: 
                    logger.error("PyPDF não disponível.")
                    return False
                print(f"DEBUG RAG: Lendo PDF {file_path}")
                reader = PdfReader(file_path)
                text = "\n".join([page.extract_text() for page in reader.pages])
                print(f"DEBUG RAG: Texto extraído ({len(text)} caracteres)")
            elif ext in [".txt", ".md", ".json"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                logger.warning(f"Extensão de arquivo não suportada: {ext}")
                return False

            if not text.strip():
                print("DEBUG RAG: Texto vazio após extração")
                return False

            chunks = self._chunk_text(text)
            print(f"DEBUG RAG: Gerados {len(chunks)} fragmentos")
            sid = str(session_id)
            
            # Cria ou obtém a coleção para a sessão
            coll_name = f"session_{sid.replace('-', '_')}"
            print(f"DEBUG RAG: Acessando coleção ChromaDB: {coll_name}")
            collection = self.client.get_or_create_collection(name=coll_name)
            
            # 2. Busca registro do Documento
            from app.modules.agents_factory.models.models import AgentDocument

            # Adiciona ao banco vetorial
            print(f"DEBUG RAG: Enviando para o ChromaDB...")
            collection.add(
                documents=chunks,
                ids=[f"{sid}_{i}_{uuid.uuid4()}" for i in range(len(chunks))],
                metadatas=[{"session_id": sid, "user_id": str(user_id)} for _ in chunks]
            )
            
            logger.info(f"✅ Arquivo {file_path} indexado com sucesso no ChromaDB.")
            print("DEBUG RAG: Ingestão concluída com sucesso")
            return True

        except Exception as e:
            logger.error(f"❌ Erro na ingestão RAG (ChromaDB): {e}")
            print(f"DEBUG RAG: Erro na ingestão: {str(e)}")
            return False

    def retrieve_context(self, session_id: UUID, query: str, n_results: int = 5) -> str:
        """
        Busca context no ChromaDB. 
        Implementa fallback para garantir que o Agente receba algo relevante mesmo 
        se a query for genérica (ex: 'analise o contrato').
        """
        if not self.client:
            return ""
            
        try:
            sid = str(session_id).replace('-', '_')
            coll_name = f"session_{sid}"
            
            try:
                collection = self.client.get_collection(name=coll_name)
            except Exception:
                # Coleção não existe
                return ""
            
            # 1. Busca semântica principal
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            documents = results.get("documents", [[]])[0]
            
            # 2. Heurística para queries genéricas ou resultados fracos
            # Se a query for muito curta ou o resultado for escasso, pegamos o início do doc
            query_lower = query.lower()
            needs_more = len(documents) < 2 or any(word in query_lower for word in ["analise", "resumo", "detalhe", "contrato"])
            
            if needs_more:
                # Busca 'cega' pelos primeiros itens (id baseada em ordem)
                # No Chroma, podemos dar um query com texto genérico ou pegar por metadata
                extra_results = collection.get(limit=3, include=["documents"])
                extra_docs = extra_results.get("documents", [])
                for d in extra_docs:
                    if d not in documents:
                        documents.append(d)
            
            if not documents:
                return ""
                
            # Limita ao n_results final para não estourar o prompt
            final_docs = documents[:n_results]
            
            logger.info(f"RAG: Recuperados {len(final_docs)} fragmentos para a sessao {sid}")
            return "\n---\n".join(final_docs)
            
        except Exception as e:
            logger.warning(f"Erro ao recuperar contexto RAG: {str(e)}")
            return ""

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """Divide o texto em chunks menores com sobreposição."""
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
        return chunks
