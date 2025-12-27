"""
================================================================================
@fichier      : src/tools/__init__.py
@description  : Registre central des outils (Functions) pour le LLM.
                Expose les fonctions Python réelles et définit le schéma JSON
                envoyé à l'API OpenAI pour le "Function Calling".
================================================================================
"""

from .spotify import commander_spotify_reel
from .hue import commander_lumiere_reel
from .calendar import ajouter_agenda_reel, consulter_agenda_reel
from .meteo import obtenir_meteo_reel
from .system import controle_media_reel, creer_alarme_reel

# ------------------------------------------------------------------------------
# DÉFINITIONS DES OUTILS (JSON SCHEMA)
# ------------------------------------------------------------------------------
# Ce dictionnaire décrit à GPT comment utiliser les fonctions Python ci-dessus.

TOOLS_DEFINITION = [
    # --- AGENDA : AJOUT ---
    {
        "type": "function",
        "function": {
            "name": "ajouter_agenda",
            "description": "Ajoute un événement dans Google Agenda. IMPORTANT: date_str doit être une date/heure future calculée à partir d'aujourd'hui en Europe/Paris.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titre": {"type": "string"},
                    "date_str": {
                        "type": "string",
                        "description": "Date/heure locale Europe/Paris au format ISO: YYYY-MM-DDTHH:MM:SS (sans Z). Ex: 2025-12-22T08:00:00",
                    },
                },
                "required": ["titre", "date_str"],
            },
        },
    },
    # --- AGENDA : LECTURE ---
    {
        "type": "function",
        "function": {
            "name": "consulter_agenda",
            "description": "Lecture agenda",
            "parameters": {
                "type": "object",
                "properties": {"date_cible_str": {"type": "string"}},
                "required": ["date_cible_str"],
            },
        },
    },
    # --- SYSTÈME : VOLUME ---
    {
        "type": "function",
        "function": {
            "name": "controle_media",
            "description": "Volume Système RPi (Pas Spotify)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["volume_monter", "volume_baisser", "mute"],
                    }
                },
                "required": ["action"],
            },
        },
    },
    # --- MÉTÉO ---
    {
        "type": "function",
        "function": {
            "name": "obtenir_meteo",
            "description": "Météo",
            "parameters": {
                "type": "object",
                "properties": {"ville": {"type": "string"}},
                "required": ["ville"],
            },
        },
    },
    # --- SYSTÈME : ALARME ---
    {
        "type": "function",
        "function": {
            "name": "creer_alarme",
            "description": "Alarme",
            "parameters": {
                "type": "object",
                "properties": {"heure_str": {"type": "string"}},
                "required": ["heure_str"],
            },
        },
    },
    # --- DOMOTIQUE : LUMIÈRES (HUE) ---
    {
        "type": "function",
        "function": {
            "name": "commander_lumiere",
            "description": "Lumières Hue",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["allumer", "eteindre", "couleur", "luminosite"],
                    },
                    "cible": {"type": "string"},
                    "valeur": {"type": "string"},
                },
                "required": ["action", "cible"],
            },
        },
    },
    # --- MULTIMÉDIA : SPOTIFY ---
    {
        "type": "function",
        "function": {
            "name": "commander_spotify",
            "description": "Contrôle la musique sur Spotify (Play, Pause, Recherche).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play", "pause", "next", "previous"],
                    },
                    "recherche": {
                        "type": "string",
                        "description": "Ce qu'il faut jouer : Titre, Artiste, Playlist ou 'Titres Likés'. Obligatoire sauf pour 'Reprendre'.",
                    },
                    "appareil": {"type": "string", "description": "Appareil cible."},
                    "position": {
                        "type": "integer",
                        "description": "Numéro de la piste par laquelle commencer (ex: 3).",
                    },
                },
                "required": ["action"],
            },
        },
    },
]
