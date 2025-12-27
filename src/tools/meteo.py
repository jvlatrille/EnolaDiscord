"""
================================================================================
@fichier      : src/tools/meteo.py
@description  : Récupération des données météorologiques.
                Utilise l'API Open-Meteo (gratuite, sans clé) pour obtenir
                les coordonnées GPS d'une ville puis sa température actuelle.
================================================================================
"""

import requests
from config import MA_VILLE


def obtenir_meteo_reel(ville: str) -> str:
    """
    Récupère la température actuelle pour une ville donnée via Open-Meteo.
    Utilise la ville par défaut définie dans la config si aucune ville n'est fournie.
    """
    if not ville:
        ville = MA_VILLE

    try:
        # 1. Étape de Géocodage : Trouver Latitude/Longitude depuis le nom
        url_geo = f"https://geocoding-api.open-meteo.com/v1/search?name={ville}&count=1&language=fr&format=json"
        res = requests.get(url_geo).json()

        if not res.get("results"):
            return "Ville inconnue."

        lat = res["results"][0]["latitude"]
        lon = res["results"][0]["longitude"]

        # 2. Étape Météo : Récupérer la température avec les coordonnées
        url_weather = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        weather = requests.get(url_weather).json()

        temp = weather["current"]["temperature_2m"]

        return f"Il fait {temp}°C à {ville}."

    except Exception:
        return "Erreur météo."
