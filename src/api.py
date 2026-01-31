# fichier: src/api.py
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import base64
from brain import traiter_commande_gpt
from voice import generer_audio_edge  # 👈 On importe la nouvelle fonction

app = FastAPI(title="Enola API")

class Commande(BaseModel):
    texte: str

historique = []

@app.on_event("startup")
async def startup_event():  # 👈 async ici aussi
    print("🟢 Enola API (Edge TTS Version) est en ligne !")

# ⚠️ Changement important : on ajoute 'async' devant la fonction
@app.post("/ask")
async def poser_question(commande: Commande):
    global historique
    user_text = commande.texte
    print(f"📞 Reçu : {user_text}")

    if user_text.lower() in ["reset", "clear", "oubli"]:
        historique = []
        return {"reponse": "Mémoire effacée.", "audio": ""}

    try:
        # 1. Cerveau (Texte)
        # Note: traiter_commande_gpt est synchrone, ça ne bloque pas trop pour un usage perso.
        reponse_texte, new_hist = traiter_commande_gpt(user_text, historique)
        historique = new_hist
        print(f"🤖 Réponse Texte : {reponse_texte}")

        # 2. Voix (Audio) - Edge TTS
        print("🗣️ Génération de la voix Edge (Eloise)...")
        
        # On utilise 'await' car la fonction est asynchrone
        audio_bytes = await generer_audio_edge(reponse_texte)
        
        audio_base64 = ""
        if audio_bytes:
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        return {
            "reponse": reponse_texte,
            "audio": audio_base64
        }

    except Exception as e:
        print(f"❌ Erreur : {e}")
        return {"reponse": "Erreur technique.", "audio": ""}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)