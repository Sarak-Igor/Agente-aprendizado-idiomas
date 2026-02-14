import re
import unicodedata
from difflib import SequenceMatcher

def normalize_text(text: str) -> str:
    """Normaliza texto removendo acentos, pontuação e convertendo para minúsculas"""
    if not text:
        return ""
    
    # Remove espaços extras
    text = " ".join(text.split())
    
    # Converte para minúsculas
    text = text.lower()
    
    # Remove acentos
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    
    # Remove pontuação (mantém apenas letras, números e espaços)
    text = re.sub(r'[^\w\s]', '', text)
    
    return text.strip()

def normalize_semantic(text: str) -> str:
    """
    Normalização semântica (pode incluir expansão de contrações no futuro).
    Por enquanto, usa a normalização básica.
    """
    return normalize_text(text)

def calculate_similarity(a: str, b: str) -> float:
    """Calcula similaridade entre duas strings (0.0 a 1.0)"""
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()

def check_answer_similarity(user_answer: str, correct_answer: str, threshold: float = 0.85) -> bool:
    """Verifica se a resposta é considerada correta baseada no threshold"""
    if not user_answer or not correct_answer:
        return False
        
    sim = calculate_similarity(user_answer, correct_answer)
    return sim >= threshold
