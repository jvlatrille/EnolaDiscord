"""
================================================================================
@fichier      : src/tools/wiz.py
@description  : Contrôle WiZ via UDP avec Retry (Tentatives multiples).
================================================================================
"""
import socket
import json
import time
from config import WIZ_PLUG_IP

def envoyer_commande_udp(payload, ip, port=38899, tentatives=3):
    """
    Envoie un payload JSON en UDP avec plusieurs tentatives.
    Retourne la réponse JSON ou None si échec après N essais.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0) # 2 secondes d'attente max par essai
    
    message = json.dumps(payload).encode('utf-8')
    
    for i in range(tentatives):
        try:
            # print(f"🔌 WiZ: Envoi essai {i+1}/{tentatives}...")
            sock.sendto(message, (ip, port))
            
            # Attente réponse
            data, _ = sock.recvfrom(1024)
            reponse = json.loads(data.decode('utf-8'))
            sock.close()
            return reponse

        except socket.timeout:
            # Si timeout, on attend un tout petit peu et on recommence
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ Erreur WiZ (Essai {i+1}): {e}")
            break
            
    sock.close()
    return None

def commander_prise_reel(action: str) -> str:
    """
    Envoie un ordre à la prise WiZ ou demande son état.
    Action: "allumer", "eteindre", "statut".
    """
    if not WIZ_PLUG_IP:
        return "IP de la prise WiZ non configurée dans le .env."

    try:
        # --- CAS 1 : Lecture d'état (Statut) ---
        if action == "statut":
            payload = {"method": "getPilot", "params": {}}
            reponse = envoyer_commande_udp(payload, WIZ_PLUG_IP)
            
            if reponse and "result" in reponse and "state" in reponse["result"]:
                etat_bool = reponse["result"]["state"]
                etat_str = "Allumée 🟢" if etat_bool else "Éteinte 🔴"
                return f"La prise 'PC' est actuellement : {etat_str}"
            else:
                return "Je n'arrive pas à joindre la prise (après 3 tentatives)."

        # --- CAS 2 : Action (Allumer/Eteindre) ---
        elif action in ["allumer", "eteindre"]:
            etat = True if action == "allumer" else False
            payload = {"method": "setPilot", "params": {"state": etat}}
            
            reponse = envoyer_commande_udp(payload, WIZ_PLUG_IP)
            
            if reponse and "result" in reponse and "success" in reponse["result"]:
                 if reponse["result"]["success"]:
                     return f"Prise {action}e avec succès."
            
            # Parfois WiZ répond juste { "method": "setPilot", "env": "pro" ... } sans success explicit
            # Si on a une réponse, c'est que l'ordre est passé
            if reponse:
                return f"Ordre envoyé (Prise {action}e)."
            
            return "La prise ne répond pas. Vérifie qu'elle est bien branchée."
        
        else:
            return f"Action inconnue : {action}"

    except Exception as e:
        return f"Erreur technique WiZ : {e}"