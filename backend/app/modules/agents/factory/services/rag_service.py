import os
import uuid
import logging
from typing import List, Optional, Tuple
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
    
    Arquitetura de coleções:
    - session_{id}_docs: Documentos enviados pelo usuário (PDFs, TXTs, etc.)
    - session_{id}_msgs: Mensagens da conversa (user + assistant)
    """
    
    def __init__(self, db: Optional[any] = None, persist_directory: Optional[str] = None):
        if persist_directory is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            self.persist_directory = os.path.join(base_dir, "chroma_db")
        else:
            self.persist_directory = persist_directory
            
        logger.info(f"ChromaDB persistindo em: {self.persist_directory}")
        self.client = None
        
        if CHROMA_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=self.persist_directory)
                logger.info("✅ ChromaDB inicializado com sucesso.")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar ChromaDB: {e}")
        else:
            logger.warning("⚠️ ChromaDB não está instalado. RAG estará desativado.")

    def _get_collection_name(self, session_id: UUID, collection_type: str) -> str:
        """Gera nome padronizado para coleção."""
        sid = str(session_id).replace('-', '_')
        return f"session_{sid}_{collection_type}"

    def index_message(self, session_id: UUID, role: str, content: str) -> bool:
        """
        Indexa uma mensagem da conversa no banco vetorial.
        
        Args:
            session_id: ID da sessão
            role: 'user' ou 'assistant'
            content: Conteúdo da mensagem
            
        Returns:
            True se indexado com sucesso
        """
        if not self.client:
            return False
            
        if not content or len(content.strip()) < 10:
            return False
            
        try:
            coll_name = self._get_collection_name(session_id, "msgs")
            collection = self.client.get_or_create_collection(name=coll_name)
            
            msg_id = f"msg_{uuid.uuid4()}"
            
            collection.add(
                documents=[content],
                ids=[msg_id],
                metadatas=[{
                    "session_id": str(session_id),
                    "role": role,
                    "type": "message"
                }]
            )
            
            logger.debug(f"Mensagem indexada: {role} ({len(content)} chars)")
            return True
            
        except Exception as e:
            logger.warning(f"Erro ao indexar mensagem: {str(e)}")
            return False

    async def ingest_file(self, session_id: UUID, file_path: str, user_id: UUID) -> bool:
        """Extrai texto de arquivo e indexa no ChromaDB (coleção _docs)."""
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
                reader = PdfReader(file_path)
                text = "\n".join([page.extract_text() for page in reader.pages])
            elif ext in [".txt", ".md", ".json"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                logger.warning(f"Extensão de arquivo não suportada: {ext}")
                return False

            if not text.strip():
                return False

            chunks = self._chunk_text(text)
            
            coll_name = self._get_collection_name(session_id, "docs")
            collection = self.client.get_or_create_collection(name=coll_name)
            
            collection.add(
                documents=chunks,
                ids=[f"doc_{i}_{uuid.uuid4()}" for i in range(len(chunks))],
                metadatas=[{
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                    "source": os.path.basename(file_path),
                    "type": "document"
                } for _ in chunks]
            )
            
            logger.info(f"✅ Arquivo {file_path} indexado: {len(chunks)} chunks")
            return True

        except Exception as e:
            logger.error(f"❌ Erro na ingestão RAG: {e}")
            return False

    def _query_collection(self, coll_name: str, query: str, n_results: int) -> List[Tuple[str, str]]:
        """Busca em uma coleção específica e retorna (documento, tipo)."""
        results = []
        try:
            collection = self.client.get_collection(name=coll_name)
            query_results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas"]
            )
            
            documents = query_results.get("documents", [[]])[0]
            metadatas = query_results.get("metadatas", [[]])[0]
            
            for doc, meta in zip(documents, metadatas):
                doc_type = meta.get("type", "unknown")
                results.append((doc, doc_type))
                
        except Exception:
            pass
            
        return results

    def retrieve_context(self, session_id: UUID, query: str, n_results: int = 5) -> str:
        """
        Busca contexto híbrido: documentos + histórico de mensagens.
        Retorna contexto formatado com indicação de origem.
        """
        if not self.client:
            return ""
            
        try:
            docs_coll = self._get_collection_name(session_id, "docs")
            msgs_coll = self._get_collection_name(session_id, "msgs")
            
            doc_results = self._query_collection(docs_coll, query, n_results)
            msg_results = self._query_collection(msgs_coll, query, n_results)
            
            formatted_parts = []
            
            for doc, doc_type in doc_results[:3]:
                formatted_parts.append(f"[DOC] {doc}")
                
            for msg, msg_type in msg_results[:3]:
                formatted_parts.append(f"[MSG] {msg}")
            
            if not formatted_parts:
                return ""
                
            context = "\n---\n".join(formatted_parts)
            logger.info(f"RAG: Recuperados {len(doc_results)} docs + {len(msg_results)} msgs")
            return context
            
        except Exception as e:
            logger.warning(f"Erro ao recuperar contexto RAG: {str(e)}")
            return ""

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """Divide o texto em chunks menores com sobreposição."""
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        return chunks
