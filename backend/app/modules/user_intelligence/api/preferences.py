
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.modules.user_intelligence.models.models import UserProfile
from app.schemas.schemas import ModelPreferencesUpdate, UserProfileResponse
from app.api.routes.auth import get_current_user
from app.models.database import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/preferences", tags=["user_preferences"])

@router.put("/", response_model=UserProfileResponse)
async def update_preferences(
    prefs: ModelPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza as preferências de modelo do usuário.
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de usuário não encontrado"
        )
    
    # Atualiza preferências. 
    # model_preferences é um dict JSONB.
    # Se já existir, faz merge.
    
    current_prefs = profile.model_preferences or {}
    
    updates = prefs.dict(exclude_unset=True)
    if not updates:
        return UserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            native_language=profile.native_language,
            learning_language=profile.learning_language,
            proficiency_level=profile.proficiency_level,
            total_chat_messages=profile.total_chat_messages,
            total_practice_sessions=profile.total_practice_sessions,
            average_response_time=profile.average_response_time,
            learning_context=profile.learning_context,
            preferred_learning_style=profile.preferred_learning_style,
            preferred_model=profile.preferred_model,
            model_preferences=current_prefs,
            created_at=current_user.created_at
        )
        
    # Merge updates
    current_prefs.update(updates)
    
    # Força SQLAlchemy a detectar mudança no JSONB
    profile.model_preferences = dict(current_prefs)
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(profile, "model_preferences")
    
    try:
        db.commit()
        db.refresh(profile)
        logger.info(f"Preferências atualizadas para usuário {current_user.id}: {profile.model_preferences}")
        
        return UserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            native_language=profile.native_language,
            learning_language=profile.learning_language,
            proficiency_level=profile.proficiency_level,
            total_chat_messages=profile.total_chat_messages,
            total_practice_sessions=profile.total_practice_sessions,
            average_response_time=profile.average_response_time,
            learning_context=profile.learning_context,
            preferred_learning_style=profile.preferred_learning_style,
            preferred_model=profile.preferred_model,
            model_preferences=profile.model_preferences,
            created_at=current_user.created_at
        )
    except Exception as e:
        logger.error(f"Erro ao atualizar preferencias: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao salvar preferências")
