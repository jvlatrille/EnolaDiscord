"""
================================================================================
@fichier      : src/tools/anilist.py
@description  : Gestion des anime avec Anilist (GraphQL).
                Permet de chercher, ajouter à une watchlist et vérifier les sorties.
================================================================================
"""
import os
import json
import time
import requests

# --- CONFIGURATION DES CHEMINS (Infaillible) ---
# On part de ce fichier : src/tools/anilist.py
CURRENT_FILE = os.path.abspath(__file__)
TOOLS_DIR = os.path.dirname(CURRENT_FILE)        # src/tools
SRC_DIR = os.path.dirname(TOOLS_DIR)             # src
PROJECT_ROOT = os.path.dirname(SRC_DIR)          # discordEnola (racine)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

# Fichiers de données
WATCHLIST_FILE = os.path.join(ASSETS_DIR, "anime_watchlist.json")
HISTORY_FILE = os.path.join(ASSETS_DIR, "anime_history.json")

ANILIST_API_URL = "https://graphql.anilist.co"

# --- UTILITAIRES FICHIERS ---

def _load_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception as e:
        print(f"⚠️ Erreur lecture JSON {filepath} : {e}")
        return []

def _save_json(filepath, data):
    try:
        # On s'assure que le dossier assets existe
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"💾 Sauvegarde réussie : {filepath}") # Debug log
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde JSON {filepath} : {e}")

def get_watchlist():
    return _load_json(WATCHLIST_FILE)

# --- FONCTIONS "REELLES" (Backend) ---

def tool_recherche_anime(query: str) -> str:
    """
    Cherche un anime sur AniList pour obtenir ID/Titre/Image.
    Retourne une string formatée pour l'IA.
    """
    gql = """
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        id
        title { romaji }
        coverImage { large }
        siteUrl
        description
      }
    }
    """
    try:
        resp = requests.post(ANILIST_API_URL, json={'query': gql, 'variables': {'search': query}}, timeout=5)
        data = resp.json()
        
        if not data.get('data') or not data['data'].get('Media'):
            return "❌ Anime introuvable sur AniList."

        m = data['data']['Media']
        # On retourne un résumé texte brut (URL simple)
        return (
            f"J'ai trouvé : {m['title']['romaji']} (ID: {m['id']})\n"
            f"Lien image: {m['coverImage']['large']}\n"
            f"URL: {m['siteUrl']}\n"
            "Demande confirmation à l'utilisateur."
        )
    except Exception as e:
        return f"Erreur API AniList : {e}"

def tool_ajouter_anime_confirme(media_id: int, titre: str) -> str:
    """
    Ajoute l'ID à la watchlist (appelé uniquement après confirmation).
    """
    watchlist = get_watchlist()
    
    # Conversion en int pour éviter les doublons string/int
    try:
        media_id = int(media_id)
    except:
        return "Erreur : L'ID doit être un nombre."

    if media_id in watchlist:
        return f"⚠️ {titre} est déjà dans la liste."
    
    watchlist.append(media_id)
    _save_json(WATCHLIST_FILE, watchlist)
    return f"✅ {titre} a été ajouté aux notifications."

def tool_gerer_watchlist(action: str, query: str = "") -> str:
    """
    Liste ou supprime des animes.
    action: 'lister' ou 'supprimer'
    """
    ids = get_watchlist()
    
    if action == "lister":
        if not ids: return "La watchlist est vide."
        # Récupération des titres en masse
        gql = """
        query ($ids: [Int]) {
          Page { media(id_in: $ids) { title { romaji } } }
        }
        """
        try:
            resp = requests.post(ANILIST_API_URL, json={'query': gql, 'variables': {'ids': ids}})
            data = resp.json()
            if 'errors' in data: return "Erreur API lors du listing."
            
            medias = data['data']['Page']['media']
            titres = [f"- {m['title']['romaji']}" for m in medias]
            return "**📺 Watchlist actuelle :**\n" + "\n".join(titres)
        except Exception as e:
            return f"Erreur récupération liste : {e}"

    elif action == "supprimer":
        search_res = tool_recherche_anime(query)
        if "introuvable" in search_res or "Erreur" in search_res:
            return "Je ne trouve pas cet anime pour le supprimer."
        
        # On refait une petite requête ID rapide
        gql_search = "query ($s: String) { Media (search: $s, type: ANIME) { id title { romaji } } }"
        try:
            r = requests.post(ANILIST_API_URL, json={'query': gql_search, 'variables': {'s': query}})
            d = r.json()['data']['Media']
            target_id = d['id']
            target_title = d['title']['romaji']
            
            if target_id in ids:
                ids.remove(target_id)
                _save_json(WATCHLIST_FILE, ids)
                return f"🗑️ {target_title} retiré de la watchlist."
            else:
                return f"{target_title} n'était pas dans la liste."
        except:
            return "Erreur lors de la suppression."
            
    return "Action inconnue."

# --- CHECK AUTO (Task Loop) ---

def check_new_episodes():
    """Vérifie les sorties récentes (-1h à +1h)."""
    watchlist = get_watchlist()
    if not watchlist: return []

    history = _load_json(HISTORY_FILE)
    now = int(time.time())
    
    query = """
    query ($start: Int, $end: Int, $ids: [Int]) {
      Page {
        airingSchedules(airingAt_greater: $start, airingAt_lesser: $end, mediaId_in: $ids) {
          id
          episode
          airingAt
          media {
            id
            title { romaji }
            siteUrl
            coverImage { large }
            externalLinks { site url }
          }
        }
      }
    }
    """
    variables = {
        "start": now - 3600, 
        "end": now + 3600,
        "ids": watchlist
    }

    new_releases = []
    try:
        resp = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables}, timeout=10)
        if resp.status_code != 200: return []
        
        data = resp.json()
        if 'errors' in data: return []
        
        schedules = data.get('data', {}).get('Page', {}).get('airingSchedules', [])

        for item in schedules:
            unique_id = f"{item['media']['id']}_EP{item['episode']}"
            
            if unique_id in history:
                continue
            
            # Si l'heure de sortie est passée (ou imminente à 2 min près)
            if item['airingAt'] <= now + 120: 
                crunchy_link = item['media']['siteUrl']
                for link in item['media']['externalLinks']:
                    if "Crunchyroll" in link['site']:
                        crunchy_link = link['url']
                        break
                
                new_releases.append({
                    "titre": item['media']['title']['romaji'],
                    "episode": item['episode'],
                    "crunchy_url": crunchy_link,
                    "anilist_url": item['media']['siteUrl'],
                    "image_url": item['media']['coverImage']['large'],
                    "timestamp": item['airingAt']
                })
                history.append(unique_id)
        
        if len(history) > 200: history = history[-200:]
        if new_releases: _save_json(HISTORY_FILE, history)

    except Exception as e:
        print(f"⚠️ Erreur Check Anime : {e}")

    return new_releases