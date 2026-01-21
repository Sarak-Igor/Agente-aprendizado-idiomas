"""
Utilitários para criar arquivos mínimos de teste para modelos LLM
Usado para testar modelos de imagem, áudio e vídeo sem consumir muitos recursos
"""
import base64
import io
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow não disponível. Testes de imagem podem falhar.")


def create_minimal_image_base64() -> str:
    """
    Cria uma imagem PNG mínima (1x1 pixel) e retorna em base64
    
    Returns:
        String base64 da imagem PNG 1x1 pixel
    """
    if not PIL_AVAILABLE:
        # Fallback: retorna uma imagem PNG 1x1 válida em base64 (pixel branco)
        # PNG válido mínimo: IHDR chunk com 1x1 pixel
        minimal_png = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00'
            b'\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return base64.b64encode(minimal_png).decode('utf-8')
    
    try:
        # Cria imagem 1x1 pixel branca
        img = Image.new('RGB', (1, 1), color='white')
        
        # Salva em buffer de memória
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Converte para base64
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return img_base64
    except Exception as e:
        logger.error(f"Erro ao criar imagem mínima: {e}")
        # Fallback para PNG válido mínimo
        minimal_png = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00'
            b'\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return base64.b64encode(minimal_png).decode('utf-8')


def create_minimal_audio_base64() -> str:
    """
    Cria um arquivo de áudio WAV mínimo (1 segundo de silêncio) e retorna em base64
    
    Returns:
        String base64 do arquivo WAV 1 segundo silêncio
    """
    try:
        # WAV header para 1 segundo de áudio mono, 16-bit, 44100 Hz
        # Formato: RIFF header + fmt chunk + data chunk com silêncio
        sample_rate = 44100
        channels = 1
        bits_per_sample = 16
        duration_seconds = 1
        
        # Calcula tamanho dos dados
        data_size = sample_rate * channels * (bits_per_sample // 8) * duration_seconds
        
        # Cria WAV válido mínimo
        wav_header = b'RIFF'
        wav_header += (36 + data_size).to_bytes(4, 'little')  # Tamanho do arquivo
        wav_header += b'WAVE'
        wav_header += b'fmt '
        wav_header += (16).to_bytes(4, 'little')  # Tamanho do fmt chunk
        wav_header += (1).to_bytes(2, 'little')  # Audio format (PCM)
        wav_header += channels.to_bytes(2, 'little')  # Número de canais
        wav_header += sample_rate.to_bytes(4, 'little')  # Sample rate
        wav_header += (sample_rate * channels * (bits_per_sample // 8)).to_bytes(4, 'little')  # Byte rate
        wav_header += (channels * (bits_per_sample // 8)).to_bytes(2, 'little')  # Block align
        wav_header += bits_per_sample.to_bytes(2, 'little')  # Bits per sample
        wav_header += b'data'
        wav_header += data_size.to_bytes(4, 'little')  # Tamanho dos dados
        wav_header += b'\x00' * data_size  # Dados de silêncio (zeros)
        
        # Converte para base64
        audio_base64 = base64.b64encode(wav_header).decode('utf-8')
        return audio_base64
    except Exception as e:
        logger.error(f"Erro ao criar áudio mínimo: {e}")
        # Fallback: WAV mínimo válido
        minimal_wav = (
            b'RIFF$\x00\x00\x00WAVE'
            b'fmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00'
            b'data\x00\x00\x00\x00'
        )
        return base64.b64encode(minimal_wav).decode('utf-8')


def analyze_response_headers(response: Any) -> Dict[str, Any]:
    """
    Analisa headers de resposta HTTP para extrair informações de quota
    
    Args:
        response: Objeto de resposta (pode ser httpx.Response, requests.Response, etc)
    
    Returns:
        Dicionário com informações de quota extraídas dos headers
    """
    quota_info = {}
    
    try:
        # Tenta acessar headers de diferentes formas
        headers = None
        if hasattr(response, 'headers'):
            headers = response.headers
        elif hasattr(response, 'get'):
            headers = response
        elif isinstance(response, dict):
            headers = response
        
        if headers:
            # Headers comuns de rate limit/quota
            quota_headers = {
                'x-ratelimit-limit-requests': 'limit_requests',
                'x-ratelimit-remaining-requests': 'remaining_requests',
                'x-ratelimit-limit-tokens': 'limit_tokens',
                'x-ratelimit-remaining-tokens': 'remaining_tokens',
                'x-ratelimit-reset': 'reset_time',
                'x-ratelimit-limit': 'limit',
                'x-ratelimit-remaining': 'remaining',
            }
            
            for header_name, info_key in quota_headers.items():
                # Tenta diferentes variações do nome do header
                for variant in [header_name, header_name.upper(), header_name.replace('-', '_')]:
                    value = None
                    if isinstance(headers, dict):
                        value = headers.get(variant) or headers.get(variant.lower())
                    elif hasattr(headers, 'get'):
                        value = headers.get(variant) or headers.get(variant.lower())
                    
                    if value:
                        try:
                            # Tenta converter para número se possível
                            if value.isdigit():
                                quota_info[info_key] = int(value)
                            else:
                                quota_info[info_key] = value
                        except (ValueError, AttributeError):
                            quota_info[info_key] = value
                        break
    except Exception as e:
        logger.debug(f"Erro ao analisar headers: {e}")
    
    return quota_info
