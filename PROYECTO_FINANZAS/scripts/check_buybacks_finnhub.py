#!/usr/bin/env python3
# scripts/check_buybacks_finnhub.py
import os
import json
import time
import requests
import re
from datetime import datetime, timedelta
from send_email import send_email

# Config (via env vars)
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
LOOKBACK_DAYS = int(os.getenv('LOOKBACK_DAYS', '7'))  # ventana en días
TICKERS_FILE = os.getenv('TICKERS_FILE', 'empresas.txt')
NOTIFIED_FILE = os.getenv('NOTIFIED_FILE', 'notified.json')

HEADERS = {'User-Agent': 'buyback-detector/1.0'}
MONEY_RE = re.compile(r'(\$?\s?)([0-9]{1,3}(?:[,\.\s][0-9]{3})*(?:\.[0-9]+)?)(\s?(B|M|K|bn|m|k)?)', re.IGNORECASE)
FINNHUB_BASE = 'https://finnhub.io/api/v1'

def load_tickers(path=TICKERS_FILE):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [l.strip() for l in f if l.strip() and not l.startswith('#')]

def load_notified(path=NOTIFIED_FILE):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_notified(data, path=NOTIFIED_FILE):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def parse_money(text):
    if not text:
        return None
    m = MONEY_RE.search(text.replace('\xa0',' '))
    if not m:
        return None
    num_str = m.group(2).replace(',', '').replace(' ', '')
    suf = (m.group(4) or '').upper()
    try:
        num = float(num_str)
    except:
        return None
    mult = 1.0
    if 'B' in suf:
        mult = 1_000_000_000
    elif 'M' in suf:
        mult = 1_000_000
    elif 'K' in suf:
        mult = 1_000
    return num * mult

def make_event_id(symbol, date, desc):
    return f"{symbol}__{date}__{abs(hash(desc[:120]))}"

def fetch_corporate_actions(symbol, from_date, to_date):
    url = f"{FINNHUB_BASE}/corporate-actions"
    params = {'symbol': symbol, 'from': from_date, 'to': to_date, 'token': FINNHUB_API_KEY}
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_company_profile(symbol):
    url = f"{FINNHUB_BASE}/stock/profile2"
    params = {'symbol': symbol, 'token': FINNHUB_API_KEY}
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return {}
    return r.json()

def main():
    if not FINNHUB_API_KEY:
        print("ERROR: FINNHUB_API_KEY no configurada en variables de entorno.")
        return 2

    tickers = load_tickers()
    if not tickers:
        print("No hay tickers en", TICKERS_FILE)
        return 0

    notified = load_notified()
    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=LOOKBACK_DAYS)
    from_str, to_str = from_date.isoformat(), to_date.isoformat()

    found_events = []
    for ticker in tickers:
        try:
            print(f"[{datetime.utcnow().isoformat()}] Consultando {ticker} {from_str}..{to_str}")
            actions = fetch_corporate_actions(ticker, from_str, to_str) or []
            profile = fetch_company_profile(ticker)
            marketcap = profile.get('marketCapitalization')  # puede ser None
            for evt in actions:
                desc = evt.get('description') or evt.get('text') or ''
                date = evt.get('date') or evt.get('exDate') or to_str
                action_lower = (evt.get('action') or '').lower()
                # detectar buyback
                if ('buyback' in action_lower) or any(k in desc.lower() for k in ['buyback','repurchase','recompra']):
                    amount = None
                    if evt.get('amount'):
                        try:
                            amount = float(evt.get('amount'))
                        except:
                            amount = None
                    if not amount:
                        amount = parse_money(desc)
                    pct = None
                    if amount and marketcap:
                        try:
                            mc = float(marketcap)
                            if mc < 1e6:
                                mc *= 1_000_000
                            pct = (amount / mc) * 100.0
                        except:
                            pct = None
                    event_id = make_event_id(ticker, date, desc)
                    if event_id in notified:
                        continue
                    text = f"BUYBACK DETECTADO\n{ticker}\nFecha: {date}\n"
                    if desc:
                        text += f"Descripción: {desc}\n"
                    if amount:
                        text += f"Importe estimado: {amount:,.0f} USD\n"
                    if pct is not None:
                        text += f"≈ {pct:.2f}% del market cap\n"
                    if evt.get('url'):
                        text += f"URL: {evt.get('url')}\n"
                    found_events.append({'id': event_id, 'text': text})
            time.sleep(0.6)  # respetar rate limit
        except Exception as e:
            print(f"Error consultando {ticker}: {e}")

    if not found_events:
        print("No se detectaron buybacks nuevos.")
        return 0

    # Agrupar en un solo correo
    body = "\n\n---\n\n".join([e['text'] for e in found_events])
    subject = f"[Buyback detector] {len(found_events)} evento(s) detectado(s) - {datetime.utcnow().date().isoformat()}"

    try:
        code, resp = send_email(subject, body)
        print("SendGrid response code:", code)
    except Exception as e:
        print("Error enviando email:", e)
        return 1

    # marcar como notificado
    now = datetime.utcnow().isoformat()
    for e in found_events:
        notified[e['id']] = {'notified_at': now}
    save_notified(notified)
    print(f"{len(found_events)} eventos notificados y guardados en {NOTIFIED_FILE}")
    return 0

if __name__ == '__main__':
    main()
