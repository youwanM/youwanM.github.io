import requests
from bs4 import BeautifulSoup
import os

# --- CONFIGURATION ---
TEMPLATE_FILE = "publications_empty.html"
OUTPUT_FILE = "publications.html"
HAL_URL = (
    "https://haltools.inria.fr/Public/afficheRequetePubli.php?"
    "idHal=youwan&CB_auteur=oui&CB_titre=oui&CB_article=oui&"
    "langue=Anglais&tri_exp=annee_publi&tri_exp2=typdoc&"
    "tri_exp3=date_publi&ordre_aff=TA&Fen=Aff&"
    "css=https://youwanmahe.fr/assets/css/stylepubli.css"
)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def build_page():
    # 1. Fetch HAL Content
    print("Fetching data from HAL...")
    try:
        response = requests.get(HAL_URL, headers=HEADERS)
        response.raise_for_status()
        response.encoding = "utf-8"
        hal_soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract everything inside <body>
        if hal_soup.body:
            # We convert it back to a soup object to ensure it's clean
            hal_content = BeautifulSoup(hal_soup.body.decode_contents(), "html.parser")
        else:
            print("Error: Could not find <body> in HAL response.")
            return
    except Exception as e:
        print(f"Error fetching HAL: {e}")
        return

    # 2. Load the Template
    print(f"Loading template: {TEMPLATE_FILE}")
    if not os.path.exists(TEMPLATE_FILE):
        print(f"Error: {TEMPLATE_FILE} not found!")
        return

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        main_soup = BeautifulSoup(f, "html.parser")

    # 3. Find the injection point
    container = main_soup.find("div", class_="container_publications")
    if not container:
        print("Error: Could not find <div class='container_publications'> in template.")
        return

    # 4. Inject the content
    print("Injecting publications...")
    container.clear() # Make sure it's empty
    container.append(hal_content)

    # 5. Save the final file
    print(f"Saving final file: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Use str() instead of prettify() to keep the HAL formatting intact
        f.write(str(main_soup))

    print("Success! Your publications page is ready.")

if __name__ == "__main__":
    build_page()