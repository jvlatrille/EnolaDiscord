"""
================================================================================
@fichier      : src/tools/spotify.py
@description  : Contrôle de la lecture musicale via l'API Spotify.
                Gère l'authentification OAuth2, la sélection intelligente du
                périlecteur (enceinte), et les commandes de lecture (Play, Pause,
                Suivant, Précédent) avec support des playlists et favoris.
================================================================================
"""

import difflib
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import (
    SPOTIPY_CLIENT_ID,
    SPOTIPY_CLIENT_SECRET,
    SPOTIPY_REDIRECT_URI,
    SPOTIFY_CACHE_PATH,
)

# ------------------------------------------------------------------------------
# AUTHENTIFICATION & CONNEXION
# ------------------------------------------------------------------------------


def get_spotify_client():
    """
    Crée et retourne un client Spotify authentifié.
    Utilise le cache pour éviter de se re-loguer à chaque fois.
    """
    if not SPOTIPY_CLIENT_ID:
        print("⚠️ Pas de config Spotify trouvée (Env Vars manquantes).")
        return None

    try:
        scope_list = (
            "user-read-playback-state "
            "user-modify-playback-state "
            "user-library-read "
            "playlist-read-private"
        )

        auth_manager = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=scope_list,
            cache_path=SPOTIFY_CACHE_PATH,
            open_browser=False,
        )

        return spotipy.Spotify(auth_manager=auth_manager)

    except Exception as e:
        print(f"❌ Erreur Init Spotify : {e}")
        return None


# ------------------------------------------------------------------------------
# FONCTIONS UTILITAIRES INTERNES
# ------------------------------------------------------------------------------


def _trouver_device_id(sp, nom_appareil=None):
    """
    Cherche l'ID d'un appareil Spotify.
    1. Si un nom est donné : cherche correspondance exacte ou approchante.
    2. Si aucun nom ou pas trouvé : prend l'appareil actif ou le premier dispo.
    """
    try:
        devices = sp.devices()
        active_devices = devices.get("devices", [])
    except Exception:
        return None

    if not active_devices:
        return None

    # A. Recherche par nom (si fourni)
    if nom_appareil:
        # 1. Correspondance exacte (partielle)
        for d in active_devices:
            if nom_appareil.lower() in d["name"].lower():
                return d["id"]

        # 2. Correspondance approximative (Fuzzy Matching)
        device_dict = {d["name"]: d["id"] for d in active_devices}
        matches = difflib.get_close_matches(
            nom_appareil, list(device_dict.keys()), n=1, cutoff=0.4
        )
        if matches:
            print(f"✅ Appareil deviné : {matches[0]}")
            return device_dict[matches[0]]

        print(f"⚠️ Appareil '{nom_appareil}' introuvable.")
        return None  # On retourne None pour signaler l'échec de la recherche spécifique

    # B. Fallback : Appareil actif ou premier de la liste
    currently_playing = next((d for d in active_devices if d["is_active"]), None)
    if currently_playing:
        return currently_playing["id"]

    return active_devices[0]["id"]


# ------------------------------------------------------------------------------
# FONCTION PRINCIPALE
# ------------------------------------------------------------------------------


def commander_spotify_reel(action, recherche=None, appareil=None, position=None):
    """
    Pilote Spotify selon les demandes de l'IA.

    Args:
        action (str): play, pause, next, previous
        recherche (str): Titre, artiste, playlist ou mots-clés "Titres Likés"
        appareil (str): Nom de l'enceinte cible
        position (int): Numéro de piste de départ (ex: 3 pour la 3ème chanson)
    """
    sp = get_spotify_client()
    if not sp:
        return "Spotify non configuré."

    print(
        f"🎵 Spotify: {action} (Rech: {recherche} | Dev: {appareil} | Pos: {position})"
    )

    try:
        # 1. Résolution de l'appareil cible
        target_device_id = _trouver_device_id(sp, appareil)

        if not target_device_id:
            if appareil:
                return f"Je ne trouve pas l'appareil '{appareil}'."
            return "Aucun appareil Spotify disponible."

        # 2. Gestion de la position (Offset)
        # L'utilisateur dit "3ème", l'API veut l'index 2.
        offset_idx = 0
        if position:
            try:
                offset_idx = int(position) - 1
                if offset_idx < 0:
                    offset_idx = 0
            except ValueError:
                pass

        # 3. Exécution de l'action
        if action == "play":
            return _gerer_lecture(sp, target_device_id, recherche, offset_idx)

        elif action == "pause":
            sp.pause_playback(device_id=target_device_id)
            return "Pause."

        elif action == "next":
            sp.next_track(device_id=target_device_id)
            return "Suivant."

        elif action == "previous":
            sp.previous_track(device_id=target_device_id)
            return "Précédent."

        return "Action inconnue."

    except spotipy.SpotifyException as e:
        print(f"⚠️ Erreur Spotify API: {e}")
        if "No active device" in str(e):
            return "Aucun lecteur actif."
        return "Erreur technique Spotify."
    except Exception as e:
        return f"Problème Spotify : {e}"


