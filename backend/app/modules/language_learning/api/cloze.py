from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database import Video, Translation, User
from app.api.routes.auth import get_current_user
from uuid import UUID
import random
import re
import logging
from app.modules.language_learning.storage.cloze_store import save_cloze, get_cloze
from difflib import SequenceMatcher

router = APIRouter()
logger = logging.getLogger(__name__)


def choose_cloze_positions(text: str, gaps: int):
    # Simple heuristic: choose words longer than 2 letters, not very common
    # Legacy helper — kept for compatibility but not used by main generator.
    words = [w for w in re.split(r'(\s+)', text) if w.strip() != '']
    candidates_idx = [i for i, w in enumerate(words) if re.match(r'^\w+$', w) and len(w) > 2]
    if not candidates_idx:
        return []
    random.shuffle(candidates_idx)
    chosen = sorted(candidates_idx[:gaps])
    return chosen


def normalize_text(s: str) -> str:
    if s is None:
        return ''
    s2 = s.lower().strip()
    s2 = re.sub(r'[^\w\s]', '', s2, flags=re.U)
    return s2


def similarity_score(a: str, b: str) -> float:
    try:
        return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()
    except Exception:
        return 0.0


@router.post("/cloze")
async def get_cloze(request: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Gera exercício cloze a partir de traduções ou frases geradas.
    Body:
      mode: 'music-context' | 'new-context'
      direction: 'en-to-pt' | 'pt-to-en'
      difficulty: 'easy'|'medium'|'hard'
      gaps: number of gaps (1-4)
      video_ids: optional
    """
    try:
        mode = request.get('mode', 'music-context')
        direction = request.get('direction', 'en-to-pt')
        difficulty = request.get('difficulty', 'medium')
        gaps = int(request.get('gaps', 1))
        video_ids = request.get('video_ids')

        # For music-context, pick a translation segment
        query = db.query(Translation).join(Video).filter(
            Translation.user_id == current_user.id,
            Video.user_id == current_user.id
        )
        if video_ids:
            video_ids_list = [UUID(vid) for vid in video_ids]
            query = query.filter(Video.id.in_(video_ids_list))
        translations = query.all()
        if not translations:
            raise HTTPException(status_code=404, detail="Nenhuma tradução disponível")

        if mode == 'music-context':
            translation = random.choice(translations)
            video = db.query(Video).filter(Video.id == translation.video_id).first()
            segments = translation.segments or []
            if not segments:
                raise HTTPException(status_code=404, detail="Sem segmentos na tradução")
            segment = random.choice(segments)
            # Determine effective text based on direction (reuse inversion logic)
            if direction == 'en-to-pt':
                original_text = segment.get('original', '')
                translated_text = segment.get('translated', '')
                src = translation.source_language
                tgt = translation.target_language
                # if translation stored reversed, we still trust fields
            else:
                original_text = segment.get('original', '')
                translated_text = segment.get('translated', '')

            # build placeholder representation: find word token indices, then choose gaps among them
            tokens = re.split(r'(\s+)', original_text)
            word_indices = [i for i, t in enumerate(tokens) if re.match(r'^\w+$', t)]
            if not word_indices:
                masked = original_text
                answers = []
            else:
                choose_n = max(1, min(4, gaps, len(word_indices)))
                chosen_indices = random.sample(word_indices, choose_n)
                chosen_indices.sort()
                answers = []
                for ti in chosen_indices:
                    answers.append(tokens[ti])
                    tokens[ti] = '____'
                masked = ''.join(tokens)

            payload = {
                "id": f"cloze-{translation.id}-{segment.get('start', 0)}",
                "original": original_text,
                "masked": masked,
                "translated": translated_text,
                "answers": answers,
                "source_language": translation.source_language,
                "target_language": translation.target_language,
                "video_title": video.title if video else None,
                "video_id": str(video.id) if video else None
            }
            try:
                save_cloze(payload["id"], payload)
            except Exception:
                pass
            return payload
        else:
            # new-context: if LLM available, generate phrase using existing code; else fallback to translations
            # For simplicity, reuse a random translation segment as fallback
            translation = random.choice(translations)
            video = db.query(Video).filter(Video.id == translation.video_id).first()
            segments = translation.segments or []
            if not segments:
                raise HTTPException(status_code=404, detail="Sem segmentos na tradução")
            segment = random.choice(segments)
            original_text = segment.get('original', '')
            tokens = re.split(r'(\s+)', original_text)
            word_indices = [i for i, t in enumerate(tokens) if re.match(r'^\w+$', t)]
            if not word_indices:
                masked = original_text
                answers = []
            else:
                choose_n = max(1, min(4, gaps, len(word_indices)))
                chosen_indices = random.sample(word_indices, choose_n)
                chosen_indices.sort()
                answers = []
                for ti in chosen_indices:
                    answers.append(tokens[ti])
                    tokens[ti] = '____'
                masked = ''.join(tokens)
            return {
                "id": f"cloze-fallback-{translation.id}-{segment.get('start', 0)}",
                "original": original_text,
                "masked": masked,
                "translated": segment.get('translated', ''),
                "answers": answers,
                "source_language": translation.source_language,
                "target_language": translation.target_language,
                "video_title": video.title if video else None,
                "video_id": str(video.id) if video else None
            }
        # persist generated cloze so check endpoint can validate without relying on frontend-provided expected_answers
        try:
            save_cloze(f"cloze-{translation.id}-{segment.get('start', 0)}", {
                "original": original_text,
                "masked": masked,
                "translated": segment.get('translated', ''),
                "answers": answers,
                "source_language": translation.source_language,
                "target_language": translation.target_language,
                "video_title": video.title if video else None,
                "video_id": str(video.id) if video else None
            })
        except Exception:
            # best effort
            pass
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao gerar cloze")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-cloze")
async def check_cloze(request: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Verifica respostas de um cloze.
    Body:
      phrase_id, answers: list[str], direction
    """
    try:
        phrase_id = request.get('phrase_id')
        answers = request.get('answers', [])
        expected_answers = request.get('expected_answers', None)
        direction = request.get('direction', 'en-to-pt')

        if not phrase_id:
            raise HTTPException(status_code=400, detail="phrase_id required")

        # If expected_answers provided by frontend, use them. Otherwise try to fallback to lookup in store.
        if expected_answers is None:
            stored = get_cloze(phrase_id)
            if stored and stored.get('answers'):
                expected_answers = stored.get('answers')
            else:
                # Basic fallback: accept non-empty answers
                is_all_correct = all([a and len(a.strip()) > 0 for a in answers])
                return {"is_correct": is_all_correct, "details": {"provided": len(answers), "mode": "fallback_non_empty"}}

        # Normalize function
        def normalize_text(s: str) -> str:
            if s is None:
                return ''
            s = s.lower().strip()
            s = re.sub(r'[^\w\s]', '', s, flags=re.U)
            return s

        from difflib import SequenceMatcher

        results = []
        all_ok = True
        for idx, expected in enumerate(expected_answers):
            provided = answers[idx] if idx < len(answers) else ''
            ne = normalize_text(expected)
            np = normalize_text(provided)
            score = 0.0
            if ne == np and ne != '':
                score = 1.0
            else:
                # fuzzy similarity
                try:
                    score = SequenceMatcher(None, ne, np).ratio()
                except Exception:
                    score = 0.0
            ok = score >= 0.7  # threshold
            if not ok:
                all_ok = False
            results.append({"index": idx, "expected": expected, "provided": provided, "score": score, "ok": ok})

        return {"is_correct": all_ok, "details": {"per_gap": results}}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao verificar cloze")
        raise HTTPException(status_code=500, detail=str(e))

