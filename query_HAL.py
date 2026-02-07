import requests
import os
from bs4 import BeautifulSoup
from collections import defaultdict

# --- CONFIGURATION ---
TEMPLATE_FILE = "publications_empty.html"
OUTPUT_FILE = "publications.html"

# Added docSubType_s to the field list
HAL_API_URL = (
    "https://api.archives-ouvertes.fr/search/?"
    "q=authIdHal_s:youwan&"
    "sort=producedDateY_i desc, docType_s asc&"
    "rows=1000&"
    "fl=title_s,authFullName_s,producedDateY_i,docType_s,docSubType_s,label_s,uri_s,files_s,halId_s&"
    "wt=json"
)

# REVISED CATEGORY MAPPING
# We will check docType_s first, but override based on docSubType_s
MAIN_TYPE_MAPPING = {
    "ART": "Journal articles",
    "COMM": "Conference papers",
    "POSTER": "Posters",
}

SUB_TYPE_MAPPING = {
    "PREPRINT": "Preprints",
    "WORKINGPAPER": "Preprints",
}

DEFAULT_CAT = "Documents associated with scientific events"

CATEGORY_ORDER = [
    "Journal articles",
    "Conference papers",
    "Posters",
    "Preprints",
    "Documents associated with scientific events"
]

def get_category(doc):
    """Logic to determine category based on Type and SubType."""
    doc_type = doc.get('docType_s')
    doc_sub_type = doc.get('docSubType_s') # List or string depending on API response

    # Handle if docSubType_s is a list (HAL sometimes returns it as such)
    sub_type = doc_sub_type[0] if isinstance(doc_sub_type, list) else doc_sub_type

    # 1. Check SubType first (Preprints/Working Papers)
    if sub_type in SUB_TYPE_MAPPING:
        return SUB_TYPE_MAPPING[sub_type]
    
    # 2. Check specific check for PREPRINT docType if subtype is missing
    if doc_type == "PREPRINT":
        return "Preprints"

    # 3. Check Main Type Mapping
    if doc_type in MAIN_TYPE_MAPPING:
        return MAIN_TYPE_MAPPING[doc_type]

    # 4. Fallback
    return DEFAULT_CAT

def build_page():
    print(f"🚀 Calling: {HAL_API_URL}")
    try:
        response = requests.get(HAL_API_URL)
        docs = response.json().get('response', {}).get('docs', [])
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Grouping
    grouped_data = defaultdict(lambda: defaultdict(list))
    for doc in docs:
        year = doc.get('producedDateY_i', "Unknown")
        cat_label = get_category(doc)
        grouped_data[year][cat_label].append(doc)

    # HTML Construction
    if not os.path.exists(TEMPLATE_FILE): return
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        main_soup = BeautifulSoup(f, "html.parser")

    container = main_soup.find("div", class_="container_publications")
    container.clear()

    for year in sorted(grouped_data.keys(), reverse=True):
        year_p = main_soup.new_tag("p", attrs={"class": "Rubrique"})
        year_p.string = str(year)
        container.append(year_p)

        year_cats = grouped_data[year]
        for cat_name in CATEGORY_ORDER:
            if cat_name in year_cats:
                sub_p = main_soup.new_tag("p", attrs={"class": "SousRubrique"})
                sub_p.string = cat_name
                container.append(sub_p)

                for doc in year_cats[cat_name]:
                    dl = create_publication_dl(main_soup, doc)
                    container.append(dl)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(str(main_soup))
    print(f"✅ Success! Generated {OUTPUT_FILE}")

def create_publication_dl(soup, doc):
    dl = soup.new_tag("dl", attrs={"class": "NoticeRes"})
    
    # Title
    dt_t = soup.new_tag("dt", attrs={"class": "ChampRes"})
    dt_t.string = "titre"
    dd_t = soup.new_tag("dd", attrs={"class": "ValeurRes Titre"})
    a_t = soup.new_tag("a", href=doc.get('uri_s'), target="_blank")
    a_t.string = doc.get('title_s', [''])[0]
    dd_t.append(a_t)
    
    # Authors
    dt_a = soup.new_tag("dt", attrs={"class": "ChampRes"})
    dt_a.string = "auteur"
    dd_a = soup.new_tag("dd", attrs={"class": "ValeurRes Auteurs"})
    dd_a.string = ", ".join(doc.get('authFullName_s', []))

    # Article
    dt_d = soup.new_tag("dt", attrs={"class": "ChampRes"})
    dt_d.string = "article"
    dd_d = soup.new_tag("dd", attrs={"class": "ValeurRes article"})
    full_label = doc.get('label_s', '')
    title_text = doc.get('title_s', [''])[0]
    details = full_label.split(title_text)[-1].strip(". ") if title_text in full_label else full_label
    venue_i = soup.new_tag("i")
    venue_i.append(BeautifulSoup(details, "html.parser"))
    dd_d.append(venue_i)

    # Links
    dt_l = soup.new_tag("dt", attrs={"class": "ChampRes"})
    dt_l.string = "Accès au texte intégral et bibtex"
    dd_l = soup.new_tag("dd", attrs={"class": "ValeurRes Fichier_joint"})
    
    if doc.get('files_s'):
        pdf_a = soup.new_tag("a", href=doc['files_s'][0], target="_blank")
        pdf_a.string = "[PDF]"
        dd_l.append(pdf_a); dd_l.append(" ") 

    hal_id = doc.get('halId_s') or doc.get('uri_s', '').split('/')[-1].split('v')[0]
    bib_a = soup.new_tag("a", href=f"https://hal.science/{hal_id}/bibtex", target="_blank")
    bib_a.string = "[BibTeX]"
    dd_l.append(bib_a)

    dl.extend([dt_t, dd_t, dt_a, dd_a, dt_d, dd_d, dt_l, dd_l])
    return dl

if __name__ == "__main__":
    build_page()