def _gerer_lecture(sp, device_id, recherche, offset_idx):
    """
    Logique interne pour l'action 'play'.
    Gère : Titres Likés, Playlists, Recherche Globale, Reprise simple.
    """
    # Fallback : Si on demande une position sans titre, on assume "Titres Likés"
    if offset_idx > 0 and not recherche:
        recherche = "Titres Likés"

    # CAS 1 : Reprise simple (Play sans argument)
    if not recherche:
        sp.start_playback(device_id=device_id)
        return "Lecture."

    recherche_low = recherche.lower()

    # --- A. MODE : TITRES LIKÉS ---
    mots_likes = [
        "titres likés",
        "titres likes",
        "mes likes",
        "coups de cœur",
        "favoris",
        "ma musique",
        "mes titres likés",
        "titres reliqués",
    ]

    if any(m in recherche_low for m in mots_likes):
        print("❤️ Mode: Titres Likés")
        try:
            # On charge assez de titres pour atteindre l'offset demandé
            limit_fetch = 50
            if offset_idx > 40:
                limit_fetch = offset_idx + 10

            results = sp.current_user_saved_tracks(limit=limit_fetch)
            uris = [item["track"]["uri"] for item in results["items"]]

            if not uris:
                return "Bibliothèque vide."

            # Tentative de mode aléatoire (shuffle)
            try:
                sp.shuffle(state=False, device_id=device_id)
            except:
                pass

            # Calcul de la liste à lire selon l'offset
            safe_offset = offset_idx if offset_idx < len(uris) else 0
            uris_to_play = uris[safe_offset:]

            sp.start_playback(device_id=device_id, uris=uris_to_play)
            return f"Titres likés lancés à partir du titre n°{safe_offset + 1}."

        except Exception as e:
            print(f"Erreur Likes: {e}")
            return "Erreur lors du lancement des likes."

    # --- B. MODE : PLAYLISTS ---
    print("📂 Recherche Playlist...")
    try:
        # Récupération des playlists utilisateur
        user_playlists = sp.current_user_playlists(limit=50)
        playlist_dict = {p["name"]: p["uri"] for p in user_playlists["items"]}

        # Recherche approximative
        matches = difflib.get_close_matches(
            recherche, list(playlist_dict.keys()), n=1, cutoff=0.6
        )

        if matches:
            best_match = matches[0]

            try:
                sp.shuffle(state=False, device_id=device_id)
            except:
                pass

            kwargs = {"device_id": device_id, "context_uri": playlist_dict[best_match]}
            if offset_idx > 0:
                kwargs["offset"] = {"position": offset_idx}

            sp.start_playback(**kwargs)
            return f"Playlist '{best_match}' lancée."
    except Exception:
        pass  # On continue vers la recherche globale si pas trouvé dans les playlists

    # --- C. MODE : RECHERCHE GLOBALE (Tracks, Artistes, Albums) ---
    print("🌍 Recherche mondiale...")
    results = sp.search(q=recherche, limit=1, type="track,artist,album")

    if results["tracks"]["items"]:
        uri = results["tracks"]["items"][0]["uri"]
        nom = results["tracks"]["items"][0]["name"]
        sp.start_playback(device_id=device_id, uris=[uri])
        return f"Titre '{nom}' lancé."

    elif results["artists"]["items"]:
        uri = results["artists"]["items"][0]["uri"]
        nom = results["artists"]["items"][0]["name"]
        sp.start_playback(device_id=device_id, context_uri=uri)
        return f"Artiste '{nom}' lancé."

    return f"Rien trouvé pour {recherche}."
