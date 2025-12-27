"""
================================================================================
@fichier      : src/main.py
@description  : Bot Discord Domotique.
                DOIT ETRE COPIÉ DANS UN FICHIER VIDE.
================================================================================
"""
import discord
import config  # Import du module complet pour éviter les NameError
from brain import traiter_commande_gpt

# Configuration Discord
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
client = discord.Client(intents=intents)

# Mémoire de conversation
historiques = {}

@client.event
async def on_ready():
    print(f"🟢 Enola est connectée : {client.user}")
    print(f"🔒 Utilisateur autorisé ID : {config.AUTHORIZED_USER_ID}")
    
    # Message de bienvenue
    try:
        user = await client.fetch_user(config.AUTHORIZED_USER_ID)
        if user:
            await user.send("Coucou ! Je suis en ligne et prête à servir. 🫡")
    except Exception as e:
        print(f"⚠️ Impossible d'envoyer le MP de démarrage : {e}")

@client.event
async def on_message(message):
    # Ignorer ses propres messages
    if message.author == client.user:
        return

    # Sécurité ID
    if message.author.id != config.AUTHORIZED_USER_ID:
        print(f"⛔ Ignoré message de {message.author.name} ({message.author.id})")
        return

    print(f"📩 Reçu : {message.content}")

    # Reset
    if message.content.lower() in ["reset", "clear"]:
        historiques[message.channel.id] = []
        await message.channel.send("🧹 Mémoire effacée.")
        return

    # Traitement IA
    hist = historiques.get(message.channel.id, [])
    
    async with message.channel.typing():
        reponse, new_hist = traiter_commande_gpt(message.content, hist)
    
    historiques[message.channel.id] = new_hist

    # Envoi (découpage si trop long)
    if reponse:
        if len(reponse) > 2000:
            for i in range(0, len(reponse), 2000):
                await message.channel.send(reponse[i:i+2000])
        else:
            await message.channel.send(reponse)

if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        print("❌ ERREUR CRITIQUE : Variable DISCORD_TOKEN introuvable.")
        print("👉 Vérifie ton fichier config/.env")
    else:
        try:
            client.run(config.DISCORD_TOKEN)
        except Exception as e:
            print(f"❌ Erreur au lancement : {e}")