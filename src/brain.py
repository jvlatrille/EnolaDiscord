"""
================================================================================
@fichier      : src/brain.py
@description  : Cerveau de l'assistant (LLM).
                Adapté pour Discord : Retourne du texte au lieu de parler.
================================================================================
"""

import json
from datetime import datetime
import httpx
from openai import OpenAI

from config import OPENAI_API_KEY
from tools import (
    TOOLS_DEFINITION,
    ajouter_agenda_reel,
    consulter_agenda_reel,
    obtenir_meteo_reel,
    commander_lumiere_reel,
    controle_media_reel,
    creer_alarme_reel,
    commander_spotify_reel,
)

# Client OpenAI avec timeout augmenté
custom_http_client = httpx.Client(timeout=30.0, http2=False)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=custom_http_client)

def traiter_commande_gpt(user_text, conversation_history=None):
    """
    Traite le texte entrant, exécute les outils si besoin, 
    et RETOURNE la réponse textuelle finale + l'historique mis à jour.
    
    Returns:
        tuple: (reponse_str, historique_list)
    """
    # Initialisation de l'historique si vide
    if conversation_history is None:
        conversation_history = []

    # System Prompt minimaliste si nouveau contexte
    if not conversation_history:
        now = datetime.now()
        conversation_history.append({
            "role": "system",
            "content": (
                "Tu es Enola, une IA domotique sur Discord. "
                "Tu es efficace, concise et familière. "
                "Tu pilotes Spotify, les lumières Hue et l'agenda Google. "
                f"Date: {now.strftime('%A %d/%m/%Y %H:%M')}."
            ),
        })

    # Ajout du message utilisateur
    conversation_history.append({"role": "user", "content": user_text})

    try:
        # 1. Premier appel GPT (Détection d'intention)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history,
            tools=TOOLS_DEFINITION,
            tool_choice="auto",
        )
        msg = completion.choices[0].message
        conversation_history.append(msg)

        # 2. Gestion des Outils (Function Calling)
        if msg.tool_calls:
            for tc in msg.tool_calls:
                fname = tc.function.name
                args = json.loads(tc.function.arguments)
                print(f"🛠️  Outil appelé : {fname}")
                
                res = "Fait."

                # Exécution réelle
                if fname == "commander_spotify":
                    res = commander_spotify_reel(args.get("action"), args.get("recherche"), args.get("appareil"), args.get("position"))
                elif fname == "commander_lumiere":
                    res = commander_lumiere_reel(args.get("action"), args.get("cible"), args.get("valeur"))
                elif fname == "ajouter_agenda":
                    res = ajouter_agenda_reel(args.get("titre"), args.get("date_str"))
                elif fname == "consulter_agenda":
                    res = consulter_agenda_reel(args.get("date_cible_str"))
                elif fname == "obtenir_meteo":
                    res = obtenir_meteo_reel(args.get("ville"))
                elif fname == "creer_alarme":
                    res = creer_alarme_reel(args.get("heure_str"))
                elif fname == "controle_media":
                    res = controle_media_reel(args.get("action"))

                # Ajout du résultat technique à l'historique
                conversation_history.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": str(res)}
                )

            # 3. Réponse finale après exécution des outils
            final_response = client.chat.completions.create(
                model="gpt-4o-mini", messages=conversation_history
            )
            final_msg = final_response.choices[0].message
            conversation_history.append(final_msg)
            
            return final_msg.content, conversation_history

        # Cas simple : Pas d'outil, conversation directe
        return msg.content, conversation_history

    except Exception as e:
        err_msg = f"⚠️ Oups, erreur cerveau : {e}"
        print(err_msg)
        return err_msg, conversation_history