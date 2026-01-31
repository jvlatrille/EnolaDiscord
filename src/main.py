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
from datetime import datetime, timedelta
from discord.ext import tasks

import config
from brain import traiter_commande_gpt, transcrire_audio
from tools.spotify import obtenir_lecture_en_cours, commander_spotify_reel
from tools.scraper import check_new_codes
from tools.anilist import check_new_episodes
from tools.system import check_alarmes_actives, get_recap_alarmes

import subprocess
import sys
import time

# Configuration Discord
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
client = discord.Client(intents=intents)
dernier_channel_autorise = None
prochain_recap = None

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


@tasks.loop(hours=4)
async def task_codes():
    # Le scraper retourne maintenant une liste de dicts : [{'game': '...', 'code': '...'}]
    nouveautés = await client.loop.run_in_executor(None, check_new_codes)
    
    if nouveautés:
        user = await client.fetch_user(config.AUTHORIZED_USER_ID)
        if user:
            for item in nouveautés:
                jeu = item['game']
                code = item['code']
                
                # Couleur différente selon le jeu
                couleur = 0xE67E22 # Orange par défaut (Arknights)
                if "Strinova" in jeu:
                    couleur = 0x3498DB # Bleu pour Strinova

                embed = discord.Embed(
                    title=f"🎁 Nouveau code {jeu} !",
                    description=f"Code : **{code}**\n\n_Pense à l'activer en jeu !_ 🎮",
                    color=couleur
                )
                await user.send(embed=embed)
                print(f"✉️ Code envoyé pour {jeu} : {code}")
       
@tasks.loop(minutes=5)
async def task_animes():
    global dernier_channel_autorise

    nouveaux = await client.loop.run_in_executor(None, check_new_episodes)
    if not nouveaux:
        return

    # cible: salon connu, sinon DM
    canal = None
    if dernier_channel_autorise:
        canal = client.get_channel(dernier_channel_autorise)

    if canal is None:
        try:
            canal = await client.fetch_user(config.AUTHORIZED_USER_ID)
        except Exception:
            canal = None

    if canal is None:
        return

    for item in nouveaux:
        titre = item["titre"]
        ep = item["episode"]
        crunchy = item["crunchy_url"]
        anilist = item.get("anilist_url")
        image = item.get("image_url")

        embed = discord.Embed(
            title=f"Nouvel épisode: {titre}",
            description=f"Épisode {ep} détecté.",
            url=anilist or crunchy,
            color=0x7F8C8D
        )
        if image:
            embed.set_thumbnail(url=image)

        embed.add_field(name="Crunchyroll", value=crunchy, inline=False)
        if anilist:
            embed.add_field(name="AniList", value=anilist, inline=False)

        await canal.send(embed=embed)

def planifier_prochain_recap():
    """Calcule une heure aléatoire entre 08h00 et 21h00 pour le prochain message"""
    global prochain_recap
    now = datetime.now()
    
    # On choisit une heure aléatoire aujourd'hui
    heure_random = random.randint(8, 20)
    minute_random = random.randint(0, 59)
    
    cible = now.replace(hour=heure_random, minute=minute_random, second=0)
    
    # Si cette heure est déjà passée aujourd'hui, on la met à demain
    if cible < now:
        cible = cible + timedelta(days=1)
        # On relance le dé pour demain pour que ce soit pas la même heure
        cible = cible.replace(hour=random.randint(8, 20), minute=random.randint(0, 59))
    
    prochain_recap = cible
    print(f"📅 Prochain récap planifié pour : {prochain_recap.strftime('%d/%m %H:%M')}")

