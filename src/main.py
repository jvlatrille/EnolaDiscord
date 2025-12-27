"""
================================================================================
@fichier      : src/main.py
@description  : Bot Discord Domotique (Texte + Vocaux + Statuts via JSON).
                Version propre avec chargement depuis assets/activites.json.
================================================================================
"""
import discord
import os
import json
import random
import asyncio
from discord.ext import tasks

import config
from brain import traiter_commande_gpt, transcrire_audio
from tools.spotify import obtenir_lecture_en_cours

# Configuration Discord
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
client = discord.Client(intents=intents)

historiques = {}

# Chemin ABSOLU vers le fichier JSON pour éviter les erreurs relatives
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Dossier src/
PROJECT_ROOT = os.path.dirname(BASE_DIR)              # Dossier racine du projet
ACTIVITES_FILE = os.path.join(PROJECT_ROOT, "assets", "activites.json")

# Mapping Texte JSON -> Objet Discord
TYPE_MAPPING = {
    "playing": discord.ActivityType.playing,
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
    "streaming": discord.ActivityType.streaming
}

# Activités de secours (Fallback) si le JSON foire
FALLBACK_ACTIVITIES = [
    {"type": "watching", "name": "le fichier JSON manquant..."},
    {"type": "playing", "name": "au mode sans échec"},
]

def charger_activites():
    """
    Charge et parse le fichier JSON des activités.
    Retourne les activités de secours si erreur ou fichier vide.
    """
    if not os.path.exists(ACTIVITES_FILE):
        # On ne spamme pas le log à chaque boucle, juste retour silencieux
        return FALLBACK_ACTIVITIES
    
    try:
        with open(ACTIVITES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                return FALLBACK_ACTIVITIES
            return data
    except Exception:
        return FALLBACK_ACTIVITIES

@tasks.loop(seconds=30)
async def update_status_loop():
    """
    Boucle infinie qui met à jour le statut du bot toutes les 30 secondes.
    Priorité : Musique Spotify > Activité Random (depuis JSON)
    """
    try:
        # 1. Check Spotify
        titre_spotify = obtenir_lecture_en_cours()
        
        if titre_spotify:
            # Si musique en cours : Statut "Écoute ..." (icône par défaut)
            await client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening, 
                    name=titre_spotify
                )
            )
        else:
            # 2. Si pas de musique : Activité Random du JSON
            # On change un peu moins souvent (1 chance sur 3)
            if random.randint(1, 3) == 1:
                activites = charger_activites()
                
                if activites:
                    act_data = random.choice(activites)
                    
                    # Conversion du type (str -> discord.Enum)
                    type_str = act_data.get("type", "playing")
                    activity_type = TYPE_MAPPING.get(type_str, discord.ActivityType.playing)
                    
                    # Création de l'activité SIMPLE (sans image custom)
                    activity = discord.Activity(
                        type=activity_type, 
                        name=act_data["name"]
                    )
                    
                    await client.change_presence(activity=activity)

    except Exception as e:
        print(f"⚠️ Erreur update status : {e}")

@client.event
async def on_ready():
    print(f"🟢 Enola est connectée : {client.user}")
    print(f"📂 Activités JSON : {ACTIVITES_FILE}")
    
    # Démarrage de la boucle d'activité
    if not update_status_loop.is_running():
        update_status_loop.start()
    
    # Message de bienvenue
    try:
        user = await client.fetch_user(config.AUTHORIZED_USER_ID)
        if user:
            await user.send("Coucou ! Je suis en ligne (V6 - JSON Clean). 🫡")
    except Exception as e:
        print(f"⚠️ Erreur MP démarrage : {e}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.author.id != config.AUTHORIZED_USER_ID:
        return

    user_content = message.content

    # Gestion des vocaux
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and "audio" in attachment.content_type:
                print(f"🎤 Vocal reçu : {attachment.filename}")
                temp_filename = f"temp_{attachment.filename}"
                await attachment.save(temp_filename)
                
                async with message.channel.typing():
                    transcription = transcrire_audio(temp_filename)
                
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

                if transcription:
                    user_content = transcription
                    print(f"📝 Transcription : {user_content}")
                    await message.channel.send(f"*(J'ai entendu : \"{user_content}\")*")
                else:
                    await message.channel.send("⚠️ Je n'ai rien entendu.")
                    return
                break

    if not user_content:
        return

    print(f"📩 Traitement : {user_content}")

    if user_content.lower() in ["reset", "clear", "oubli"]:
        historiques[message.channel.id] = []
        await message.channel.send("🧹 Mémoire effacée.")
        return

    hist = historiques.get(message.channel.id, [])
    
    async with message.channel.typing():
        reponse, new_hist = traiter_commande_gpt(user_content, hist)
    
    historiques[message.channel.id] = new_hist

    if reponse:
        if len(reponse) > 2000:
            for i in range(0, len(reponse), 2000):
                await message.channel.send(reponse[i:i+2000])
        else:
            await message.channel.send(reponse)

if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        print("❌ ERREUR : DISCORD_TOKEN manquant.")
    else:
        client.run(config.DISCORD_TOKEN)