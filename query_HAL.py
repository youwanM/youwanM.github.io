#!/usr/bin/env python3
"""Génère publications.html à partir de HAL (idHAL « youwan »).

Usage : python query_HAL.py
Le modèle est publications_empty.html ; la page existante n'est jamais
écrasée si HAL est injoignable ou ne renvoie aucun résultat.
"""
import os
import re
import sys
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

TEMPLATE_FILE = "publications_empty.html"
OUTPUT_FILE = "publications.html"
IDHAL = "youwan"
ME = "Youwan Mahé"  # affiché en gras dans les listes d'auteurs

HAL_API_URL = "https://api.archives-ouvertes.fr/search/"
HAL_PARAMS = {
    "q": f"authIdHal_s:{IDHAL}",
    "sort": "producedDate_tdate desc",
    "rows": 1000,
    "fl": ("title_s,authFullName_s,producedDateY_i,producedDate_tdate,docType_s,"
           "docSubType_s,label_s,uri_s,files_s,halId_s,doiId_s,language_s"),
    "wt": "json",
}

MAIN_TYPE_MAPPING = {"ART": "Journal articles", "COMM": "Conference papers", "POSTER": "Posters"}
SUB_TYPE_MAPPING = {"PREPRINT": "Preprints", "WORKINGPAPER": "Preprints"}
DEFAULT_CAT = "Talks & presentations"  # anciennement « Documents associated with scientific events »

# Blocs de la page : (titre, catégories). Un bloc sans document n'est pas affiché.
SECTIONS = [
    ("Peer-reviewed publications", ["Journal articles", "Conference papers"]),
    ("Preprints", ["Preprints"]),
    ("Posters & talks", ["Posters", "Talks & presentations"]),
]

# « Nom de la revue ou conférence, Apr 2026, Lieu… » : seul le nom est mis en italique
VENUE_SPLIT = re.compile(r"^(.*?),\s*((?:[A-Z][a-z]{2}\s)?\d{4}\b.*)$", re.S)


def get_category(doc):
    sub = doc.get("docSubType_s")
    sub = sub[0] if isinstance(sub, list) else sub
    if sub in SUB_TYPE_MAPPING:
        return SUB_TYPE_MAPPING[sub]
    if doc.get("docType_s") == "PREPRINT":
        return "Preprints"
    return MAIN_TYPE_MAPPING.get(doc.get("docType_s"), DEFAULT_CAT)


def first(value, default=""):
    if isinstance(value, list):
        return value[0] if value else default
    return value or default


def venue_parts(doc, title):
    """Sépare le libellé HAL en (nom du support, reste), sans id HAL ni DOI."""
    label = BeautifulSoup(doc.get("label_s", ""), "html.parser").get_text()
    details = label.split(title)[-1] if title and title in label else label
    details = re.sub(r"\s*⟨hal-[^⟩]*⟩", "", details)  # déjà présent dans les liens
    details = re.sub(r"\s*⟨10\.[^⟩]*⟩", "", details)  # le DOI est ajouté proprement ensuite
    details = details.strip(". ")
    m = VENUE_SPLIT.match(details)
    if not m:
        return details, ""
    rest = re.sub(r"\.\s*\d{4}$", "", m.group(2).strip(". "))  # « …, France. 2026 » : année déjà indiquée
    return m.group(1), rest


def link(soup, href, text, **attrs):
    a = soup.new_tag("a", href=href, target="_blank", rel="noopener", **attrs)
    a.string = text
    return a


