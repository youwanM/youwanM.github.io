# youwanmahe.fr

Site statique basé sur le template **Browny** (ThemeSINE, licence gratuite : conserver le crédit si la licence l'exige).

## Mettre à jour
- **Pages** (`index`, `curriculum`, `community`, `outreach`) : éditer le HTML directement. La navigation et le pied de page sont dupliqués dans chaque fichier.
- **Publications** : ne pas éditer `publications.html`. Lancer `python query_HAL.py` (dépendances : `requests`, `beautifulsoup4`) ou laisser le workflow GitHub (`.github/workflows/update-publications.yml`, chaque lundi) le faire. `publications_empty.html` est le modèle ; il ne doit pas être indexé (voir `robots.txt`).
- **CV** : remplacer `assets/files/CV.pdf`.

## Fichiers CSS
`style.css` et `responsive.css` (template) ne sont pas modifiés. Les corrections sont dans `assets/css/custom.css`, chargé en dernier. `assets/css/stylepubli.css` ne concerne que la page Publications.
