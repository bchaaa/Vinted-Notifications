# Gestion des recherches Vinted

Les recherches surveillées par le bot (iPhone, PS5, etc.) sont définies dans
[`config/queries.yaml`](config/queries.yaml), versionné dans ce repo.

## Format

```yaml
iphone:
  categorie: 3661          # ID de catégorie Vinted (catalog[])
  recherches:
    - nom: iphone 16 pro max
      texte: iphone 16 pro max   # optionnel : search_text (absent = pas de texte)
      prix_min: 150
      prix_max: 310

ps5:
  categorie: 3025
  platform: 1281           # optionnel : video_game_platform_ids[]
  recherches:
    - nom: PS5 50-310      # pas de `texte` : parcourt juste la catégorie par prix
      prix_min: 50
      prix_max: 310

# Section "filet de sécurité" : pas de `categorie`, cherche sur tout Vinted.
# Utile pour rattraper les annonces mal classées par le vendeur.
filets:
  recherches:
    - nom: Filet iPhone (toutes catégories)
      texte: iphone
      prix_min: 40
      prix_max: 310

# Optionnel : réglages du bot synchronisés en même temps que les requêtes.
parametres:
  items_per_query: 40
  query_refresh_delay: 15
  banwords:
    - portable
    - coque
    - chargeur
```

Chaque section a une `categorie` optionnelle (absente = pas de filtre de
catégorie, donc un "filet de sécurité" qui cherche sur tout Vinted) et
éventuellement un `platform`. Chaque recherche a un `nom` (affiché sur
`/queries`) et une fourchette de prix ; le `texte` (search_text) est
optionnel — sans lui, la requête parcourt juste la catégorie/prix, ce qui
est utile quand la catégorie suffit à cibler (ex. PS5 précis).

La section `parametres` (optionnelle) permet de versionner `items_per_query`,
`query_refresh_delay` et `banwords` — le script les pousse dans la table
`parameters` (`banwords` est automatiquement joint avec le séparateur `|||`
attendu par le bot).

## Utilisation

1. Éditer `config/queries.yaml` (ajouter un modèle, changer un prix, etc.)
2. Lancer le script de synchronisation :

   ```bash
   pip install -r requirements.txt   # une seule fois, installe PyYAML
   python sync_queries.py
   ```

   Utiliser `--dry-run` pour vérifier ce qui serait généré sans toucher à la
   base :

   ```bash
   python sync_queries.py --dry-run
   ```

3. Vérifier le résultat sur la page `/queries` du bot.

Le script **remplace entièrement** le contenu de la table `queries` (et
l'historique d'items associé) à chaque exécution : relancer plusieurs fois
avec le même YAML ne crée pas de doublons. C'est l'équivalent versionné de
l'ancien script JS collé dans la console (`/remove_query/all` puis
`/add_query` en boucle).

Par défaut le script cible `./data/vinted_notifications.db` (le chemin utilisé
par le bot sur le Volume Railway). Pour cibler une autre base, utiliser
`--db chemin/vers/la.db` ou la variable d'environnement `VINTED_DB_PATH`.
