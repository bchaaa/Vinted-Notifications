# Gestion des recherches Vinted

Les recherches surveillées par le bot (iPhone, PS5, etc.) sont définies dans
[`config/queries.yaml`](config/queries.yaml), versionné dans ce repo.

## Format

```yaml
iphone:
  categorie: 3661          # ID de catégorie Vinted (catalog[])
  recherches:
    - nom: iphone 16 pro max
      prix_min: 150
      prix_max: 310
    - nom: iphone 15
      prix_min: 100
      prix_max: 250

ps5:
  categorie: 3025
  platform: 1281           # optionnel : video_game_platform_ids[]
  recherches:
    - nom: ps5
      prix_min: 50
      prix_max: 310
```

Chaque section (`iphone`, `ps5`, ...) a une `categorie` (et éventuellement un
`platform`), et une liste de `recherches` avec un nom et une fourchette de
prix. Le nom sert à la fois de `search_text` Vinted et de nom affiché sur la
page `/queries`.

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
