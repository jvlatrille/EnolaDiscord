"""
================================================================================
@fichier      : src/tools/system.py
@description  : Contrôle des fonctions système du Raspberry Pi.
                Gère le volume général (via ALSA/amixer) et la création d'alarmes.
================================================================================
"""

import subprocess

def controle_media_reel(action: str) -> str:
    """
    Ajuste le volume global du système Linux via la commande 'amixer'.
    
    Args:
        action (str): "volume_monter", "volume_baisser" ou "mute"
    """
    try:
        if action == "mute":
            # Bascule l'état Mute/Unmute
            subprocess.run(["amixer", "sset", "Master", "toggle"], check=False)
        else:
            # Détermine la variation (+10% ou -10%)
            variation = "10%+" if action == "volume_monter" else "10%-"
            subprocess.run(["amixer", "sset", "Master", variation], check=False)
        
        return "Volume système ajusté."
        
    except Exception as e:
        print(f"❌ Erreur Volume : {e}")
        return "Erreur volume système."


def creer_alarme_reel(heure_str: str) -> str:
    """
    Programme une alarme (Stub / Fonctionnalité à implémenter).
    """
    # TODO: Connecter à un vrai planificateur (Cron, Systemd timer ou Thread)
    return f"Alarme {heure_str} OK"