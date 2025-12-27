"""
================================================================================
@fichier      : src/tools/calendar.py
@description  : Gestion de Google Agenda.
                Permet d'ajouter des événements et de consulter le planning
                via l'API Google Calendar v3. Gère l'authentification OAuth2.
================================================================================
"""

import os
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import TOKEN_PATH, SCOPES


# ------------------------------------------------------------------------------
# AUTHENTIFICATION GOOGLE
# ------------------------------------------------------------------------------


def get_calendar_service():
    """
    Crée et retourne un objet service authentifié pour l'API Google Calendar.
    Gère le rafraîchissement automatique du token s'il a expiré.
    """
    creds = None

    # 1. Chargement du token existant
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # 2. Vérification de la validité
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                # Rafraîchissement du token
                creds.refresh(Request())
                # Sauvegarde du nouveau token
                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"⚠️ Erreur refresh token Google: {e}")
                return None
        else:
            # Token manquant ou invalide sans refresh possible
            print(f"⚠️ Token Google absent ou invalide dans {TOKEN_PATH}.")
            print("👉 Tu dois générer un token.json (comme pour Spotify).")
            return None

    return build("calendar", "v3", credentials=creds)


# ------------------------------------------------------------------------------
# FONCTIONS MÉTIER (Appelées par le cerveau)
# ------------------------------------------------------------------------------


def ajouter_agenda_reel(titre: str, date_str: str) -> str:
    """
    Ajoute un événement dans l'agenda principal.
    Gère les erreurs de format de date et force l'année courante si nécessaire.
    """
    print(f"📅 Agenda : Demande d'ajout de '{titre}' pour {date_str}")

    try:
        service = get_calendar_service()
        if not service:
            return "Je n'ai pas accès à ton agenda Google (Token manquant)."

        # --- Conversion de la date (ISO) ---
        try:
            start_dt = datetime.fromisoformat(date_str)
        except ValueError:
            return "Je n'ai pas compris la date donnée par le système."

        # --- Correction intelligente de l'année ---
        now = datetime.now()
        # Si l'IA donne une date passée (ex: 2023), on tente de corriger pour l'année en cours
        if start_dt.year < now.year:
            print(
                f"⚠️ Date reçue dans le passé ({start_dt.year}). Correction vers {now.year}..."
            )
            try:
                start_dt = start_dt.replace(year=now.year)
            except ValueError:
                # Gestion du 29 fév si on change d'année
                start_dt = start_dt.replace(year=now.year, day=28)

        # Garde-fou final : on ne crée pas d'événement dans le passé
        if start_dt < now:
            print("⚠️ Date finale toujours dans le passé -> refus.")
            return "ERREUR_DATE_PASSEE: la date calculée est dans le passé"

        # Durée par défaut de 1h
        end_dt = start_dt + timedelta(hours=1)

        event = {
            "summary": titre,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Paris"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Paris"},
        }

        service.events().insert(calendarId="primary", body=event).execute()

        # Formatage de la date pour la réponse orale (ex: "le 12 mars à 14 heures")
        date_orale = start_dt.strftime("le %d %B à %H heures")
        return f"C'est noté, '{titre}' ajouté pour {date_orale}."

    except Exception as e:
        print(f"❌ Erreur Agenda : {e}")
        return "J'ai eu un souci technique avec l'agenda."


def consulter_agenda_reel(date_cible_str: str) -> str:
    """
    Récupère les événements de la journée spécifiée.
    """
    print(f"📅 Agenda : Consultation pour {date_cible_str}")

    try:
        service = get_calendar_service()
        if not service:
            return "Je n'ai pas accès à ton agenda."

        now = datetime.now()

        if not date_cible_str:
            date_cible = now
        else:
            try:
                date_cible = datetime.fromisoformat(date_cible_str)
            except ValueError:
                date_cible = now

            # Correction année si nécessaire
            if date_cible.year < now.year:
                date_cible = date_cible.replace(year=now.year)

        # Définition de la plage de recherche (Toute la journée UTC)
        time_min = (
            date_cible.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            + "Z"
        )
        time_max = (
            date_cible.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
            + "Z"
        )

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        if not events:
            return f"Rien de prévu pour le moment."

        reponse = "Voici le programme : "
        for event in events:
            # Gestion date vs datetime (journée entière vs heure précise)
            start = event["start"].get("dateTime", event["start"].get("date"))

            if "T" in start:
                heure = start.split("T")[1][:5]  # Récupère HH:MM
            else:
                heure = "Toute la journée"

            reponse += f"{event['summary']} à {heure}. "

        return reponse

    except Exception as e:
        print(f"❌ Erreur Lecture Agenda : {e}")
        return "Impossible de lire l'agenda pour l'instant."
