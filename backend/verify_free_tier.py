
import requests
import sys

BASE_URL = "http://localhost:8000"

def test_preferences_free_tier():
    print("1. Registrando/Logando usuário...")
    email = "test_free@example.com"
    username = "test_free"
    
    session = requests.Session()
    
    # Login/Register logic
    try:
        resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": email})
        if resp.status_code == 200:
            token = resp.json()["access_token"]
        else:
            resp = session.post(f"{BASE_URL}/api/auth/register", json={
                "email": email,
                "username": username,
                "native_language": "pt",
                "learning_language": "en"
            })
            resp.raise_for_status()
            token = resp.json()["access_token"]
    except Exception as e:
        print(f"Erro auth: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n2. Testando estratégia 'free'...")
    new_prefs = {
        "chat": "free",
        "translation": "free",
        "video_analysis": "free"
    }
    
    try:
        resp = session.put(f"{BASE_URL}/api/user/preferences/", json=new_prefs, headers=headers)
        resp.raise_for_status()
        updated_profile = resp.json()
        print(f"   Update response: {updated_profile.get('model_preferences')}")
        
        saved_prefs = updated_profile.get('model_preferences')
        if saved_prefs.get('chat') == 'free':
             print("SUCESSO: Estratégia 'free' aceita e salva!")
        else:
             print(f"FALHA: Esperado 'free', recebido {saved_prefs.get('chat')}")
             
    except Exception as e:
        print(f"ERRO ao salvar 'free': {e}")
        # Se falhar, pode ser validação do Pydantic
        if hasattr(e, 'response') and e.response:
             print(f"Detalhes do erro: {e.response.text}")

if __name__ == "__main__":
    test_preferences_free_tier()
