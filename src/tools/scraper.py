import os
import json
import requests
from bs4 import BeautifulSoup

# --- Configuration ---
URL_ARKNIGHTS = "https://endfield.gg/arknights-endfield-codes/"
URL_STRINOVA = "https://www.pcgamesn.com/strinova/codes"

# Fichier mémoire
MEMORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../assets/codes_memory.json"))

def _charger_memoire():
    """Charge le JSON (liste de strings)."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception as e:
        print(f"⚠️ Erreur lecture mémoire : {e}")
        return []

def _sauvegarder_memoire(codes_connus):
    try:
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w") as f:
            json.dump(codes_connus, f, indent=4)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde mémoire : {e}")

def scrape_arknights():
    """Scraper spécifique pour Arknights Endfield (Tableaux)"""
    codes = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(URL_ARKNIGHTS, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for row in soup.find_all('tr'):
                cols = row.find_all('td')
                if cols:
                    raw_text = cols[0].get_text(" ", strip=True)
                    potential_code = raw_text.split(" ")[0].replace(":", "").strip()
                    if potential_code.isupper() and len(potential_code) > 3 and "CODE" not in potential_code:
                        codes.append(potential_code)
    except Exception as e:
        print(f"⚠️ Erreur Arknights : {e}")
    return list(set(codes))

def scrape_strinova():
    """Scraper spécifique pour Strinova (Listes à puces PCGamesN)"""
    codes = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(URL_STRINOVA, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # PCGamesN met souvent les codes en gras (strong) dans des listes (li)
            # On cherche tous les <li> qui contiennent un <strong>
            for li in soup.find_all('li'):
                strong = li.find('strong')
                if strong:
                    text = strong.get_text(strip=True)
                    # Filtres Strinova (accepte Minuscules/Majuscules, pas d'espaces)
                    if (len(text) > 3 
                        and " " not in text 
                        and "Code" not in text 
                        and "Reward" not in text):
                        codes.append(text)
    except Exception as e:
        print(f"⚠️ Erreur Strinova : {e}")
    return list(set(codes))

def check_new_codes():
    """
    Vérifie TOUS les jeux.
    Retourne une liste de dictionnaires : [{'game': 'NomJeu', 'code': 'XYZ'}, ...]
    """
    nouveaux_trouvailles = []
    memoire_actuelle = _charger_memoire()
    
    # 1. ARKNIGHTS
    codes_ark = scrape_arknights()
    for code in codes_ark:
        id_unique = f"ARKNIGHTS_{code}" # Préfixe pour unicité
        if id_unique not in memoire_actuelle:
            nouveaux_trouvailles.append({"game": "Arknights: Endfield", "code": code})
            memoire_actuelle.append(id_unique)

    # 2. STRINOVA
    codes_stri = scrape_strinova()
    for code in codes_stri:
        id_unique = f"STRINOVA_{code}"
        if id_unique not in memoire_actuelle:
            nouveaux_trouvailles.append({"game": "Strinova", "code": code})
            memoire_actuelle.append(id_unique)

    # Sauvegarde si on a trouvé des trucs
    if nouveaux_trouvailles:
        _sauvegarder_memoire(memoire_actuelle)
        
    return nouveaux_trouvailles

if __name__ == "__main__":
    print("🔍 Test multi-jeux...")
    print(check_new_codes())