def create_publication_dl(soup, doc):
    dl = soup.new_tag("dl", attrs={"class": "NoticeRes"})
    title = first(doc.get("title_s"))
    uri = doc.get("uri_s", "")

    dt_t = soup.new_tag("dt", attrs={"class": "ChampRes"}); dt_t.string = "titre"
    dd_t = soup.new_tag("dd", attrs={"class": "ValeurRes Titre"})
    if uri:
        extra = {"lang": "fr"} if "fr" in (doc.get("language_s") or []) else {}
        dd_t.append(link(soup, uri, title, **extra))
    else:
        dd_t.string = title

    dt_a = soup.new_tag("dt", attrs={"class": "ChampRes"}); dt_a.string = "auteur"
    dd_a = soup.new_tag("dd", attrs={"class": "ValeurRes Auteurs"})
    for i, name in enumerate(doc.get("authFullName_s", [])):
        if i:
            dd_a.append(", ")
        if name.strip() == ME:
            b = soup.new_tag("b"); b.string = name; dd_a.append(b)
        else:
            dd_a.append(name)

    dt_d = soup.new_tag("dt", attrs={"class": "ChampRes"}); dt_d.string = "article"
    dd_d = soup.new_tag("dd", attrs={"class": "ValeurRes article"})
    venue, rest = venue_parts(doc, title)
    if venue:
        i_tag = soup.new_tag("i"); i_tag.string = venue; dd_d.append(i_tag)
    if rest:
        dd_d.append(", " + rest)
    doi = first(doc.get("doiId_s"))
    if doi:
        dd_d.append(". ")
        dd_d.append(link(soup, f"https://doi.org/{doi}", f"doi:{doi}"))

    dt_l = soup.new_tag("dt", attrs={"class": "ChampRes"}); dt_l.string = "Accès au texte intégral et bibtex"
    dd_l = soup.new_tag("dd", attrs={"class": "ValeurRes Fichier_joint"})
    if doc.get("files_s"):
        dd_l.append(link(soup, doc["files_s"][0], "[PDF]"))
        dd_l.append(" ")
    hal_id = doc.get("halId_s") or re.sub(r"v\d+$", "", uri.rsplit("/", 1)[-1])
    if hal_id:
        dd_l.append(link(soup, f"https://hal.science/{hal_id}/bibtex", "[BibTeX]"))

    dl.extend([dt_t, dd_t, dt_a, dd_a, dt_d, dd_d, dt_l, dd_l])
    return dl


def render_page(docs, template_path=TEMPLATE_FILE, output_path=OUTPUT_FILE):
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Modèle introuvable : {template_path}")
    with open(template_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    container = soup.find("div", class_="container_publications")
    if container is None:
        raise ValueError("Le modèle ne contient pas <div class=\"container_publications\">")
    container.clear()

    docs = sorted(docs, key=lambda d: d.get("producedDate_tdate", ""), reverse=True)
    for section_title, cats in SECTIONS:
        years = defaultdict(lambda: defaultdict(list))
        for doc in docs:
            cat = get_category(doc)
            if cat in cats:
                years[doc.get("producedDateY_i") or 0][cat].append(doc)
        if not years:
            continue
        h2 = soup.new_tag("h2", attrs={"class": "PartieRes"}); h2.string = section_title
        container.append(h2)
        for year in sorted(years, reverse=True):  # clés toutes entières : tri sûr
            p = soup.new_tag("p", attrs={"class": "Rubrique"})
            p.string = str(year) if year else "Undated"
            container.append(p)
            for cat in cats:
                if cat not in years[year]:
                    continue
                if len(cats) > 1:
                    sp = soup.new_tag("p", attrs={"class": "SousRubrique"}); sp.string = cat
                    container.append(sp)
                for doc in years[year][cat]:
                    container.append(create_publication_dl(soup, doc))

    tmp = output_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(str(soup))
    os.replace(tmp, output_path)  # écriture atomique
    return len(docs)


def main():
    try:
        r = requests.get(HAL_API_URL, params=HAL_PARAMS, timeout=20)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
    except (requests.RequestException, ValueError) as e:
        print(f"❌ HAL injoignable ou réponse invalide : {e}\n   {OUTPUT_FILE} n'a pas été modifié.")
        return 1
    if not docs:
        print(f"⚠️ HAL n'a renvoyé aucun document : {OUTPUT_FILE} n'a pas été modifié.")
        return 1
    try:
        n = render_page(docs)
    except (OSError, ValueError) as e:
        print(f"❌ {e}")
        return 1
    print(f"✅ {OUTPUT_FILE} généré ({n} documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
