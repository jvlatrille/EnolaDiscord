"""
================================================================================
@fichier      : src/config.py
@description  : Configuration globale.
                DOIT ETRE COPIÉ DANS UN FICHIER VIDE.
================================================================================
"""
import os
from dotenv import load_dotenv

# 1. Chemins
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
ENV_PATH = os.path.join(CONFIG_DIR, ".env")
TOKEN_PATH = os.path.join(CONFIG_DIR, "token.json")
CREDENTIALS_PATH = os.path.join(CONFIG_DIR, "credentials.json")
HUE_CONFIG_PATH = os.path.join(CONFIG_DIR, "python_hue")
SPOTIFY_CACHE_PATH = os.path.join(CONFIG_DIR, ".spotify_cache")

# 2. Chargement variables
load_dotenv(ENV_PATH)

# 3. Variables
MA_VILLE = os.getenv("MA_VILLE", "Bayonne")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Gestion ID Utilisateur (sécurité)
user_id_str = os.getenv("AUTHORIZED_USER_ID", "583268098983985163")
try:
    AUTHORIZED_USER_ID = int(user_id_str)
except ValueError:
    AUTHORIZED_USER_ID = 0
    print("⚠️ ERREUR: AUTHORIZED_USER_ID mal configuré dans .env")

# APIs Externes
HUE_BRIDGE_IP = os.getenv("HUE_BRIDGE_IP")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/calendar"]