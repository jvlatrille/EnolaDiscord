"""
================================================================================
@fichier      : src/brain.py
@description  : Cerveau de l'assistant (LLM + STT).
                Routeur intelligent (Contexte + Mots-clés).
================================================================================
"""
import httpx
from datetime import datetime
from openai import OpenAI

from config import OPENAI_API_KEY

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.messages import SystemMessage, HumanMessage
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage

from tools.langchain_tools import charger_tools_langchain
import re

# -----------------------------
# Whisper
# -----------------------------
custom_http_client = httpx.Client(timeout=30.0, http2=False)
client_whisper = OpenAI(api_key=OPENAI_API_KEY, http_client=custom_http_client)

def transcrire_audio(chemin_fichier: str) -> str:
    try:
        with open(chemin_fichier, "rb") as audio_file:
            transcription = client_whisper.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="fr",
            )
        return transcription.text
    except Exception as e:
        print(f"Erreur Whisper : {e}")
        return ""


# -----------------------------
# LLM + Agents
# -----------------------------
SYSTEM_PROMPT_BASE = (
    "Tu es Enola, une IA domotique sur Discord.\n"
    "Tu es efficace, concise, et tu réponds en français.\n"
    "Si une action est demandée, utilise les tools disponibles.\n"
    "Si l'utilisateur demande un truc non supporté, dis-le et propose ce que tu peux faire.\n"
)

SYSTEM_PROMPT_DOMO = SYSTEM_PROMPT_BASE + (
    "Règle: si tu utilises un tool, ta réponse finale doit être uniquement le retour du tool.\n"
)

SYSTEM_PROMPT_ANIME = (
    "Tu es Enola, assistante de suivi d'animés.\n"
    "Tu réponds en français, court.\n"
    "Règle stricte ajout: si l'utilisateur veut ajouter un animé, tu dois d'abord appeler recherche_anime, "
    "afficher le titre + l'URL d'image (texte brut), puis attendre une confirmation explicite "
    "(ex: 'confirme <id>'). Ensuite seulement tu peux appeler ajouter_anime_confirme.\n"
    "Garde tout le reste dans gerer_watchlist.\n"
    "Ne parle pas de domotique/agenda ici.\n"
)

_modele = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0.2,
    timeout=30,
)

_tools = charger_tools_langchain()

_tools_anime = [t for t in _tools if t.name in ("recherche_anime", "ajouter_anime_confirme", "gerer_watchlist")]
_tools_domo = [t for t in _tools if t.name not in ("recherche_anime", "ajouter_anime_confirme", "gerer_watchlist")]

_agent_domo = create_agent(model=_modele, tools=_tools_domo, system_prompt=SYSTEM_PROMPT_DOMO)
_agent_anime = create_agent(model=_modele, tools=_tools_anime, system_prompt=SYSTEM_PROMPT_ANIME)


def _est_demande_anime(texte: str, historique: list = None) -> bool:
    """
    Détermine si la demande concerne les animes via mots-clés OU contexte.
    """
    # 1. Analyse du CONTEXTE (Prioritaire)
    if historique:
        # On remonte l'historique pour trouver le dernier message pertinent
        for m in reversed(historique):
            # CORRECTION ICI : On vérifie AIMessage ET ToolMessage
            # Car le texte "J'ai trouvé... ID:..." est dans un ToolMessage.
            if isinstance(m, (AIMessage, ToolMessage)) and m.content:
                last_msg = m.content
                # Si le bot attend une confirmation (signature de notre tool_recherche_anime)
                if "ID:" in last_msg and "Demande confirmation" in last_msg:
                    return True
                # Si on était déjà dans une discussion Anime
                if "AniList" in last_msg or "Watchlist" in last_msg or "Crunchyroll" in last_msg:
                    return True
            
            # Si on remonte jusqu'à un message utilisateur, on arrête (contexte immédiat seulement)
            if isinstance(m, HumanMessage):
                break

    # 2. Analyse des MOTS-CLÉS (Si pas de contexte fort)
    t = (texte or "").lower()

    if re.search(r"\bconfirme\s+\d+\b", t):
        return True
    if re.search(r"\bwl\b", t):
        return True

    mots = [
        "anime", "animé", "anilist", "watchlist", "liste d'anim", "liste d’an",
        "épisode", "episode", "saison", "crunchyroll"
    ]
    return any(m in t for m in mots)


def _mettre_a_jour_system_message(historique, prompt: str):
    now = datetime.now()
    contenu = prompt + f"\nDate: {now.strftime('%A %d/%m/%Y %H:%M')} (Europe/Paris)."

    if historique and isinstance(historique[0], SystemMessage):
        historique[0] = SystemMessage(content=contenu)
        return historique

    return [SystemMessage(content=contenu)] + (historique or [])


def traiter_commande_gpt(user_text: str, conversation_history=None):
    if conversation_history is None:
        conversation_history = []

    if not user_text:
        return "Je n'ai rien entendu.", conversation_history

    # On passe l'historique au routeur pour qu'il comprenne le contexte ("oui")
    est_anime = _est_demande_anime(user_text, conversation_history)
    
    agent = _agent_anime if est_anime else _agent_domo
    prompt = SYSTEM_PROMPT_ANIME if est_anime else SYSTEM_PROMPT_DOMO

    conversation_history = _mettre_a_jour_system_message(conversation_history, prompt)

    MAX_MESSAGES = 40
    if len(conversation_history) > MAX_MESSAGES:
        conversation_history = [conversation_history[0]] + conversation_history[-(MAX_MESSAGES - 1):]

    # on ajoute le message utilisateur
    conversation_history.append(HumanMessage(content=user_text))

    try:
        resultat = agent.invoke(
            {"messages": conversation_history},
            config={"recursion_limit": 10},
        )

        messages = resultat["messages"]

        # 🔑 on récupère ce qui vient APRÈS le dernier message user
        index_last_user = max(
            i for i, m in enumerate(messages)
            if isinstance(m, HumanMessage)
        )
        nouveaux = messages[index_last_user + 1:]

        # 1️⃣ si un tool a été utilisé → on renvoie UNIQUEMENT ses retours
        sorties_tools = [
            m.content.strip()
            for m in nouveaux
            if isinstance(m, ToolMessage) and m.content and m.content.strip()
        ]

        if sorties_tools:
            return "\n".join(sorties_tools), messages

        # 2️⃣ sinon → réponse IA classique
        for m in reversed(nouveaux):
            if isinstance(m, AIMessage) and m.content and m.content.strip():
                return m.content.strip(), messages

        return "Ok.", messages

    except Exception as e:
        return f"Erreur cerveau : {e}", conversation_history