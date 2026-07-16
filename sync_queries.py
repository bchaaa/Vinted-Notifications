#!/usr/bin/env python3
"""Synchronise la base du bot (queries + parametres) avec config/queries.yaml.

Remplace entièrement le contenu de la table `queries` à chaque exécution
(idempotent) : relancer ce script plusieurs fois avec le même YAML ne crée
pas de doublons. Met aussi à jour les paramètres listés sous `parametres:`
(items_per_query, query_refresh_delay, banwords) si présents dans le YAML.
"""

import argparse
import os
import sqlite3
import sys
from urllib.parse import urlencode

import yaml

DB_PATH = os.environ.get("VINTED_DB_PATH", "./data/vinted_notifications.db")
CONFIG_PATH = os.environ.get("VINTED_QUERIES_CONFIG", "config/queries.yaml")
BASE_URL = "https://www.vinted.fr/catalog"
CURRENCY = "EUR"


def build_query_url(recherche, categorie=None, platform=None):
    params = {}
    if categorie is not None:
        params["catalog[]"] = categorie

    texte = recherche.get("texte")
    if texte:
        params["search_text"] = texte

    params["price_from"] = recherche["prix_min"]
    params["price_to"] = recherche["prix_max"]
    params["order"] = "newest_first"
    params["currency"] = CURRENCY

    if platform is not None:
        params["video_game_platform_ids[]"] = platform

    return f"{BASE_URL}?{urlencode(params, doseq=True)}"


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_queries(config):
    queries = []
    for section_name, section in config.items():
        if section_name == "parametres":
            continue
        categorie = section.get("categorie")
        platform = section.get("platform")
        for recherche in section.get("recherches", []):
            queries.append(
                {
                    "name": recherche["nom"],
                    "url": build_query_url(recherche, categorie, platform),
                }
            )
    return queries


def load_parametres(config):
    parametres = dict(config.get("parametres") or {})
    if "banwords" in parametres and isinstance(parametres["banwords"], list):
        parametres["banwords"] = " ||| ".join(parametres["banwords"])
    return parametres


def sync(queries, parametres, db_path, dry_run=False):
    if dry_run:
        print(f"[dry-run] {len(queries)} requête(s) seraient synchronisées vers {db_path} :")
        for q in queries:
            print(f"  - {q['name']}: {q['url']}")
        if parametres:
            print(f"[dry-run] Paramètres qui seraient mis à jour : {list(parametres.keys())}")
        return

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        # Remplacement complet : on vide la table puis on réinsère depuis le YAML,
        # ce qui garantit l'idempotence et évite les doublons.
        cursor.execute("DELETE FROM items")
        cursor.execute("DELETE FROM queries")
        for q in queries:
            cursor.execute(
                "INSERT INTO queries (query, last_item, query_name) VALUES (?, NULL, ?)",
                (q["url"], q["name"]),
            )
        for key, value in parametres.items():
            cursor.execute(
                "UPDATE parameters SET value=? WHERE key=?", (str(value), key)
            )
        conn.commit()
        print(f"{len(queries)} requête(s) synchronisée(s) vers {db_path}.")
        if parametres:
            print(f"Paramètres mis à jour : {list(parametres.keys())}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=CONFIG_PATH, help="Chemin vers le fichier queries.yaml"
    )
    parser.add_argument(
        "--db", default=DB_PATH, help="Chemin vers la base SQLite du bot"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les requêtes générées sans toucher à la base",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Fichier de config introuvable : {args.config}", file=sys.stderr)
        sys.exit(1)

    config = load_config(args.config)
    queries = load_queries(config)
    parametres = load_parametres(config)

    if not queries:
        print("Aucune requête trouvée dans le fichier de config.", file=sys.stderr)
        sys.exit(1)

    sync(queries, parametres, args.db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