@tasks.loop(minutes=1) # On vérifie chaque minute
async def task_recap_alarmes():
    global prochain_recap
    
    # Sécurité initialisation
    if prochain_recap is None:
        planifier_prochain_recap()
        return

    now = datetime.now()
    
    # Si on a dépassé l'heure prévue (à la minute près)
    if now >= prochain_recap:
        # 1. On récupère le texte
        texte_recap = await client.loop.run_in_executor(None, get_recap_alarmes)
        
        # 2. On envoie si y'a des alarmes
        if texte_recap:
            user = await client.fetch_user(config.AUTHORIZED_USER_ID)
            if user:
                embed = discord.Embed(title="⏰ Récapitulatif de tes alarmes", description=texte_recap, color=0xF1C40F)
                await user.send(embed=embed)
                print("✉️ Récap envoyé !")
        
        # 3. On replanifie pour demain
        # On force l'ajout d'un jour pour être sûr de pas boucler
        demain = now + timedelta(days=1)
        prochain_recap = demain.replace(hour=random.randint(8, 20), minute=random.randint(0, 59))
        print(f"📅 Prochain récap (replanifié) : {prochain_recap.strftime('%d/%m %H:%M')}")


@tasks.loop(seconds=60)
async def task_alarmes():
    """Vérifie chaque minute si une alarme doit sonner"""
    # On exécute la vérification dans un thread pour ne pas bloquer le bot
    playlist = await client.loop.run_in_executor(None, check_alarmes_actives)
    
    if playlist:
        print(f"⏰ DRIIING ! Lancement de l'alarme : {playlist}")
        
        # On force la lecture sur l'appareil 'Enola_Pi' (ton speaker)
        await client.loop.run_in_executor(None, lambda: commander_spotify_reel(
            action="play", 
            recherche=playlist, 
            appareil="Enola_Pi"
        ))

@task_alarmes.before_loop
async def before_task_alarmes():
    """
    Cette fonction s'exécute UNE FOIS avant le démarrage de la boucle.
    Elle permet de se caler sur la minute pile (XX:XX:00).
    """
    await client.wait_until_ready()
    
    now = datetime.now()
    # On calcule combien de secondes il reste avant la prochaine minute
    secondes_a_attendre = 60 - now.second
    
    print(f"⏳ Synchronisation de l'horloge... Attente de {secondes_a_attendre}s.")
    await asyncio.sleep(secondes_a_attendre)

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
            await user.send("Coucou\nEn ligne 🫡")
    except Exception as e:
        print(f"⚠️ Erreur MP démarrage : {e}")
    
    if not task_codes.is_running():
        task_codes.start()
        print("✅ Scraper Arknights activé.")

    if not task_animes.is_running():
        task_animes.start()
        print("✅ Scraper Animes activé.")

    if not task_alarmes.is_running():
        task_alarmes.start()
        print("✅ Système d'alarmes activé.")

    if not task_recap_alarmes.is_running():
        planifier_prochain_recap()
        task_recap_alarmes.start()

@client.event
async def on_message(message):
    global dernier_channel_autorise
    
    if message.author == client.user:
        return

    if message.author.id != config.AUTHORIZED_USER_ID:
        return

    user_content = message.content
    dernier_channel_autorise = message.channel.id

    # Gestion des vocaux
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and "audio" in attachment.content_type:
                print(f"🎤 Vocal reçu : {attachment.filename}")
                temp_filename = f"temp_{attachment.filename}"
                await attachment.save(temp_filename)
                
                async with message.channel.typing():
                    transcription = await asyncio.to_thread(transcrire_audio, temp_filename)
                
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
        reponse, new_hist = await asyncio.to_thread(traiter_commande_gpt, user_content, hist)
    
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
        sys.exit(1)

    # Lancement de l'API en parallèle
    api_path = os.path.join(BASE_DIR, "api.py")
    process_api = None

    try:
        print(f"🚀 Lancement de l'API depuis : {api_path}")
        # On utilise sys.executable pour garder le même environnement Python (venv ou autre)
        process_api = subprocess.Popen([sys.executable, api_path])
        
        # Lancement du bot (bloquant)
        client.run(config.DISCORD_TOKEN)

    except KeyboardInterrupt:
        # Géré proprement par discord.py, mais au cas où
        pass

    finally:
        # Nettoyage à la fermeture du bot
        if process_api:
            print("🛑 Arrêt de l'API...")
            process_api.terminate()
            try:
                process_api.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process_api.kill()
            print("✅ API arrêtée.")