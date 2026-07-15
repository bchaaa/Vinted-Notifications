#!/usr/bin/env python3
"""Re-checker AUTOMATIQUE de liens Vinted "morts" (compagnon du bot)."""

import os
import re
import sys
import json
import time
import html
import sqlite3

import requests

try:
    from pyVintedVN import requester  # session anti-bot partagée avec le bot
    HAVE_REQUESTER = True
except Exception:
    requester = None
    HAVE_REQUESTER = False

WINDOW_HOURS = float(os.environ.get("RECHECK_WINDOW_HOURS", "3"))
MAX_TRACK = int(os.environ.get("RECHECK_MAX_TRACK", "60"))
INTERVAL = int(os.environ.get("RECHECK_INTERVAL", "300"))
ITEM_DELAY = float(os.environ.get("RECHECK_ITEM_DELAY", "3"))
DB_PATH = os.environ.get("RECHECK_DB_PATH", "./data/vinted_notifications.db")
WATCHLIST_FILE = os.environ.get("RECHECK_WATCHLIST", "recheck_watchlist.txt")
STATE_FILE = os.environ.get("RECHECK_STATE", "recheck_state.json")

ITEM_ID_RE = re.compile(r"/items/(\d+)")
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


def read_param_from_bot_db(key):
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute("SELECT value FROM parameters WHERE key=?", (key,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    except Exception:
        return None


def read_recent_items():
    cutoff = time.time() - WINDOW_HOURS * 3600
    out = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT item, title, price, currency FROM items "
                "WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                (cutoff, MAX_TRACK),
            )
            for item_id, title, price, currency in cur.fetchall():
                out[str(item_id)] = {
                    "title": title or "annonce",
                    "price": price,
                    "currency": currency or "",
                }
        finally:
            conn.close()
    except Exception as e:
        print(f"[!] Lecture base du bot impossible ({DB_PATH}) : {e}")
    return out


def telegram_config():
    token = os.environ.get("TELEGRAM_TOKEN") or read_param_from_bot_db("telegram_token")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or read_param_from_bot_db("telegram_chat_id")
    return token, chat


def extract_id(text):
    text = (text or "").strip()
    if not text or text.startswith("#"):
        return None
    m = ITEM_ID_RE.search(text)
    if m:
        return m.group(1)
    return text if text.isdigit() else None


def item_url(item_id):
    return f"https://www.vinted.fr/items/{item_id}"


def fetch(url):
    if HAVE_REQUESTER:
        return requester.get(url)
    return requests.get(url, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=20)


def check_available(item_id):
    try:
        r = fetch(f"https://www.vinted.fr/api/v2/items/{item_id}?localization=fr")
    except Exception:
        return None
    status = getattr(r, "status_code", None)
    if status == 200:
        return True
    if status in (404, 410):
        return False
    return None


def telegram_send(token, chat, text):
    if not token or not chat:
        print("[!] Token/chat Telegram introuvables. Message :")
        print("    " + text.replace("\n", "\n    "))
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "false",
            },
            timeout=20,
        )
    except Exception as e:
        print(f"[!] Envoi Telegram échoué : {e}")


def price_text(meta):
    price = meta.get("price")
    if price in (None, "", 0):
        return ""
    return f" — {price} {meta.get('currency', '')}".rstrip()


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"[!] Sauvegarde de l'état échouée : {e}")


def load_manual_watchlist():
    ids = {}
    try:
        with open(WATCHLIST_FILE, encoding="utf-8") as f:
            for line in f:
                iid = extract_id(line)
                if iid:
                    ids[iid] = {"title": "annonce épinglée", "price": None, "currency": ""}
    except FileNotFoundError:
        pass
    for arg in sys.argv[1:]:
        iid = extract_id(arg)
        if iid:
            ids[iid] = {"title": "annonce épinglée", "price": None, "currency": ""}
    return ids


def main():
    token, chat = telegram_config()
    print(f"[i] Re-checker AUTO démarré. Fenêtre={WINDOW_HOURS}h, max suivi={MAX_TRACK}, tour={INTERVAL}s.")
    print(f"[i] pyVintedVN : {'OK' if HAVE_REQUESTER else 'ABSENT (fallback requests)'}")
    print(f"[i] Telegram : {'configuré' if (token and chat) else 'NON configuré'}")

    state = load_state()

    while True:
        now = time.time()
        candidates = read_recent_items()
        candidates.update(load_manual_watchlist())

        for iid, meta in candidates.items():
            entry = state.get(iid)
            if entry is None:
                state[iid] = {"first_seen": now, "was_pulled": False, "resolved": False, "meta": meta}
            else:
                entry["meta"] = meta

        checked = 0
        for iid, entry in list(state.items()):
            if entry.get("resolved") or (now - entry.get("first_seen", now) > WINDOW_HOURS * 3600):
                state.pop(iid, None)
                continue

            dispo = check_available(iid)
            checked += 1
            if dispo is False:
                if not entry["was_pulled"]:
                    print(f"[!] Retiree (mise en revue ?) : {iid}")
                entry["was_pulled"] = True
            elif dispo is True:
                if entry["was_pulled"]:
                    meta = entry.get("meta", {})
                    money = "\U0001F911" * 7
                    msg = (
                        f"{money} DE NOUVEAU EN LIGNE\n"
                        f"<b>{html.escape(str(meta.get('title', 'annonce')))}</b>"
                        f"{html.escape(price_text(meta))}\n{item_url(iid)}"
                    )
                    telegram_send(token, chat, msg)
                    print(f"[✓] Retour en ligne signale : {iid}")
                    entry["resolved"] = True

            time.sleep(ITEM_DELAY)

        save_state(state)
        print(f"[i] Tour termine ({checked} verifiees, {len(state)} suivies). Pause {INTERVAL}s.")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
