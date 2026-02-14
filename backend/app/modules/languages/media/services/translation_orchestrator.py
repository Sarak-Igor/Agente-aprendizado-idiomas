import os
import logging
from typing import Tuple, List, Optional

from app.modules.agents.core_llm.models.models import ApiKey
from app.services.encryption import encryption_service
from app.modules.languages.media.services.translation_factory import TranslationServiceFactory

logger = logging.getLogger(__name__)


def select_translation_service(db, user_id, gemini_api_key: Optional[str] = None, preferred_service: Optional[str] = None) -> Tuple[Optional[object], Optional[str], List[str], Optional[str]]:
    """
    Retorna (translation_service, selected_service_name, tried_services, last_error)
    """
    translation_service = None
    tried_services = []
    last_error = None
    selected_service_name = None

    translation_service_name = os.getenv("TRANSLATION_SERVICE", "googletrans").lower()
    force_tools_first = translation_service_name == "gemini"
    if force_tools_first:
        translation_service_name = "googletrans"

    # base list: deeptranslator, googletrans, argos, libretranslate
    services_to_try = []
    services_to_try.append(("deeptranslator", {"delay": 0.2}))
    services_to_try.append(("googletrans", {"delay": 0.3}))
    services_to_try.append(("argos", {}))
    libretranslate_url = os.getenv("LIBRETRANSLATE_URL", "http://localhost:5000")
    services_to_try.append(("libretranslate", {"api_url": libretranslate_url}))

    # add gemini fallback if key exists
    existing_gemini_key = db.query(ApiKey).filter(ApiKey.user_id == user_id, ApiKey.service == "gemini").first()
    if existing_gemini_key:
        try:
            decrypted_key = encryption_service.decrypt(existing_gemini_key.encrypted_key)
            services_to_try.append(("gemini", {"api_key": decrypted_key, "db": db}))
        except Exception as e:
            logger.debug(f"Erro ao descriptografar chave Gemini: {e}")
    elif gemini_api_key:
        try:
            encrypted_key = encryption_service.encrypt(gemini_api_key)
            api_key = ApiKey(user_id=user_id, video_id=None, service="gemini", encrypted_key=encrypted_key)
            db.add(api_key)
            db.commit()
            services_to_try.append(("gemini", {"api_key": gemini_api_key, "db": db}))
        except Exception as e:
            logger.debug(f"Erro ao salvar chave Gemini: {e}")

    # Try services
    for service_name, service_config in services_to_try:
        try:
            tried_services.append(service_name)
            translation_service = TranslationServiceFactory.create(service_name, service_config)
            if translation_service.is_available():
                selected_service_name = service_name
                return translation_service, selected_service_name, tried_services, None
            else:
                translation_service = None
                last_error = f"Serviço {service_name} não está disponível"
                logger.debug(last_error)
        except ImportError as e:
            translation_service = None
            last_error = f"{service_name} não instalado: {str(e)}"
            logger.debug(last_error)
            continue
        except Exception as e:
            translation_service = None
            last_error = str(e)
            logger.debug(f"Erro ao usar {service_name}: {last_error}")
            continue

    # final fallback attempt for gemini if not tried
    if "gemini" not in tried_services:
        try:
            existing_key = db.query(ApiKey).filter(ApiKey.user_id == user_id, ApiKey.service == "gemini").first()
            if existing_key:
                decrypted_key = encryption_service.decrypt(existing_key.encrypted_key)
                translation_service = TranslationServiceFactory.create("gemini", {"api_key": decrypted_key, "db": db})
            elif gemini_api_key:
                encrypted_key = encryption_service.encrypt(gemini_api_key)
                api_key = ApiKey(user_id=user_id, video_id=None, service="gemini", encrypted_key=encrypted_key)
                db.add(api_key)
                db.commit()
                translation_service = TranslationServiceFactory.create("gemini", {"api_key": gemini_api_key, "db": db})
            else:
                translation_service = None

            if translation_service and translation_service.is_available():
                selected_service_name = "gemini"
                return translation_service, selected_service_name, tried_services, None
            else:
                translation_service = None
        except Exception as e:
            translation_service = None
            last_error = f"Gemini também falhou: {str(e)}"

    return None, None, tried_services, last_error

