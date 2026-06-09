from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
import os
import requests
import time
import threading

app = Flask(__name__)
CORS(app) # Permite que o seu HTML local acesse o servidor

BASE_DIR = Path("c:/Apps/#5 SqueezeSniper-V4")
JSON_LATEST = BASE_DIR / "eAssets/dados_eassets/eassets_latest.json"
SIGNALS_LOG = BASE_DIR / "logs/signals.jsonl"

# Cache para dados macro para não banir o IP no Yahoo
macro_cache = {
    "macro_data": {},
    "fgi_data": {},
    "last_macro_update": 0.0,
    "last_fgi_update": 0.0
}

def update_macro_data():
    """Lógica interna de busca do Yahoo Finance (roda em background)"""
    symbols = {
        "VIX": "%5EVIX",
        "DXY": "DX-Y.NYB",
        "SP500": "%5EGSPC",
        "NASDAQ": "%5EIXIC",
        "GOLD": "GC%3DF"
    }
    
    results = {}
    for name, sym in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
            # User-agent para o Yahoo não bloquear a requisição
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=5)
            if r.ok:
                data = r.json()
                meta = data['chart']['result'][0]['meta']
                price = meta['regularMarketPrice']
                prev = meta.get('previousClose') or meta.get('chartPreviousClose')
                
                change = 0
                if price and prev:
                    change = ((price - prev) / prev) * 100
                
                results[name] = {
                    "price": price,
                    "change": change
                }
        except Exception as e:
            print(f"Erro ao buscar {name}: {e}")
            results[name] = {"price": None, "change": 0}
    
    return results

def update_fgi_data():
    """Lógica interna de busca do Fear & Greed (roda em background)"""
    try:
        r = requests.get('https://api.alternative.me/fng/?limit=1', timeout=5)
        if r.ok:
            d = r.json()
            val = d['data'][0]['value']
            label = d['data'][0]['value_classification']
            return {"value": val, "label": label}
    except Exception as e:
        print(f"Erro ao buscar Fear & Greed: {e}")
    return {"value": None, "label": "Error"}

def background_worker():
    """Trabalhador que mantém o cache sempre quente sem travar o request do usuário."""
    print("🕵️ Background Data Worker iniciado.")
    
    # Primeira carga imediata ao ligar o servidor
    macro_cache["macro_data"] = update_macro_data()
    macro_cache["last_macro_update"] = time.time()
    macro_cache["fgi_data"] = update_fgi_data()
    macro_cache["last_fgi_update"] = time.time()
    print("🚀 Primeira carga de dados externos concluída.")

    while True:
        # Atualiza Yahoo a cada 2 min
        if (time.time() - macro_cache["last_macro_update"]) > 120:
            macro_cache["macro_data"] = update_macro_data()
            macro_cache["last_macro_update"] = time.time()
            print("✅ Cache Macro (Yahoo) atualizado.")

        # Atualiza FGI a cada 10 min (não muda rápido)
        if (time.time() - macro_cache["last_fgi_update"]) > 600:
            macro_cache["fgi_data"] = update_fgi_data()
            macro_cache["last_fgi_update"] = time.time()
            print("✅ Cache Sentimento (FGI) atualizado.")
        
        time.sleep(10) # Verifica expiração a cada 10s

def load_signals():
    signals = {}
    if not SIGNALS_LOG.exists():
        return signals
    try:
        with open(SIGNALS_LOG, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                symbol = data.get("symbol")
                if symbol:
                    signals[symbol] = data
    except Exception:
        pass
    return signals

@app.route('/api/latest-enriched', methods=['GET'])
def get_enriched():
    if not JSON_LATEST.exists():
        return jsonify({"error": "Nenhum JSON detectado ainda"}), 404

    try:
        with open(JSON_LATEST, "r", encoding="utf-8") as f:
            eassets_data = json.load(f)
        
        signals = load_signals()
        
        # Adicionar dados Externos (Centralizados)
        eassets_data["macro_tradfi"] = macro_cache["macro_data"]
        eassets_data["sentiment"] = macro_cache["fgi_data"]
        
        # Enriquecimento (Logic de fusão eAssets + SS)
        main_data = eassets_data.get("data", {})
        for symbol, info in main_data.items():
            if symbol in signals:
                ss = signals[symbol]
                info["ss_score"] = ss.get("score", 0)
                info["ss_cvd_1m"] = ss.get("cvd_1m", 0)
                info["ss_trades_1m"] = ss.get("trades_1m", 0)
                info["ss_status"] = "GATILHO ATIVO"
        
        # SALVAMENTO AUTOMÁTICO: Cria o arquivo consolidado para auditoria futura
        consolidated_path = JSON_LATEST.parent / "eassets_consolidado_com_sniper.json"
        with open(consolidated_path, "w", encoding="utf-8") as f_save:
            json.dump(eassets_data, f_save, indent=2)
            
        return jsonify(eassets_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-update', methods=['GET'])
def check_update():
    """Retorna o timestamp da última modificação para o Dashboard saber se recarrega."""
    if not JSON_LATEST.exists():
        return jsonify({"mtime": 0})
    return jsonify({"mtime": os.path.getmtime(JSON_LATEST)})

if __name__ == "__main__":
    print("🚀 eAssets Enrichment Server Online!")
    print("🔗 Endpoint: http://127.0.0.1:5001/api/latest-enriched")
    
    # Inicia o trabalhador de background antes de subir o servidor Flask
    threading.Thread(target=background_worker, daemon=True).start()
    
    app.run(port=5001, debug=False)