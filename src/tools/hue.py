"""
================================================================================
@fichier      : src/tools/hue.py
@description  : Interface avec le pont Philips Hue.
                Permet de contrôler les lumières (allumer, éteindre, couleur,
                luminosité) en détectant automatiquement s'il s'agit d'un
                groupe ou d'une ampoule unique.
================================================================================
"""

from phue import Bridge
from config import HUE_BRIDGE_IP, HUE_CONFIG_PATH

# ------------------------------------------------------------------------------
# CONSTANTES (Palette de couleurs)
# ------------------------------------------------------------------------------
# Conversion Nom -> Coordonnées XY (CIE color space) pour Hue
COULEURS_HUE = {
    "rouge": [0.6679, 0.3181],
    "vert": [0.4091, 0.5180],
    "bleu": [0.1670, 0.0400],
    "jaune": [0.4325, 0.5007],
    "orange": [0.5562, 0.4084],
    "violet": [0.2700, 0.1300],
    "rose": [0.3800, 0.1400],
    "blanc": [0.3227, 0.3290],
}

# ------------------------------------------------------------------------------
# GESTION DE LA CONNEXION
# ------------------------------------------------------------------------------


def get_hue_bridge():
    """
    Tente d'établir la connexion avec le pont Hue.
    Retourne l'objet Bridge ou None en cas d'échec.
    """
    if not HUE_BRIDGE_IP:
        return None

    try:
        return Bridge(HUE_BRIDGE_IP, config_file_path=HUE_CONFIG_PATH)
    except Exception:
        return None


# ------------------------------------------------------------------------------
# FONCTIONS MÉTIER
# ------------------------------------------------------------------------------


def commander_lumiere_reel(action: str, cible: str, valeur: str = None) -> str:
    """
    Exécute une action sur une lumière ou un groupe Hue.

    Args:
        action (str): "allumer", "eteindre", "couleur", "luminosite"
        cible (str): Le nom de la lampe ou de la pièce (ex: "Salon", "Cuisine")
        valeur (str): Paramètre optionnel (ex: "rouge" pour couleur, "50" pour luminosité)
    """
    bridge = get_hue_bridge()
    if not bridge:
        return "Pont Hue injoignable."

    try:
        target_id = None
        target_type = None

        # 1. Recherche dans les GROUPES (prioritaire)
        groups = bridge.get_group()
        for gid, ginfo in groups.items():
            if cible.lower() in ginfo["name"].lower():
                target_id = int(gid)
                target_type = "group"
                break

        # 2. Si pas trouvé, recherche dans les LUMIÈRES individuelles
        if not target_id:
            lights = bridge.get_light_objects("name")
            for lname in lights:
                if cible.lower() in lname.lower():
                    target_id = lname  # Pour phue, l'ID peut être le nom
                    target_type = "light"
                    break

        if not target_id:
            return f"Lumière ou pièce '{cible}' introuvable."

        # 3. Exécution de l'action

        if action == "allumer":
            if target_type == "group":
                bridge.set_group(target_id, "on", True)
            else:
                bridge.set_light(target_id, "on", True)

        elif action == "eteindre":
            if target_type == "group":
                bridge.set_group(target_id, "on", False)
            else:
                bridge.set_light(target_id, "on", False)

        elif action == "couleur":
            xy = COULEURS_HUE.get(valeur.lower())
            if xy:
                if target_type == "group":
                    bridge.set_group(target_id, "xy", xy)
                else:
                    bridge.set_light(target_id, "xy", xy)
            else:
                return f"Couleur '{valeur}' inconnue."

        elif action == "luminosite":
            # Hue gère la luminosité de 0 à 254
            # On convertit le % utilisateur (0-100) en byte (0-254)
            if valeur:
                bri = int(int(valeur) * 2.54)
                # Bornage de sécurité
                bri = max(0, min(254, bri))
            else:
                bri = 254  # Max par défaut

            if target_type == "group":
                bridge.set_group(target_id, "bri", bri)
            else:
                bridge.set_light(target_id, "bri", bri)

        return "Fait."

    except Exception as e:
        return f"Erreur Hue: {e}"
