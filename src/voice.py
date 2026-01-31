# fichier: src/voice.py
import edge_tts
import tempfile
import os

# La voix parfaite pour toi : Jeune, française, dynamique
# VOICE = "fr-FR-EloiseNeural"
VOICE = "fr-FR-VivienneMultilingualNeural"

async def generer_audio_edge(texte: str) -> bytes:
    """
    Génère un fichier audio MP3 avec la voix Edge TTS (Microsoft).
    Retourne les octets du fichier.
    """
    try:
        # On crée un fichier temporaire pour stocker le son
        communicate = edge_tts.Communicate(texte, VOICE)
        
        # On utilise un fichier temporaire sécurisé
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name
            
        # On sauvegarde l'audio dedans (await est obligatoire ici)
        await communicate.save(temp_path)
        
        # On relit le fichier en mode binaire pour récupérer les bytes
        with open(temp_path, "rb") as f:
            audio_bytes = f.read()
            
        # On nettoie (supprime) le fichier temporaire
        os.remove(temp_path)
        
        return audio_bytes

    except Exception as e:
        print(f"⚠️ Erreur Edge TTS : {e}")
        return None