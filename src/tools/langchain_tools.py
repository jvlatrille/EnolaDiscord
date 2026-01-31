"""
================================================================================
@fichier      : src/tools/langchain_tools.py
@description  : Définition des outils pour LangChain.
                Importe les fonctions réelles et les transforme en StructuredTool.
================================================================================
"""
# --- CORRECTION IMPORT ---
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, Literal

# Imports des fonctions réelles
from .spotify import commander_spotify_reel
from .hue import commander_lumiere_reel
from .calendar import ajouter_agenda_reel, consulter_agenda_reel
from .meteo import obtenir_meteo_reel
from .system import controle_media_reel, creer_alarme_reel, get_recap_alarmes
from .wiz import commander_prise_reel
from .anilist import tool_recherche_anime, tool_ajouter_anime_confirme, tool_gerer_watchlist

# --- SCHÉMAS D'ENTRÉE (Pydantic) ---

class SpotifyInput(BaseModel):
    action: Literal["play", "pause", "next", "previous"] = Field(description="Action à effectuer")
    recherche: Optional[str] = Field(default=None, description="Titre, artiste ou 'Titres Likés'")
    appareil: Optional[str] = Field(default=None, description="Nom de l'appareil cible")
    position: Optional[int] = Field(default=None, description="Numéro de piste (si playlist)")

class HueInput(BaseModel):
    action: Literal["allumer", "eteindre", "couleur", "luminosite"] = Field(description="Action lumière")
    cible: str = Field(description="Nom de la lampe ou pièce (ex: Salon)")
    valeur: Optional[str] = Field(default=None, description="Couleur (rouge, bleu...) ou luminosité (0-100)")

class WizInput(BaseModel):
    action: Literal["allumer", "eteindre", "statut"] = Field(description="Action prise connectée")

class AgendaAjoutInput(BaseModel):
    titre: str = Field(description="Titre de l'événement")
    date_str: str = Field(description="Date ISO (YYYY-MM-DDTHH:MM:SS)")

class AgendaConsultInput(BaseModel):
    date_cible_str: str = Field(description="Date cible ISO ou 'aujourd'hui'")

class MeteoInput(BaseModel):
    ville: str = Field(description="Nom de la ville")

class MediaInput(BaseModel):
    action: Literal["volume_monter", "volume_baisser", "mute"] = Field(description="Action volume système")

class AnimeRechercheInput(BaseModel):
    query: str = Field(description="Nom de l'anime à chercher")

class AnimeAjoutInput(BaseModel):
    media_id: int = Field(description="ID de l'anime trouvé")
    titre: str = Field(description="Titre de l'anime")

class AnimeGestionInput(BaseModel):
    action: Literal["lister", "supprimer"] = Field(description="Action watchlist")
    query: Optional[str] = Field(default="", description="Nom de l'anime si suppression")

class AlarmeInput(BaseModel):
    heure_str: str = Field(description="Heure au format HH:MM")
    playlist: Optional[str] = Field(default="Titres Likés", description="Nom playlist")
    jours_str: Optional[str] = Field(default=None, description="Jours de récurrence (ex: 'lundi,mardi', 'semaine', 'weekend'). Laisser vide pour une seule fois.")

# --- LISTE DES TOOLS ---

def charger_tools_langchain():
    return [
        StructuredTool.from_function(
            func=commander_spotify_reel,
            name="commander_spotify",
            description="Pilote la musique Spotify.",
            args_schema=SpotifyInput
        ),
        StructuredTool.from_function(
            func=commander_lumiere_reel,
            name="commander_lumiere",
            description="Pilote les lumières Hue.",
            args_schema=HueInput
        ),
        StructuredTool.from_function(
            func=commander_prise_reel,
            name="commander_prise",
            description="Pilote la prise connectée WiZ (PC).",
            args_schema=WizInput
        ),
        StructuredTool.from_function(
            func=ajouter_agenda_reel,
            name="ajouter_agenda",
            description="Ajoute un RDV à l'agenda.",
            args_schema=AgendaAjoutInput
        ),
        StructuredTool.from_function(
            func=consulter_agenda_reel,
            name="consulter_agenda",
            description="Lit l'agenda.",
            args_schema=AgendaConsultInput
        ),
        StructuredTool.from_function(
            func=obtenir_meteo_reel,
            name="obtenir_meteo",
            description="Donne la météo.",
            args_schema=MeteoInput
        ),
        StructuredTool.from_function(
            func=controle_media_reel,
            name="controle_media",
            description="Gère le volume du système (Raspberry Pi).",
            args_schema=MediaInput
        ),
        StructuredTool.from_function(
            func=tool_recherche_anime,
            name="recherche_anime",
            description="Cherche un anime sur AniList (ID/Image) AVANT ajout.",
            args_schema=AnimeRechercheInput
        ),
        StructuredTool.from_function(
            func=tool_ajouter_anime_confirme,
            name="ajouter_anime_confirme",
            description="Ajoute un anime confirmé à la watchlist.",
            args_schema=AnimeAjoutInput
        ),
        StructuredTool.from_function(
            func=tool_gerer_watchlist,
            name="gerer_watchlist",
            description="Liste ou supprime des animes de la watchlist.",
            args_schema=AnimeGestionInput
        ),
        StructuredTool.from_function(
            func=creer_alarme_reel,
            name="creer_alarme",
            description="Programme une alarme Spotify. Préciser les jours si récurrent.",
            args_schema=AlarmeInput
        ),
    ]