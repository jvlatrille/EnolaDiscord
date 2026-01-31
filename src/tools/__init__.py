"""
================================================================================
@fichier      : src/tools/__init__.py
@description  : Point d'entrée du package tools.
================================================================================
"""

# Exports des fonctions réelles
from .spotify import commander_spotify_reel
from .hue import commander_lumiere_reel
from .calendar import ajouter_agenda_reel, consulter_agenda_reel
from .meteo import obtenir_meteo_reel
from .system import controle_media_reel, creer_alarme_reel
from .wiz import commander_prise_reel
from .anilist import tool_recherche_anime, tool_ajouter_anime_confirme, tool_gerer_watchlist, check_new_episodes

# Note : L'ancien dictionnaire TOOLS_DEFINITION a été retiré.
# Utilisez src/tools/langchain_tools.py pour les définitions d'outils LangChain.