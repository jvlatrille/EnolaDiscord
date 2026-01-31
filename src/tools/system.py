"""
================================================================================
@fichier      : src/tools/system.py
@description  : Gestion Volume + Alarmes (V2: Récurrence + One-Shot)
================================================================================
"""
import subprocess
import json
import os
import datetime
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
ALARMES_FILE = os.path.join(PROJECT_ROOT, "assets", "alarmes.json")

# Mapping des jours pour simplifier la vie de l'IA
JOURS_MAPPING = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, 
    "vendredi": 4, "samedi": 5, "dimanche": 6
}

def controle_media_reel(action: str) -> str:
    try:
        if action == "mute":
            subprocess.run(["amixer", "-c", "2", "sset", "Speaker", "toggle"], check=False)
        else:
            variation = "10%+" if action == "volume_monter" else "10%-"
            subprocess.run(["amixer", "-c", "2", "sset", "Speaker", variation], check=False)
        return "Volume ajusté."
    except Exception as e:
        return f"Erreur volume : {e}"

# --- GESTION ALARMES V2 ---

def _charger_alarmes():
    if not os.path.exists(ALARMES_FILE):
        return []
    try:
        with open(ALARMES_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def _sauver_alarmes(alarmes):
    os.makedirs(os.path.dirname(ALARMES_FILE), exist_ok=True)
    with open(ALARMES_FILE, "w") as f:
        json.dump(alarmes, f, indent=4)

def _parser_jours(jours_str: str):
    """Convertit 'lundi,mardi' en [0, 1]. Retourne None pour 'une fois'."""
    if not jours_str or jours_str.lower() in ["une fois", "non", "aucun"]:
        return None  # Mode One-Shot
    
    jours_str = jours_str.lower()
    indices = set()
    
    # Mots-clés magiques
    if "tous" in jours_str or "chaque jour" in jours_str:
        return [0, 1, 2, 3, 4, 5, 6]
    if "semaine" in jours_str: # Lundi au Vendredi
        indices.update([0, 1, 2, 3, 4])
    if "weekend" in jours_str or "week-end" in jours_str:
        indices.update([5, 6])
        
    # Jours spécifiques
    for nom, idx in JOURS_MAPPING.items():
        if nom in jours_str:
            indices.add(idx)
            
    return list(indices) if indices else None

def creer_alarme_reel(heure_str: str, playlist: str = "Titres Likés", jours_str: str = None) -> str:
    """
    Crée une alarme.
    jours_str: "lundi,mardi", "semaine", "tous les jours". Si vide -> One Shot.
    """
    try:
        datetime.datetime.strptime(heure_str, "%H:%M")
    except ValueError:
        return "Format invalide (HH:MM)."

    indices_jours = _parser_jours(jours_str)
    alarmes = _charger_alarmes()
    
    # On ajoute la nouvelle
    alarmes.append({
        "heure": heure_str,
        "playlist": playlist,
        "jours": indices_jours, # Liste [0,1...] ou None
        "active": True
    })
    
    _sauver_alarmes(alarmes)
    
    if indices_jours:
        noms = [k for k,v in JOURS_MAPPING.items() if v in indices_jours]
        txt_jours = ", ".join(noms)
        return f"📅 Alarme récurrente réglée à {heure_str} ({txt_jours})."
    else:
        return f"⏰ Alarme unique réglée pour demain (ou aujourd'hui) à {heure_str}."

def check_alarmes_actives():
    """Vérifie et nettoie les alarmes One-Shot passées."""
    now = datetime.datetime.now()
    heure_now = now.strftime("%H:%M")
    jour_now = now.weekday() # 0 = Lundi
    
    alarmes = _charger_alarmes()
    alarmes_a_garder = []
    playlist_a_lancer = None
    
    for alarme in alarmes:
        declenche = False
        
        if alarme["active"] and alarme["heure"] == heure_now:
            # Cas 1 : Récurrent
            if alarme["jours"] is not None:
                if jour_now in alarme["jours"]:
                    declenche = True
                    # On garde l'alarme
                    alarmes_a_garder.append(alarme)
                else:
                    # Pas le bon jour, on garde quand même
                    alarmes_a_garder.append(alarme)
            
            # Cas 2 : One-Shot (Une seule fois)
            else:
                declenche = True
                # On NE l'ajoute PAS à alarmes_a_garder -> Elle sera supprimée
        else:
            alarmes_a_garder.append(alarme)
            
        if declenche:
            playlist_a_lancer = alarme.get("playlist", "Titres Likés")

    # Si on a supprimé des alarmes one-shot, on sauvegarde
    if len(alarmes) != len(alarmes_a_garder):
        _sauver_alarmes(alarmes_a_garder)
        
    return playlist_a_lancer

def get_recap_alarmes():
    """Retourne un texte joli avec les alarmes programmées."""
    alarmes = _charger_alarmes()
    if not alarmes:
        return None
        
    lignes = []
    for a in alarmes:
        h = a["heure"]
        p = a["playlist"]
        if a["jours"]:
            j_txt = ",".join([k[:3] for k,v in JOURS_MAPPING.items() if v in a["jours"]]) # lun,mar...
            lignes.append(f"• 🔄 {h} : {p} ({j_txt})")
        else:
            lignes.append(f"• 1️⃣ {h} : {p} (Une fois)")
            
    return "\n".join(lignes)