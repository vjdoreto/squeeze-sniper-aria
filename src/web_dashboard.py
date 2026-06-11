"""FastAPI dashboard — runs in a thread (Windows-safe), streams state via WebSocket."""
import asyncio
import contextlib
import logging
import os
import subprocess
import threading
import signal
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional, Callable, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse

from src.bot_state import BotState
from src.signal_engine import SqueezeIgnition

logger = logging.getLogger("WebDashboard")

# ---- Persistent diagnostics (dashboard offline root-cause) ----
_DASH_DIAG_PATH = Path("logs/dashboard_diagnostics.log")
def _dash_diag(msg: str) -> None:
    try:
        _DASH_DIAG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DASH_DIAG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except Exception:
        pass

# ---- HTTP guards / rate limit (web panel controls) ----
_HTTP_RATE_STATE: dict[str, list[float]] = {}
_HTTP_RATE_LOCK = threading.Lock()

_DASHBOARD_ALLOW_REMOTE = os.getenv("DASHBOARD_ALLOW_REMOTE", "0").strip().lower() in ("1", "true", "yes")
_DASHBOARD_SECRET = (os.getenv("DASHBOARD_SECRET", "") or "").strip()

# SPRINT 6.45: Amplia loopback para suportar VENVs e redes locais
_LOOPBACK_IPS = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}

def _is_private_ip(ip: str) -> bool:
    """Verifica se o IP pertence a faixas de rede privada/local."""
    return ip.startswith(("127.", "192.168.", "10.", "172.16.", "172.31."))


def _http_client_ip(request: Request) -> str:
    if not request.client or not request.client.host:
        return "unknown"
    return request.client.host


def _http_guard(request: Request) -> str:
    ip = _http_client_ip(request)
    if not _DASHBOARD_ALLOW_REMOTE and ip not in _LOOPBACK_IPS and not _is_private_ip(ip):
        logger.warning(f"🔒 Acesso bloqueado: IP {ip} não autorizado. Configure DASHBOARD_ALLOW_REMOTE=1")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Acesso negado para {ip}")
    if _DASHBOARD_SECRET:
        token = request.headers.get("X-Dashboard-Token", "")
        if token != _DASHBOARD_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid dashboard token.")
    return ip


def _http_rate_limit(key: str, *, limit: int, window_seconds: float) -> None:
    now = time.time()
    with _HTTP_RATE_LOCK:
        bucket = _HTTP_RATE_STATE.setdefault(key, [])
        # remove timestamps older than window
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded.")
        bucket.append(now)

        # small GC to avoid growth
        if len(_HTTP_RATE_STATE) > 2048:
            # keep only hot keys
            for k in list(_HTTP_RATE_STATE.keys()):
                if not _HTTP_RATE_STATE[k]:
                    del _HTTP_RATE_STATE[k]

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>SqueezeSniper V4 — Doreto</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    /* ══════════════════════════════════════════════════════
       ARIA REDESIGN — SqueezeSniper V4 · Doreto
       Purely cosmetic — zero backend changes
       Preserves all IDs, classes, JS hooks
    ══════════════════════════════════════════════════════ */

    :root {
      --bg:       #080b0f;
      --bg2:      #0d1117;
      --bg3:      #111720;
      --card:     #0f1520;
      --border:   rgba(255,255,255,0.07);
      --border2:  rgba(255,255,255,0.12);
      --green:    #2ecc71;
      --green2:   #1a8a47;
      --red:      #e74c3c;
      --yellow:   #f0a500;
      --blue:     #3498db;
      --purple:   #9b59b6;
      --text:     #e8eaf0;
      --muted:    #8892a4;
      --dim:      #4a5568;
      --accent:   #2ecc71;
      --accent2:  #3498db;
      --border-dim: rgba(255,255,255,0.07);
      --font-sans: 'DM Sans', system-ui, sans-serif;
      --font-mono: 'Space Mono', monospace;
    }

    * { box-sizing: border-box; }
    html, body { height: 100%; overflow-y: auto; overflow-x: hidden; }
    body { scrollbar-width: none; }
    body::-webkit-scrollbar { width: 0; height: 0; }
    body { margin: 0; font-family: var(--font-sans); background: var(--bg); color: var(--text); }

    body::before {
      content: '';
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background:
        radial-gradient(ellipse 800px 500px at 5% 0%, rgba(46,204,113,0.04) 0%, transparent 55%),
        radial-gradient(ellipse 600px 400px at 95% 90%, rgba(52,152,219,0.03) 0%, transparent 55%);
      pointer-events: none; z-index: 0;
    }
    header, main, section, aside { position: relative; z-index: 1; }

    header {
      padding: 10px 20px;
      border-bottom: 0.5px solid rgba(46,204,113,0.15);
      display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
      background: linear-gradient(180deg, rgba(15,21,32,0.99) 0%, rgba(8,11,15,0.97) 100%);
      backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      box-shadow: 0 1px 0 rgba(46,204,113,0.1), 0 4px 24px rgba(0,0,0,0.5);
    }
    h1 { margin: 0; font-size: 1.2rem; }

    .logo-wrap { display: flex; align-items: center; gap: 10px; }
    .logo-svg { filter: drop-shadow(0 0 8px rgba(46,204,113,0.6)); transition: filter 0.3s; }
    .logo-svg:hover { filter: drop-shadow(0 0 16px rgba(46,204,113,1)); }
    .logo-text { display: flex; flex-direction: column; gap: 1px; }
    .logo-name {
      font-family: var(--font-mono); font-size: 1rem; font-weight: 700; letter-spacing: 2px;
      background: linear-gradient(90deg, #2ecc71 0%, #3498db 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .logo-tagline { font-size: 0.5rem; color: var(--muted); letter-spacing: 3px; text-transform: uppercase; font-family: var(--font-mono); }
    .logo-version {
      font-family: var(--font-mono); font-size: 0.58rem; font-weight: 700; letter-spacing: 1px;
      background: rgba(46,204,113,0.1); color: var(--green);
      border: 0.5px solid rgba(46,204,113,0.4); padding: 2px 7px; border-radius: 4px;
      align-self: flex-start; margin-top: 2px;
    }

    .badge { padding: 4px 12px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; font-family: var(--font-mono); letter-spacing: 0.5px; }
    .paper  { background: rgba(46,204,113,0.1);  color: var(--green);  border: 0.5px solid rgba(46,204,113,0.4); }
    .live   { background: rgba(231,76,60,0.1);   color: var(--red);    border: 0.5px solid rgba(231,76,60,0.4); }
    .warmup-badge { background: rgba(240,165,0,0.1); color: var(--yellow); border: 0.5px solid rgba(240,165,0,0.4); animation: pulse 1.4s ease-in-out infinite, pulse-warm 1.8s ease-out infinite !important; }
    #modeToggle { cursor: pointer; transition: all 0.2s; }
    #modeToggle:hover { opacity: 0.85; transform: scale(1.03); }

    .btn-danger {
      background: rgba(231,76,60,0.1); color: var(--red); border: 0.5px solid rgba(231,76,60,0.4);
      padding: 4px 12px; border-radius: 6px; font-size: 0.72rem; font-weight: 700;
      font-family: var(--font-mono); cursor: pointer; transition: all 0.2s;
    }
    .btn-danger:hover { background: rgba(231,76,60,0.22); box-shadow: 0 0 10px rgba(231,76,60,0.3); }

    #paperBtn {
      padding: 6px 14px; border-radius: 6px; border: 0.5px solid rgba(46,204,113,0.35);
      background: rgba(46,204,113,0.08); color: var(--green);
      font-family: var(--font-mono); font-weight: 700; cursor: pointer; transition: all 0.2s;
    }
    #paperBtn:hover { background: rgba(46,204,113,0.16); box-shadow: 0 0 10px rgba(46,204,113,0.25); }

    .meta { color: var(--muted); font-size: 0.82rem; }
    #conn { margin-left: auto; font-size: 0.78rem; }
    .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; }
    .ok  { background: var(--green); }
    .bad { background: var(--red); }

    main { display: grid; grid-template-columns: 1fr minmax(320px, 0.36fr); gap: 10px; padding: 10px 12px; align-items: start; }
    main .wide { grid-column: 1 / -1; }
    @media (max-width: 1100px) { main { grid-template-columns: 1fr; } }

    .card {
      background: var(--card); border: 0.5px solid var(--border); border-radius: 10px; overflow: hidden;
      box-shadow: 0 2px 16px rgba(0,0,0,0.4); transition: border-color 0.25s, box-shadow 0.25s;
    }
    .card:hover { border-color: rgba(46,204,113,0.2); box-shadow: 0 2px 20px rgba(0,0,0,0.5); }
    .card h2 {
      margin: 0; padding: 10px 16px; font-size: 0.82rem; font-weight: 600;
      font-family: var(--font-mono); letter-spacing: 0.5px;
      border-bottom: 0.5px solid var(--border);
      background: linear-gradient(90deg, rgba(46,204,113,0.04) 0%, transparent 50%);
      color: var(--text);
    }

    table { width: 100%; border-collapse: collapse; font-size: 0.76rem; }

    .scroll-table { max-height: 180px; height: 180px; overflow-y: auto; overflow-x: hidden; }
    .scroll-table--top {
      overflow-y: auto; overflow-x: hidden;
      max-height: calc(100vh - 320px); min-height: 400px;
      scrollbar-width: none; -ms-overflow-style: none;
    }
    .scroll-table--top::-webkit-scrollbar { width: 0; height: 0; }
    .scroll-table--post  { max-height: none; height: auto; overflow-y: visible; }
    .scroll-table--paper { max-height: none; height: auto; overflow-y: visible; }

    .col-sec-paper { display: none; }
    #paper-table-wrap.expanded .col-sec-paper { display: table-cell; }

    .scroll-table--top thead th {
      position: sticky; top: 0; z-index: 3;
      background: rgba(8,11,15,0.98) !important;
      border-bottom: 0.5px solid var(--border2);
    }

    #signals  { max-height: 190px; overflow-y: auto; overflow-x: hidden; scrollbar-width: none; }
    #signals::-webkit-scrollbar  { width: 0; height: 0; }
    #ghosts   { max-height: 190px; overflow-y: auto; overflow-x: hidden; scrollbar-width: none; }
    #ghosts::-webkit-scrollbar   { width: 0; height: 0; }

    .scroll-table table { width: 100%; border-collapse: collapse; table-layout: auto; }
    .scroll-table th, .scroll-table td { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    body:not(.is-loading) .scroll-table table { table-layout: fixed; }
    body.is-loading .scroll-table th,
    body.is-loading .scroll-table td { white-space: normal; overflow: visible; text-overflow: clip; }

    th, td { padding: 7px 9px; text-align: right; border-bottom: 0.5px solid rgba(255,255,255,0.05); }
    th:first-child, td:first-child { text-align: left; }
    th { color: var(--muted); font-weight: 600; font-size: 0.7rem; font-family: var(--font-mono); letter-spacing: 0.3px; text-transform: uppercase; }
    tr:hover td { background: rgba(255,255,255,0.03); }
    td { font-family: var(--font-mono); font-size: 0.72rem; }
    td:first-child { font-family: var(--font-sans); font-weight: 600; }

    #rows td, #rows th { padding: 3px 5px; font-size: 11px; white-space: nowrap; }
    #rows td:nth-child(n+15) { min-width: 44px; font-size: 10px; }
    #post-trade-rows td, #post-trade-rows th { padding: 5px 8px; }
    #paper-rows td, #paper-rows th { padding: 5px 8px; }
    #strong-signals-card table { table-layout: fixed; }
    #strong-signals-card th, #strong-signals-card td { vertical-align: middle; }
    #strong-signals-card .status-cell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    .status-squeeze  { color: #080b0f !important; background: var(--yellow) !important; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-family: var(--font-mono); font-size: 0.65rem; box-shadow: 0 0 8px rgba(240,165,0,0.4); }
    .status-potential{ color: #080b0f !important; background: var(--green) !important;  padding: 2px 7px; border-radius: 4px; font-weight: 700; font-family: var(--font-mono); font-size: 0.65rem; box-shadow: 0 0 8px rgba(46,204,113,0.4); }
    .status-watch    { color: var(--muted); background: transparent; border: 0.5px solid var(--border2); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 0.65rem; }

    .signals { max-height: none; overflow: visible; }
    .sig { padding: 9px 14px; border-bottom: 0.5px solid rgba(255,255,255,0.05); font-size: 0.78rem; }
    .sig b { color: var(--yellow); font-family: var(--font-mono); }
    .ghost-sig { border-left: 2px solid rgba(46,204,113,0.35); background: rgba(46,204,113,0.02); opacity: 0.85; }

    .pos { color: var(--green); font-weight: 600; }
    .neg { color: var(--red);   font-weight: 600; }

    .hm-pos-1 { background-color: rgba(46, 204, 113, 0.15); }
    .hm-pos-2 { background-color: rgba(46, 204, 113, 0.35); }
    .hm-pos-3 { background-color: rgba(46, 204, 113, 0.58); }
    .hm-neg-1 { background-color: rgba(231,  76,  60, 0.15); }
    .hm-neg-2 { background-color: rgba(231,  76,  60, 0.35); }
    .hm-neg-3 { background-color: rgba(231,  76,  60, 0.58); }

    .row-warm  { background: rgba(240,165,0,0.05) !important; }
    .row-hot   { background: rgba(240,165,0,0.09) !important; box-shadow: inset 2px 0 0 rgba(240,165,0,0.6); }
    .row-super { background: rgba(46,204,113,0.08) !important; box-shadow: inset 2px 0 0 var(--green); }

    .cell-dim  { opacity: 0.4; }
    .cell-hot  { background: rgba(240,165,0,0.28); font-weight: 700; border-radius: 3px; }
    .cell-glow { background: rgba(46,204,113,0.45); font-weight: 700; color: #fff; border-radius: 3px; box-shadow: 0 0 6px rgba(46,204,113,0.5); }

    .score-90 { color: var(--green) !important; font-weight: 900; text-shadow: 0 0 10px rgba(46,204,113,0.7); font-family: var(--font-mono); }
    .score-80 { color: var(--green); font-weight: 700; font-family: var(--font-mono); }

    @keyframes flash-green { from { background: rgba(46,204,113,0.35); } to { background: transparent; } }
    @keyframes flash-red   { from { background: rgba(231,76,60,0.35);  } to { background: transparent; } }
    .up-flash   { animation: flash-green 0.8s ease-out; }
    .down-flash { animation: flash-red   0.8s ease-out; }
    tr { transition: background 0.3s ease; }
    td { transition: color 0.2s ease; }

    #rows:empty::after { content: "Aguardando processamento de símbolos..."; color: var(--muted); padding: 20px; display: block; font-family: var(--font-mono); font-size: 0.75rem; }

    #treemap { display: grid; grid-template-columns: repeat(10, 1fr); gap: 3px; }
    .hm-box {
      aspect-ratio: 1/1; display: flex; flex-direction: column; align-items: center; justify-content: center;
      font-size: 0.6rem; font-weight: 800; border-radius: 5px; cursor: default;
      transition: transform 0.2s, box-shadow 0.2s; border: 0.5px solid rgba(255,255,255,0.06);
      overflow: hidden; font-family: var(--font-mono);
    }
    .hm-box:hover { transform: scale(1.1); z-index: 10; border-color: rgba(255,255,255,0.25); box-shadow: 0 0 10px rgba(46,204,113,0.25); }
    .hm-box .val { font-size: 0.48rem; opacity: 0.75; font-weight: 400; margin-top: 1px; }

    @keyframes hm-pulse {
      0%   { box-shadow: inset 0 0 0 0 rgba(240,165,0,0.8); }
      70%  { box-shadow: inset 0 0 0 10px rgba(240,165,0,0); }
      100% { box-shadow: inset 0 0 0 0 rgba(240,165,0,0); }
    }
    .pulse-signal { animation: hm-pulse 1.5s infinite; border: 0.5px solid var(--yellow) !important; }

    .fav-star { cursor: pointer; margin-right: 5px; color: var(--dim); transition: color 0.2s; font-size: 1rem; vertical-align: middle; }
    .fav-star.active { color: var(--yellow); }
    .fav-star:hover  { color: var(--muted); }

    @keyframes pulse      { 0%, 100% { opacity: 1; }   50% { opacity: 0.55; } }
    @keyframes pulse-warm { 0%, 100% { box-shadow: 0 0 0 0 rgba(240,165,0,0.5); } 60% { box-shadow: 0 0 0 5px rgba(240,165,0,0); } }
    @keyframes ring-pulse { 0% { box-shadow: 0 0 0 0 rgba(46,204,113,0.7); } 70% { box-shadow: 0 0 0 7px rgba(46,204,113,0); } 100% { box-shadow: 0 0 0 0 rgba(46,204,113,0); } }
    .dot.ok { animation: ring-pulse 2.2s ease-out infinite; }

    #macro-bar {
      background: linear-gradient(90deg, rgba(8,11,15,0.98) 0%, rgba(15,21,32,0.97) 50%, rgba(8,11,15,0.98) 100%) !important;
      border: 0.5px solid rgba(46,204,113,0.1) !important;
      font-family: var(--font-mono) !important;
    }

    #strong-signals-card {
      background: linear-gradient(135deg, rgba(18,34,18,0.8) 0%, rgba(8,11,15,0.97) 100%) !important;
      border: 0.5px solid rgba(46,204,113,0.25) !important;
    }

    #sq-gauge { border-radius: 4px !important; background: rgba(255,255,255,0.04) !important; border: 0.5px solid var(--border2) !important; }
    #sq-fill[style*="background:#f85149"] { box-shadow: 0 0 10px rgba(231,76,60,0.6); }
    #sq-fill[style*="background:#d29922"] { box-shadow: 0 0 10px rgba(240,165,0,0.6); }
    #sq-fill[style*="background:#3fb950"] { box-shadow: 0 0 10px rgba(46,204,113,0.6); }

    canvas { display: block; }
    #equityChart   { border: 0.5px solid rgba(46,204,113,0.2) !important; border-radius: 8px; }
    #drawdownChart { border: 0.5px solid rgba(231,76,60,0.2)  !important; border-radius: 8px; }
    #riskChart     { border: 0.5px solid rgba(240,165,0,0.2)  !important; border-radius: 8px; }
    #winRateChart  { border: 0.5px solid rgba(52,152,219,0.2) !important; border-radius: 8px; }

    #paper-stats-panel > div, #live-stats-panel > div {
      background: rgba(255,255,255,0.02); border: 0.5px solid var(--border);
      border-radius: 8px; padding: 10px 14px; transition: border-color 0.2s;
    }
    #paper-stats-panel > div:hover, #live-stats-panel > div:hover { border-color: rgba(46,204,113,0.2); }

    input[type="number"], select {
      font-family: var(--font-mono) !important; font-size: 0.75rem !important;
      background: rgba(255,255,255,0.03) !important; border: 0.5px solid var(--border2) !important;
      border-radius: 6px !important; color: var(--text) !important; transition: border-color 0.2s;
    }
    input[type="number"]:focus, select:focus { outline: none; border-color: rgba(46,204,113,0.5) !important; }

    #paper-cockpit { border-color: rgba(46,204,113,0.2) !important; }
    #live-cockpit  { border-color: rgba(231,76,60,0.2)  !important; }

    #refusal-count { font-family: var(--font-mono) !important; font-size: 1.6rem !important; font-weight: 700 !important; }
    #top-refusals  { font-family: var(--font-mono); font-size: 0.68rem; line-height: 1.8; }

    #live-controls { background: rgba(231,76,60,0.03) !important; border-bottom: 0.5px solid rgba(231,76,60,0.1) !important; }
    #live-balance-val, #live-margin-val { font-family: var(--font-mono) !important; }

    ::-webkit-scrollbar { width: 3px; height: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
  </style>
</head>
<body class="is-loading">
    <header>
      <div class="logo-wrap">
        <svg class="logo-svg" width="34" height="34" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="16" cy="16" r="13.5" stroke="#3fb950" stroke-width="1.5"/>
          <circle cx="16" cy="16" r="8.5" stroke="rgba(63,185,80,0.4)" stroke-width="1" stroke-dasharray="3 2"/>
          <circle cx="16" cy="16" r="2.8" fill="#3fb950"/>
          <line x1="1.5" y1="16" x2="9" y2="16" stroke="#3fb950" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="23" y1="16" x2="30.5" y2="16" stroke="#3fb950" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="16" y1="1.5" x2="16" y2="9" stroke="#3fb950" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="16" y1="23" x2="16" y2="30.5" stroke="#3fb950" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="9.5" cy="9.5" r="1" fill="rgba(63,185,80,0.5)"/>
          <circle cx="22.5" cy="9.5" r="1" fill="rgba(63,185,80,0.5)"/>
          <circle cx="9.5" cy="22.5" r="1" fill="rgba(63,185,80,0.5)"/>
          <circle cx="22.5" cy="22.5" r="1" fill="rgba(63,185,80,0.5)"/>
        </svg>
        <div class="logo-text">
          <span class="logo-name">SqueezeSniper</span>
          <span class="logo-tagline">Institutional Squeeze Tracker</span>
        </div>
        <span class="logo-version">V4</span>
      </div>
      <button id="modeToggle" class="badge paper" title="Clique para alternar entre Paper e Live trading">PAPER</button>
      
      <!-- Squeezometer Aggregated Gauge (Sprint 5.7 / DNA Squeeze) -->
      <div style="
        display:flex; align-items:center; gap:10px; margin-left:10px; padding:0 15px; 
        border-left:1px solid #30363d; border-right:1px solid #30363d;
        background: rgba(0,0,0,0.2); border-radius: 4px;" title="Média de Score dos Top ativos - Pulsação do Mercado">
        <div style="font-size:0.65rem; color:var(--muted); text-transform:uppercase; letter-spacing:1px;">Market Squeeze</div>
        <div id="sq-gauge" style="height:10px; background:#21262d; border-radius:5px; overflow:hidden; border:1px solid #30363d; width:100px;">
          <div id="sq-fill" style="height:100%; width:0%; background:var(--green); transition:width 0.8s, background 0.5s;"></div>
        </div>
        <span id="sq-val" style="font-size:0.8rem; font-weight:800; min-width:45px; color:var(--muted);">0/100</span>
      </div>
      <span id="warmup-timer" class="badge warmup-badge" style="display:none;">⏳ WARMUP: 300s</span>

      <input id="paperDelayMin" type="number" min="0" step="1" value="3" style="width:86px; padding:6px 8px; border-radius:8px; border:1px solid #30363d; background:#0d1117; color:var(--text); font-weight:800;" />
      <button id="paperBtn" style="padding:6px 12px; border-radius:8px; border:1px solid #30363d; background:#161b22; color:var(--green); font-weight:900; cursor:pointer;">Reset + Paper LONG</button>
      <button id="hardResetBtn" class="btn-danger" title="Apaga TUDO: Trades, Cache e força novo Warmup">HARD RESET</button>
      <button id="exitBtn" class="btn-danger" title="Encerrar o bot como CTRL+C (gracioso)">EXIT</button>
      <span class="meta" id="meta">Conectando…</span>
      <span id="conn"><span class="dot bad"></span><span id="connLabel">offline</span></span>
      <button id="wsReconnect" style="display:none; margin-left:8px; padding:3px 8px; border-radius:6px; border:1px solid #d29922; background:#1a1500; color:#d29922; cursor:pointer; font-size:.7rem;" onclick="connect()">⏳ WS falhou — reconectar</button>
    </header>
    <main>
      <section class="card macro-bar wide" id="macro-bar" style="display: flex; gap: 40px; justify-content: center; padding: 15px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117;">
        <!-- Preenchido via JS -->
      </section>

      <!-- SEÇÃO DE SINAIS FORTES EM DESTAQUE -->
      <section class="card wide" id="strong-signals-card" style="padding: 12px; background: linear-gradient(135deg, #1a2e1a, #0d1117); border: 1px solid #3fb950; border-radius: 8px;">
        <div style="font-size: 0.8rem; color: #d29922; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;"><b>🚀 Sinais Fortes — Ativos mais fortes que BTC</b></div>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.78rem;">
              <thead>
            <tr>
              <th>Símbolo</th><th style="text-align:center">Score</th><th style="color:#f0b90b;">CVD Δ%</th>
              <th>OI Δ%</th><th>LSR Δ%</th><th>exp vs BTC</th>
              <th>TRADES(1m)</th><th title="Atividade vs baseline (0-4)">T.Lvl</th><th>RSI 5m</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id="strong-rows"></tbody>
        </table>
      </section>

      <section class="card wide" style="padding: 12px; background: #0d1117; border: 1px solid #30363d;">
        <div style="font-size: 0.75rem; color: #8b949e; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;">Heatmap Momentum Compact (% 15m & Fit Score)</div>
        <div id="heatmap-strip" style="display:flex; flex-wrap:wrap; gap:3px; padding:4px 8px; max-height:75px; overflow:hidden; background:#0d1117; border-bottom:1px solid #222;"></div>
      </section>

      <section class="card wide">
        <h2 style="display: flex; align-items: center; gap: 16px;">
          🏆 Top Símbolos — CVD &amp; % Growth
          <div style="margin-left: auto; display: flex; gap: 8px; align-items: center;">
            <div style="display: flex; align-items: center; gap: 6px; margin-right: 12px; border-right: 1px solid #30363d; padding-right: 12px;">
              <input type="checkbox" id="volFilterCheck" style="cursor:pointer;" />
              <label for="volFilterCheck" style="font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; cursor:pointer;">Min Vol:</label>
              <input type="number" id="volThresholdInput" value="10" step="1" min="0" style="width: 45px; padding: 2px 4px; border-radius: 4px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-size: 0.75rem; font-weight: bold;" />
              <span style="font-size: 0.7rem; color: var(--muted);">M</span>
            </div>
            <label style="font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px;">Timeframe:</label>
            <select id="tfSelect" style="padding: 4px 10px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-size: 0.75rem; cursor: pointer; font-weight: 600;">
              <option value="1m">1m (Burst)</option>
              <option value="5m" selected>5m (Ignition)</option>
              <option value="1h">1h (Macro)</option>
            </select>
            <label style="font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px;">Ordenar por:</label>
            <select id="sortSelect" style="padding: 4px 10px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-size: 0.75rem; cursor: pointer; font-weight: 600;">
              <option value="score">Fit Score</option>
              <option value="vol_24h_m">Volume 24h</option>
              <option value="cvd_change_pct">CVD Δ%</option>
              <option value="oi_trend">OI Trend (5m)</option>
              <option value="lsr_change_pct">LSR Δ% (Pânico)</option>
            </select>
          </div>
        </h2>
        <div class="scroll-table scroll-table--top">
          <table>
            <thead>
              <tr>
                <th>Símbolo</th><th>Preço</th><th>24h %</th><th>Score</th>
                <th>CVD Δ%</th><th>📈</th>
                <th>OI Δ%</th><th>📈</th>
                <th>LSR Δ%</th>
                <th>OI Accel</th><th id="th-exp">exp</th><th>exp vs BTC</th>
                <th id="th-ema">EMA</th>
                <th>OB Imb</th><th>Funding</th>
                <th>OI(USD)</th><th id="th-oit">oi↑</th>
                <th>LSR</th><th>lsr↓</th>
                <th style="color:#d29922;">Liq. Short</th><th>HFT (10s)</th>
                <th>TRADES(1m)</th>
                <th title="Atividade vs baseline (0-4)">T.Lvl</th>
                <th>RSI 5m</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody id="rows"></tbody>
          </table>
        </div>
      </section>

    <div style="grid-column: 1 / -1; display:grid; grid-template-columns: 1fr 1fr 1fr; gap:12px; align-items:start;">
      <aside class="card signals">
        <h2>Sinais recentes</h2>
        <div id="signals"><div class="sig meta">Aguardando sinais…</div></div>
      </aside>

      <section class="card">
        <h2 style="color:var(--muted); font-size:0.8rem;">👻 Ghost Signals (Audit)</h2>
        <div id="ghosts" style="padding:12px 16px 16px;">
          <div class="sig meta">Nenhum fantasma detectado</div>
        </div>
      </section>

      <section class="card">
        <h2 style="color:var(--red); font-size:0.8rem;">🛡️ Sinais Bloqueados (1h)</h2>
        <div style="padding:12px 16px 16px;">
          <div style="margin-bottom:12px;">
            <div style="font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:4px;">Total Bloqueados</div>
            <div id="refusal-count" style="font-size:20px; font-weight:700; color:var(--red);">0</div>
            <div id="refusal-rate" style="font-size:10px; color:var(--muted); margin-top:2px;">0% dos sinais</div>
          </div>
          <div>
            <div style="font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:4px;">Top 5 Motivos</div>
            <div id="top-refusals" style="font-size:10px; color:var(--text);"></div>
          </div>
        </div>
      </section>
    </div>

      <section class="card wide" id="paper-cockpit">
        <h2 style="display: flex; align-items: center; gap: 16px;">
          📋 Paper LONG — assertividade
          <div style="margin-left: auto; display: flex; gap: 12px; align-items: center;">
            <span id="paper-open-count-badge" style="background:#1a5c2a; color:#9be9a8; padding:2px 8px; border-radius:10px; font-size:11px">0 abertos</span>
            <span id="paper-wr-header-badge" style="font-size:11px; font-weight:900; color:#f85149;">WR 0%</span>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Capital Inicial</label>
              <input id="initialCapitalInput" type="number" min="0" step="100" value="1000" style="width: 120px; padding: 6px 8px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-weight: 700;" />
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Risco %</label>
              <input id="riskPctInput" type="number" min="0.1" max="100" step="0.1" value="5" style="width: 100px; padding: 6px 8px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-weight: 700;" />
            </div>

            <div style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Alav.</label>
              <input id="leverageInput" type="number" min="1" max="125" step="1" value="10" style="width: 90px; padding: 6px 8px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-weight: 700;" />
            </div>

            <div style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Max Pos</label>
              <input id="maxPosInput" type="number" min="1" max="50" step="1" value="8" style="width: 80px; padding: 6px 8px; border-radius: 6px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-weight: 700;" />
            </div>

            <button id="updateCapitalBtn" style="padding: 6px 12px; border-radius: 6px; border: 1px solid #3fb950; background: #1f3d2a; color: #3fb950; font-weight: 900; cursor: pointer; margin-top: 18px;">
              Atualizar
            </button>
          </div>
        </h2>
        
        <!-- Stats Panel -->
        <div id="paper-stats-panel" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; padding: 12px 16px; border-bottom: 1px solid #30363d;">
          <!-- Filled via JS -->
        </div>
        
        <p class="meta" id="paper-meta" style="padding:0 16px 8px;margin:0">—</p>
        <div class="table-container">
          <div style="padding:4px 16px 4px; display:flex; align-items:center; gap:8px;">
            <button id="paper-col-toggle" onclick="togglePaperCols()" style="font-size:10px; padding:2px 8px; border-radius:4px; border:1px solid #30363d; background:#161b22; color:#8b949e; cursor:pointer;">⊕ Expandir colunas</button>
          </div>
          <div class="scroll-table scroll-table--paper" id="paper-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Símbolo</th><th>PnL %</th><th>PnL $</th><th>MFE</th><th class="col-sec-paper">MAE</th><th>Margem</th><th class="col-sec-paper">Entrada</th><th class="col-sec-paper">Atual</th><th class="col-sec-paper">Size</th><th class="col-sec-paper">Notional</th><th class="col-sec-paper">Alav.</th><th class="col-sec-paper">Fee In</th><th class="col-sec-paper">Fee Out</th><th class="col-sec-paper" title="Risco Kelly Aplicado">Risk %</th><th>SL / TP</th><th>Tempo</th><th>Qualidade</th><th>Ação</th>
                </tr>
              </thead>
              <tbody id="paper-rows"></tbody>
            </table>
          </div>
        </div>

      </section>

      <section class="card wide" id="live-cockpit">
        <h2 style="display: flex; align-items: center; gap: 16px;">
          📋 LIVE LONG — assertividade
          <div style="margin-left: auto; display: flex; gap: 12px; align-items: center;">
            <span id="live-api-led" style="display:inline-flex; align-items:center; gap:4px; font-size:10px; color:#8b949e">
              <span id="live-api-dot" style="width:7px;height:7px;border-radius:50%; background:#555; display:inline-block"></span>
              <span id="live-api-text">API ?</span>
            </span>
            <span id="live-open-count-badge" style="background:#3d1f1f; color:#f85149; padding:2px 8px; border-radius:10px; font-size:11px">0 abertos</span>
            <span id="live-wr-header-badge" style="font-size:11px; font-weight:900; color:#f85149;">WR 0%</span>
          </div>
        </h2>
        <div style="display: flex; gap: 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid #30363d; flex-wrap: wrap;">

            <div style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Capital</label>
              <input id="liveInitialCapitalInput" type="number" min="0" step="0.01" value="1000.00" style="width: 100px; padding: 6px 8px; border-radius: 6px; border: 1px solid #3d1f1f; background: #0d1117; color: #f85149; font-weight: 700;" />
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Risco %</label>
              <input id="liveRiskPctInput" type="number" min="0.1" max="100" step="0.1" value="5" style="width: 80px; padding: 6px 8px; border-radius: 6px; border: 1px solid #3d1f1f; background: #0d1117; color: #f85149; font-weight: 700;" />
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Alav.</label>
              <input id="liveLeverageInput" type="number" min="1" max="125" step="1" value="10" style="width: 70px; padding: 6px 8px; border-radius: 6px; border: 1px solid #3d1f1f; background: #0d1117; color: #f85149; font-weight: 700;" />
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Max Pos</label>
              <input id="liveMaxPosInput" type="number" min="1" max="50" step="1" value="3" style="width: 70px; padding: 6px 8px; border-radius: 6px; border: 1px solid #3d1f1f; background: #0d1117; color: #f85149; font-weight: 700;" />
            </div>

            <button id="updateLiveBtn" style="padding: 6px 12px; border-radius: 6px; border: 1px solid #f85149; background: #3d1f1f; color: #f85149; font-weight: 900; cursor: pointer; margin-top: 18px;">
              Atualizar Live
            </button>
            <button id="liveCompoundBtn" class="badge warmup-badge" style="margin-top: 18px; padding: 6px 12px; height: 35px; border-radius: 6px; cursor: pointer; font-weight: 800;">
              Compound: OFF
            </button>
          </div>
        </h2>

        <!-- SPRINT 12.21: Controles avançados LIVE (colapsável) -->
        <div style="padding:4px 16px; border-bottom:1px solid #21262d;">
          <button onclick="toggleLiveConfig()" id="live-config-toggle" style="font-size:10px;padding:2px 8px;border-radius:4px;border:1px solid #3d1f1f;background:#0d1117;color:#8b949e;cursor:pointer;">⚙ Configurações avançadas</button>
        </div>
        <div id="live-config-panel" style="display:none; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; padding: 12px 16px; border-bottom: 1px solid #30363d; background: rgba(248,81,73,0.02);">
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <label style="font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">SL %</label>
            <input id="liveSlPctInput" type="number" min="0.5" max="10" step="0.5" value="1.5" style="width: 100%; padding: 4px 6px; border-radius: 4px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-size: 0.75rem; font-weight: 700;" />
          </div>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <label style="font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">TP %</label>
            <input id="liveTpPctInput" type="number" min="1" max="20" step="0.5" value="5" style="width: 100%; padding: 4px 6px; border-radius: 4px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-size: 0.75rem; font-weight: 700;" />
          </div>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <label style="font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Max Hold (min)</label>
            <input id="liveMaxHoldInput" type="number" min="0" max="1440" step="5" value="0" style="width: 100%; padding: 4px 6px; border-radius: 4px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-size: 0.75rem; font-weight: 700;" />
          </div>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <label style="font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">Signal Mode</label>
            <select id="liveSignalModeInput" style="width: 100%; padding: 4px 6px; border-radius: 4px; border: 1px solid #30363d; background: #0d1117; color: #e6edf3; font-size: 0.75rem; font-weight: 700;">
              <option value="conservative">Conservative</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 12px;">
            <input type="checkbox" id="liveTrailingCheck" style="cursor: pointer;" />
            <label for="liveTrailingCheck" style="font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; cursor: pointer;">Trailing Stop</label>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 12px;">
            <input type="checkbox" id="liveKellyCheck" style="cursor: pointer;" />
            <label for="liveKellyCheck" style="font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; cursor: pointer;">Kelly Criterion</label>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 12px; grid-column: 1 / -1;">
            <input type="checkbox" id="liveAutoPilotCheck" style="cursor: pointer;" />
            <label for="liveAutoPilotCheck" style="font-size: 0.7rem; color: #d29922; text-transform: uppercase; letter-spacing: 1px; cursor: pointer; font-weight: 900;">🤖 AUTO-PILOT (Motor Gerencia SL/TP Dinamicamente)</label>
            <span id="autoPilotHint" style="font-size: 0.65rem; color: #8b949e; margin-left: 8px; display: none;">SL/TP baseados em ATR • R:R 3:1 • Ideal para dormir</span>
          </div>
          <button id="updateLiveAdvancedBtn" style="padding: 4px 8px; border-radius: 4px; border: 1px solid #f85149; background: #3d1f1f; color: #f85149; font-weight: 900; cursor: pointer; margin-top: 8px; font-size: 0.75rem;">
            Atualizar Avançado
          </button>
        </div>

        <div id="live-controls" style="display:flex; gap:12px; padding:8px 16px; border-bottom:1px solid #30363d; background:rgba(248,81,73,0.03);">
           <div style="font-size:11px;">Saldo: <b id="live-balance-val" style="color:var(--green)">$—</b></div>
           <div style="font-size:11px;">Margem: <b id="live-margin-val" style="color:var(--yellow)">—</b></div>
           <button class="btn-danger" style="margin-left:auto; padding:2px 8px; font-size:10px;" onclick="confirmLiveStop()">🛑 STOP ALL LIVE</button>
        </div>

        <p class="meta" id="live-meta" style="padding:0 16px 8px;margin:0">—</p>

        <!-- SPRINT 12.20: Painel de Estatísticas LIVE (ROI, Funding, Fees) -->
        <div id="live-stats-panel" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; padding: 12px 16px; border-bottom: 1px solid #30363d;"></div>

        <div class="table-container">
          <div class="scroll-table scroll-table--paper">
            <table>
              <thead>
                <tr>
                <th>Símbolo</th><th>Entrada</th><th>Slippage</th><th>Atual</th><th title="Quantidade de Moedas">Size</th><th title="Valor Total Alavancado">Notional</th><th title="Margem USDT Real">Margem</th><th>Alav.</th><th>Fee In</th><th>Fee Out</th><th title="Risco Kelly Aplicado">Risk %</th><th>PnL %</th><th>PnL $</th>
                  <th>MFE</th><th>MAE</th><th>SL</th><th>TP</th><th>Tempo</th><th>Qualidade</th><th>Ação</th>
                </tr>
              </thead>
              <tbody id="live-rows"></tbody>
            </table>
          </div>
        </div>

        <!-- SPRINT 12.20: Tabela de Trades LIVE Fechados (com ROI, Funding, Fees) -->
        <div style="padding: 16px;">
          <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 8px; color: var(--text);">📊 Trades LIVE Fechados (ROI, Funding, Fees)</h3>
          <div class="table-container">
            <div class="scroll-table scroll-table--paper">
              <table>
                <thead>
                  <tr>
                    <th>Símbolo</th><th>Entrada</th><th>Saída</th><th>Tempo</th><th>PnL %</th><th>PnL $</th><th>ROI %</th><th>Fee Saída</th><th>Funding</th><th>Total Fees</th><th>Motivo</th>
                  </tr>
                </thead>
                <tbody id="live-closed-rows"></tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- SPRINT 12.20: Tabela de Trades LIVE Abertos (com Funding acumulado) -->
        <div style="padding: 0 16px 16px;">
          <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 8px; color: var(--text);">📈 Trades LIVE Abertos (Funding acumulado)</h3>
          <div class="table-container">
            <div class="scroll-table scroll-table--paper">
              <table>
                <thead>
                  <tr>
                    <th>Símbolo</th><th>Entrada</th><th>Atual</th><th>Tempo</th><th>PnL %</th><th>PnL $</th><th>Funding</th><th>Qty</th><th>Notional</th><th>Margem</th>
                  </tr>
                </thead>
                <tbody id="live-open-rows"></tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    <section class="card wide">
      <h2>🔍 Post-Trade Impact — Análise de Alpha Decay (O que aconteceu depois?)</h2>
      <p class="meta" style="padding:0 16px 8px;margin:0">Mostra a variação do preço desde o momento que o trade foi encerrado.</p>
      <div class="table-container">
        <div class="scroll-table scroll-table--post">
          <table>
            <thead>
              <tr>
                <th>Símbolo</th><th>Motivo Saída</th><th>Preço Saída</th><th>Variação Atual</th>
                <th>Após 5m</th><th>Após 15m</th><th>Após 30m</th><th>Após 1h</th><th>Após 4h</th><th>Após 12h</th><th>Após 24h</th>
                <th>Impacto</th>
              </tr>
            </thead>
            <tbody id="post-trade-rows"></tbody>
          </table>
        </div>
      </div>
    </section>

      <!-- Paper Trading Performance Charts (abaixo do Post-Trade) -->
    <section class="card wide">
      <!-- Linha 1: Equity + Drawdown -->
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px; border-top: 1px solid #30363d; height: 250px; align-items:stretch;">
        <div id="equity-container" style="min-width:0; display:flex; flex-direction:column;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:2px; font-weight:700;">📈 Equity</div>
            <div id="equity-stats" style="font-size:0.7rem; color:var(--text);"></div>
          </div>
          <canvas id="equityChart" style="flex:1 1 auto; border:1px solid rgba(63,185,80,0.2); border-radius:8px; background:linear-gradient(180deg,rgba(13,17,23,0.8) 0%,rgba(13,17,23,0.95) 100%);"></canvas>
        </div>
        <div id="drawdown-container" style="min-width:0; display:flex; flex-direction:column;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:2px; font-weight:700;">📉 Drawdown</div>
            <div id="drawdown-stats" style="font-size:0.7rem; color:var(--text);"></div>
          </div>
          <canvas id="drawdownChart" style="flex:1 1 auto; border:1px solid rgba(248,81,73,0.2); border-radius:8px; background:linear-gradient(180deg,rgba(13,17,23,0.8) 0%,rgba(13,17,23,0.95) 100%);"></canvas>
        </div>
      </div>

      <!-- Linha 2: Risco (Kelly) + Win Rate por Ativo -->
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px; border-top: 1px solid #30363d; height: 250px; align-items:stretch;">
        <div id="risk-container" style="min-width:0; display:flex; flex-direction:column;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:2px; font-weight:700;">⚖️ Risco (Kelly)</div>
            <div id="risk-stats" style="font-size:0.7rem; color:var(--text);"></div>
          </div>
          <canvas id="riskChart" style="flex:1 1 auto; border:1px solid rgba(210,153,34,0.2); border-radius:8px; background:linear-gradient(180deg,rgba(13,17,23,0.8) 0%,rgba(13,17,23,0.95) 100%);"></canvas>
        </div>
        <div id="winrate-container" style="min-width:0; display:flex; flex-direction:column;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="font-size:0.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:2px; font-weight:700;">🎯 Win Rate por Ativo</div>
            <div id="winrate-stats" style="font-size:0.7rem; color:var(--text);"></div>
          </div>
          <canvas id="winRateChart" style="flex:1 1 auto; border:1px solid rgba(88,166,255,0.2); border-radius:8px; background:linear-gradient(180deg,rgba(13,17,23,0.8) 0%,rgba(13,17,23,0.95) 100%);"></canvas>
        </div>
      </div>

      <!-- Liquidações fica no DOM mas sem ocupar espaço (mantém JS atualizado sem “largar” layout) -->
      <div style="display:none; padding:0; margin:0;">
        <canvas id="liquidationChart"></canvas>
      </div>
    </section>

  </main>
   <script>
    function playAlert() {
      try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, audioCtx.currentTime); // Tom de A5
        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.5); // Duração de 500ms
      } catch (e) {
        console.error("Som de alerta falhou (interação necessária):", e);
      }
    }

    let equityChart = null;
    function updateEquityChart(history) {
      if (!history || history.length < 2) {
        const container = document.getElementById('equity-container');
        if (container && !container.innerHTML.includes('Aguardando')) {
          container.innerHTML = '<div style="color:#555;text-align:center;padding-top:60px;font-size:11px">Performance — aguardando 1º fechamento</div>';
        }
        return;
      }
      let canvas = document.getElementById('equityChart');
      if (!canvas) {
        document.getElementById('equity-container').innerHTML = '<canvas id="equityChart"></canvas>';
        canvas = document.getElementById('equityChart');
      }
      const ctx = document.getElementById('equityChart').getContext('2d');
      const labels = history.map(h => new Date(h.ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      const values = history.map(h => h.capital);

      // Calcular estatísticas
      const current = values[values.length - 1];
      const initial = values[0];
      const max = Math.max(...values);
      const min = Math.min(...values);
      const change = ((current - initial) / initial * 100).toFixed(2);
      const changeColor = change >= 0 ? '#3fb950' : '#f85149';

      // Atualizar stats
      const statsEl = document.getElementById('equity-stats');
      if (statsEl) {
        statsEl.innerHTML = `<span style="color:${changeColor}">${change}%</span> | Max: $${max.toFixed(0)} | Min: $${min.toFixed(0)}`;
      }

      if (!equityChart) {
        const gradEq = ctx.createLinearGradient(0, 0, 0, 200);
        gradEq.addColorStop(0, 'rgba(63,185,80,0.35)');
        gradEq.addColorStop(1, 'rgba(63,185,80,0.02)');
        equityChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{
              label: 'Capital (USDT)',
              data: values,
              borderColor: '#3fb950',
              backgroundColor: gradEq,
              borderWidth: 2,
              tension: 0.4,
              fill: true,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHoverBackgroundColor: '#3fb950'
            }]
          },
          options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
              x: { display: true, grid: { color: 'rgba(48,54,61,0.5)', lineWidth: 1 }, ticks: { color: '#8b949e', font: { size: 10, weight: 600 } } },
              y: { display: true, grid: { color: 'rgba(48,54,61,0.6)', lineWidth: 1 }, ticks: { color: '#8b949e', font: { size: 10, weight: 600 }, callback: function(value){ return '$' + value.toLocaleString('en-US'); } } }
            },
            plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(22,27,34,0.95)', borderColor: '#30363d', borderWidth: 1, titleColor: '#e6edf3', bodyColor: '#8b949e', padding: 10 } }
          }
        });
      } else {
        equityChart.data.labels = labels;
        equityChart.data.datasets[0].data = values;
        equityChart.update('none');
      }
    }

    let drawdownChart = null;
    function updateDrawdownChart(history) {
      if (!history || history.length < 2) {
        const container = document.getElementById('drawdown-container');
        if (container && !container.innerHTML.includes('Aguardando')) {
          container.innerHTML = '<div style="color:#555;text-align:center;padding-top:60px;font-size:11px">Drawdown — aguardando primeiros trades para gerar curva</div>';
        }
        return;
      }
      if (!document.getElementById('drawdownChart')) {
        document.getElementById('drawdown-container').innerHTML = '<canvas id="drawdownChart"></canvas>';
      }
      const ctx = document.getElementById('drawdownChart').getContext('2d');
      const labels = history.map(h => new Date(h.ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      const values = history.map(h => (h.drawdown_pct || 0) * 100);

      // Calcular estatísticas
      const current = values[values.length - 1];
      const max = Math.max(...values);
      const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2);
      const maxColor = max > 10 ? '#f85149' : '#d29922';

      // Atualizar stats
      const statsEl = document.getElementById('drawdown-stats');
      if (statsEl) {
        statsEl.innerHTML = `<span style="color:${maxColor}">Max: ${max.toFixed(1)}%</span> | Atual: ${current.toFixed(1)}% | Média: ${avg}%`;
      }

      if (!drawdownChart) {
        const gradDd = ctx.createLinearGradient(0, 0, 0, 200);
        gradDd.addColorStop(0, 'rgba(248,81,73,0.35)');
        gradDd.addColorStop(1, 'rgba(248,81,73,0.02)');
        drawdownChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{
              label: 'Drawdown (%)',
              data: values,
              borderColor: '#f85149',
              backgroundColor: gradDd,
              borderWidth: 2,
              tension: 0.4,
              fill: true,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHoverBackgroundColor: '#f85149'
            }]
          },
          options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
              x: { display: true, grid: { display: false }, ticks: { color: '#8b949e', font: { size: 10, weight: 600 } } },
              y: { beginAtZero: true, grid: { color: 'rgba(48,54,61,0.6)', lineWidth: 1 }, ticks: { color: '#8b949e', font: { size: 10, weight: 600 }, callback: function(value){ return value.toFixed(1) + '%'; } } }
            },
            plugins: {
              legend: { display: false },
              tooltip: { backgroundColor: 'rgba(22,27,34,0.95)', borderColor: '#30363d', borderWidth: 1, titleColor: '#e6edf3', bodyColor: '#8b949e', padding: 10 }
            }
          }
        });
      } else {
        drawdownChart.data.labels = labels;
        drawdownChart.data.datasets[0].data = values;
        drawdownChart.update('none');
      }
    }

    let riskChart = null;
    function updateRiskChart(history) {
      const validData = (history || []).filter(h => h.risk_pct > 0);
      if (validData.length < 2) {
        if (riskChart) { riskChart.destroy(); riskChart = null; }
        const container = document.getElementById('risk-container');
        if (container && !container.innerHTML.includes('Kelly')) {
           container.innerHTML = '<div style="color:#555;text-align:center;padding-top:60px;font-size:11px">Kelly — aguardando 15+ trades</div>';
        }
        return;
      }
      // Garante que o canvas existe após o placeholder
      let canvas = document.getElementById('riskChart');
      if (!canvas) {
        document.getElementById('risk-container').innerHTML = '<canvas id="riskChart"></canvas>';
        canvas = document.getElementById('riskChart');
      }
      const ctx = document.getElementById('riskChart').getContext('2d');
      const labels = validData.map(h => new Date(h.ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      const values = validData.map(h => (h.risk_pct || 0) * 100);

      // Calcular estatísticas
      const current = values[values.length - 1];
      const max = Math.max(...values);
      const min = Math.min(...values);
      const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2);
      const riskColor = current > 5 ? '#f85149' : (current > 3 ? '#d29922' : '#3fb950');

      // Atualizar stats
      const statsEl = document.getElementById('risk-stats');
      if (statsEl) {
        statsEl.innerHTML = `<span style="color:${riskColor}">Atual: ${current.toFixed(1)}%</span> | Max: ${max.toFixed(1)}% | Média: ${avg}%`;
      }

      if (!riskChart) {
        const gradRisk = ctx.createLinearGradient(0, 0, 0, 200);
        gradRisk.addColorStop(0, 'rgba(210,153,34,0.35)');
        gradRisk.addColorStop(1, 'rgba(210,153,34,0.02)');
        riskChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{
              label: 'Risco Kelly (%)',
              data: values,
              borderColor: '#d29922',
              backgroundColor: gradRisk,
              borderWidth: 2,
              tension: 0.4,
              fill: true,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHoverBackgroundColor: '#d29922'
            }]
          },
          options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
              x: { display: true, grid: { display: false }, ticks: { color: '#8b949e', font: { size: 10, weight: 600 } } },
              y: { beginAtZero: true, grid: { color: 'rgba(48,54,61,0.6)', lineWidth: 1 }, ticks: { color: '#8b949e', font: { size: 10, weight: 600 }, callback: function(value){ return value.toFixed(1) + '%'; } } }
            },
            plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(22,27,34,0.95)', borderColor: '#30363d', borderWidth: 1, titleColor: '#e6edf3', bodyColor: '#8b949e', padding: 10 } }
          }
        });
      } else {
        riskChart.data.labels = labels;
        riskChart.data.datasets[0].data = values;
        riskChart.update('none');
      }
    }

    let liquidationChart = null;
    function updateLiquidationChart(liqHist) {
      if (!liqHist || liqHist.length < 2) {
        if (liquidationChart) { liquidationChart.destroy(); liquidationChart = null; }
        return;
      }

      const ctx = document.getElementById('liquidationChart').getContext('2d');
      const labels = liqHist.map(h => new Date(h.ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      const values = liqHist.map(h => h.value);

      if (!liquidationChart) {
        liquidationChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{
              label: 'Liquidações Acumuladas (USDT)',
              data: values,
              borderColor: '#f85149',
              backgroundColor: 'rgba(248, 81, 73, 0.1)',
              borderWidth: 2,
              tension: 0.2,
              fill: true,
              pointRadius: 2
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { display: true, grid: { display: false }, ticks: { color: '#8b949e', font: { size: 9 } } },
              y: { beginAtZero: true, grid: { color: '#30363d' }, ticks: { color: '#8b949e', font: { size: 9 } } }
            },
            plugins: { legend: { display: true, labels: { color: '#8b949e', font: { size: 10 } } } }
          }
        });
      } else {
        liquidationChart.data.labels = labels;
        liquidationChart.data.datasets[0].data = values;
        liquidationChart.update('none');
      }
    }

    let winRateChart = null;
    function updateWinRateChart(stats) {
      const data = stats.win_rate_by_symbol || {};
      const labels = Object.keys(data);
      if (labels.length === 0) {
        if (winRateChart) { winRateChart.destroy(); winRateChart = null; }
        const container = document.getElementById('winrate-container');
        if (container && !container.querySelector('canvas') && !container.innerHTML.includes('Aguardando')) {
          const placeholder = document.createElement('div');
          placeholder.style.cssText = 'color:#555;text-align:center;padding-top:60px;font-size:11px';
          placeholder.textContent = 'Win Rate por Ativo — disponível após 10+ trades';
          container.appendChild(placeholder);
        }
        return;
      }
      
      const values = Object.values(data);
      const colors = values.map(v => v >= 50 ? 'rgba(63, 185, 80, 0.6)' : 'rgba(248, 81, 73, 0.6)');
      
      // Calcular estatísticas
      const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);
      const wins = values.filter(v => v >= 50).length;
      const total = values.length;
      const globalWinRate = stats.win_rate_pct || 0;
      const winRateColor = globalWinRate >= 50 ? '#3fb950' : '#f85149';

      // Atualizar stats
      const statsEl = document.getElementById('winrate-stats');
      if (statsEl) {
        statsEl.innerHTML = `<span style="color:${winRateColor}">Global: ${globalWinRate.toFixed(1)}%</span> | Média: ${avg}% | ${wins}/${total} ativos >50%`;
      }
      
      const ctx = document.getElementById('winRateChart').getContext('2d');
      if (!winRateChart) {
        winRateChart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [{
              label: 'Win Rate por Ativo (%)',
              data: values,
              backgroundColor: colors,
              borderColor: '#0d1117',
              borderWidth: 2,
              borderRadius: 4,
              borderSkipped: false
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { color: '#8b949e', font: { size: 10, weight: 900 } }, grid: { display: false } },
              y: { min: 0, max: 100, ticks: { color: '#8b949e', font: { size: 10, weight: 900 } }, grid: { color: '#30363d', lineWidth: 1 } }
            },
            plugins: { 
              legend: { display: false },
              title: { display: true, text: 'Win Rate por Ativo (%)', color: '#8b949e', font: { size: 12, weight: 900 } }
            }
          }
        });
      } else {
        winRateChart.data.labels = labels;
        winRateChart.data.datasets[0].data = values;
        winRateChart.data.datasets[0].backgroundColor = colors;
        winRateChart.update('none');
      }
    }

    let currentSortField = 'score';
    let currentTimeframe = '5m';
    let hideLowVol = false;
    let volThreshold = 10;
    let favorites = new Set(JSON.parse(localStorage.getItem('ss_favorites') || '[]'));
    let alertActive = false;
    let lastSnapshot = null;

    window.toggleFav = (sym) => {
      if (favorites.has(sym)) favorites.delete(sym);
      else favorites.add(sym);
      localStorage.setItem('ss_favorites', JSON.stringify([...favorites]));
      if (lastSnapshot) render(lastSnapshot);
    };

    function drawSpark(id, values, color) {
      const canvas = document.getElementById(id);
      if (!canvas || !values || values.length < 2) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min || 1;
      
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      values.forEach((v, i) => {
        const x = (i / (values.length - 1)) * w;
        const y = h - ((v - min) / range) * h;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }

    const fmt = (n, d=2) => {
      if (n == null) return '—';
      const num = Number(n);
      if (!Number.isFinite(num)) return '—';
      if (Math.abs(num) < 1e-6 && num !== 0) return num.toExponential(2);
      return num.toLocaleString('en-US', {minimumFractionDigits:d, maximumFractionDigits:d});
    };
    // OI já vem em milhões (market_view: oi_notional_m)
    // Ex: 1.2345 -> "1.23M"
    const fmtOI = (n) => {
      if (n == null) return '—';
      const v = Number(n);
      if (!Number.isFinite(v)) return '—';
      return v.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}) + 'M';
    };

    // Formata tendência com setas (OI sobe = verde/up, LSR cai = verde/down)
    const fmtTrend = (val, type) => {
      if (val == null || val === 0) return '<span class="cell-dim">0.00</span>';
      const abs = Math.abs(val);
      const sign = val > 0 ? '+' : '';
      const text = sign + fmt(abs, 2);
      
      if (type === 'oi') {
        // OI Subindo é bom (verde/seta pra cima)
        return val > 0 ? `<span class="pos">▲ ${text}</span>` : `<span class="neg">▼ ${text}</span>`;
      } else {
        // LSR Caindo é bom (verde/seta pra baixo)
        return val < 0 ? `<span class="pos">▼ ${text}</span>` : `<span class="neg">▲ ${text}</span>`;
      }
    };
    // Efeitos visuais intensos para sinais fortes
    const isStrong = (r) =>
      r.status === 'squeeze'
      || (r.score >= 70 && (r.cvd_change_pct || 0) >= 15);

    // Classe da linha toda: quando o sinal for QUENTE, usa fundo esverdeado
    const rowClass = (r) => {
      if (!isStrong(r)) return '';
      const intensity = r.score >= 90 ? 'super' : (r.score >= 80 ? 'hot' : 'warm');
      return 'row-' + intensity;
    };

    const cellHighlight = (r, field, thresholdHigh, thresholdMid, invert = false) => {
      if (!isStrong(r)) return '';
      const v = r[field];
      if (v == null) return 'cell-dim';
      if (typeof v === 'number') {
        if (invert) {
            if (v <= thresholdHigh) return 'cell-glow';
            if (v <= thresholdMid) return 'cell-hot';
        } else {
            if (v >= thresholdHigh) return 'cell-glow';
            if (v >= thresholdMid) return 'cell-hot';
        }
      }
      return '';
    };

    // % de crescimento (delta percentual): CVD, OI, LSR
    const fmtChgPct = (n, decimals) => {
      if (n == null) return '—';
      const v = Number(n);
      if (!Number.isFinite(v)) return '—';
      const d = decimals != null ? decimals : 1;
      const s = v > 0 ? '+' : '';
      // Indicador de teto: CVD pode ser capped em 999.9
      const capped = Math.abs(v) >= 999.0;
      return (capped ? '>' : '') + s + fmt(Math.min(Math.abs(v), 999.9) * (v < 0 ? -1 : 1), d) + '%';
    };

    const fmtScore = (r) => {
      const s = r.score || 0;
      // SPRINT 7.7: Cores eAssets (Sniper DNA)
      const color = s >= 80 ? '#3fb950' : (s >= 60 ? '#d4a017' : (s >= 35 ? '#6b5900' : '#5c1a1a'));
      const cascade = r.liq_cascade ? '<div style="color:#ff6b00;font-size:0.6rem;font-weight:900;animation:pulse 0.8s infinite;margin-bottom:2px;">🔥 CASCATA</div>' : '';
      return `
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; min-width:80px;">
          ${cascade}
          <div style="display:flex; align-items:center; gap:6px; width:100%;">
            <div style="flex-grow:1; height:6px; background:#21262d; border-radius:3px; overflow:hidden; border:1px solid #30363d;">
              <div style="width:${s}%; height:100%; background:${color}; box-shadow: 0 0 4px ${color}80;"></div>
            </div>
            <span style="font-size:10px; font-weight:900; min-width:20px; color:${color}">${s}</span>
          </div>
        </div>
      `;
    };

    const fmtEMA = (v) => {
      if (v == null) return '<span class="cell-dim">—</span>';
      let color = 'var(--muted)';
      if (v >= 5) color = 'var(--green)';
      else if (v >= 1) color = 'rgba(63, 185, 80, 0.65)';
      else if (v <= -5) color = 'var(--red)';
      else if (v <= -1) color = 'rgba(248, 81, 73, 0.65)';
      const weight = Math.abs(v) >= 5 ? '900' : (Math.abs(v) >= 3 ? '700' : '400');
      return `<span style="color:${color}; font-weight:${weight};">${v > 0 ? '+' : ''}${v}</span>`;
    };

    const fmtRange = (v) => {
      if (v == null || v === 0) return '<span class="cell-dim">—</span>';
      let html = '';
      for (let i = 0; i < v; i++) html += '▪';
      let color = v >= 4 ? 'var(--green)' : (v >= 3 ? 'var(--yellow)' : 'var(--muted)');
      return `<span style="color:${color}; letter-spacing:1px; font-size:1.1rem; line-height:1;">${html}</span>`;
    };

    const chgPctClass = (val, type) => {
      if (val == null) return '';
      const abs = Math.abs(val);
      // CVD % crescendo → positivo (verde); OI crescendo → positivo; LSR caindo → negativo (verde)
      if (type === 'lsr') {
        if (val <= -5) return 'pos';    // LSR queda >5% = shorts em pânico
        if (val <= -2) return '';
        return 'neg';
      }
      if (abs > 50) return 'pos';     // crescimento massivo
      if (abs > 15) return '';
      return 'neg';
    };
    // CVD streak: destacar se há múltiplos minutos consecutivos de CVD positivo
    const fmtStreak = (n) => n != null ? (n >= 3 ? '🔥' + n : (n >= 2 ? '⚡'+n : n)) : '—';
    const statusLabel = { squeeze: '🔥 SQUEEZE', potential: '🚀 Potencial', watch: '—', warming: '⏳ Aquecendo' };
    const statusClass = { squeeze: 'status-squeeze', potential: 'status-potential', watch: 'status-watch', warming: 'status-watch' };

    const fmtPct = (val) => val == null ? '—' : (val > 0 ? '+' : '') + fmt(val) + '%';
    const fmtCVD = (n) => {
      if (n == null) return '—';
      const v = Number(n);
      if (!Number.isFinite(v)) return '—';
      const s = v > 0 ? '+' : '';
      return s + fmt(v, 0);
    };
    function hmClass(val) {
      if (val == null) return '';
      const abs = Math.abs(val);
      const sign = val > 0 ? 'pos' : 'neg';
      if (abs > 1.5) return `hm-${sign}-3`;
      if (abs > 0.5) return `hm-${sign}-2`;
      if (abs > 0.1) return `hm-${sign}-1`;
      return '';
    }

    const tradesLvlBadge = (lvl) => {
      if (lvl == null || lvl === 0) return '<span style="color:#8b949e">—</span>';
      const v = Math.max(0, Math.min(4, Math.floor(lvl)));
      const colors = ['#333','#6b5900','#d4a017','#e8a000','#ff6b00'];
      const labels = ['—','1×','2×','3×','4×'];
      const bg = colors[v] || '#333';
      const txt = labels[v] || '—';
      return `<span style="background:${bg}; color:#fff; padding:1px 6px; border-radius:3px; font-size:10px; font-weight:900; letter-spacing:0.5px;">${txt}</span>`;
    };

      function render(data) {
        lastSnapshot = data;

        // SPRINT 8.3: Dashboard warmup indicator
        const isWarmup = data.warmup_remaining !== undefined && data.warmup_remaining > 0;
        document.body.classList.toggle('is-loading', Boolean(isWarmup));

        // Update Warmup Timer Badge no Cabeçalho (Sprint 6.26) - Sempre atualiza antes de qualquer lógica
        const warmupEl = document.getElementById('warmup-timer');
        if (warmupEl) {
          if (isWarmup) {
            warmupEl.style.display = 'inline-block';
            warmupEl.textContent = `⏳ WARMUP: ${Math.round(data.warmup_remaining)}s`;
          } else {
            warmupEl.style.display = 'none';
          }
        }

        // Warmup: render “hard” e retorne cedo.
        // Por quê: qualquer erro de render em seções posteriores (especialmente LIVE)
        // pode impedir que o tbody seja atualizado e o operador vê “warmup travado”.
        if (isWarmup) {
          const pct = Math.max(0, Math.min(100, Math.round(data.warmup_pct || 0)));
          const tbody = document.getElementById('rows');
          if (tbody) {
            tbody.innerHTML = [
              '<tr><td colspan="99" style="padding:16px; text-align:center">',
              '<div style="background:#1a1a1a; border:1px solid #d4a017; border-radius:6px; padding:12px; max-width:460px; margin:0 auto">',
              '<div style="color:#d4a017; font-weight:600; margin-bottom:8px">⏳ Aquecendo Motor — ' + String(Math.ceil(data.warmup_remaining)) + 's restantes</div>',
              '<div style="background:#333; border-radius:3px; height:6px">',
              '<div style="background:#d4a017; width:' + String(pct) + '%; height:6px; border-radius:3px; transition:width 1s"></div>',
              '</div>',
              '<div style="color:#555; font-size:10px; margin-top:6px">Indicadores calibrando — sinais bloqueados durante este período</div>',
              '</div>',
              '</td></tr>'
            ].join('');
          }
          // Importante: não retornar cedo. Durante warmup precisamos ainda renderizar LIVE (saldo e tabelas)
        }

        // Notificação discreta no título da aba (Sprint 4)
        const highScores = (data.rows || []).filter(r => r.score >= 90).length;
        document.title = highScores > 0 ? `🔥 (${highScores}) SqueezeSniper V4` : 'SqueezeSniper V4';

      // Update Squeezometer (Sprint 5.7)
      const sqLevel = Math.round(data.market_squeeze_level || 0);
      const sqFill = document.getElementById('sq-fill');
      const sqVal = document.getElementById('sq-val');
      if (sqFill && sqVal) {
        sqFill.style.width = sqLevel + '%';
        
        // Cor dinâmica incluindo estado de PAUSA (cinza)
        let color = sqLevel > 80 ? 'var(--red)' : (sqLevel > 60 ? 'var(--yellow)' : 'var(--green)');
        let label = `${sqLevel}/100`;
        
        if (data.market_paused) {
            color = '#444'; // Cinza escuro para pausa
            label += ' (PAUSED 💤)';
        }
        
        sqFill.style.backgroundColor = color;
        sqVal.style.color = color; sqFill.style.boxShadow = `0 0 8px ${color}80`;
        sqVal.innerHTML = `${label} ${sqLevel > 80 ? '🔥' : (sqLevel > 60 ? '⚡' : '')}`;

        if (sqLevel > 80 && !alertActive) {
          playAlert();
          alertActive = true;
        } else if (sqLevel <= 80) {
          alertActive = false;
        }
      }

      const mode = document.getElementById('modeToggle');
      // SPRINT 12.64: Atualiza botão de modo baseado no trading_mode do snapshot
      const tradingMode = data.trading_mode || 'paper';
      mode.textContent = tradingMode.toUpperCase();
      mode.className = `badge ${tradingMode}`;

      // F-02: colapsa automaticamente o cockpit oposto ao modo ativo
      const paperCockpit = document.getElementById('paper-cockpit');
      const liveCockpit  = document.getElementById('live-cockpit');
      if (paperCockpit && liveCockpit) {
        if (tradingMode === 'live') {
          paperCockpit.style.display = 'none';
          liveCockpit.style.display  = '';
        } else {
          liveCockpit.style.display  = 'none';
          paperCockpit.style.display = '';
        }
      }
      const st = data.stats || {};

      // SPRINT 6.37: Filtro Visual de Peneira (Score >= 0)
      // Ajustado para 0 para garantir que o painel mostre os dados populando desde o início da sessão.
      let rows = [...(data.rows || [])].filter(r => (r.score || 0) >= 0);

      document.getElementById('meta').textContent =
        `${data.symbol_count} símbolos (${rows.length} Sniper Zone) | preço ${st.with_price||0} | OI ${st.with_oi||0} | uptime ${data.uptime_sec}s`;

      if (hideLowVol) {
        rows = rows.filter(r => (r.vol_24h_m || 0) >= volThreshold);
      }

      // Lógica de Ordenação Dinâmica com Favoritos (Sprint 4)
      rows.sort((a, b) => {
          const isFavA = favorites.has(a.symbol);
          const isFavB = favorites.has(b.symbol);
          if (isFavA && !isFavB) return -1;
          if (!isFavA && isFavB) return 1;

          const valA = a[currentSortField] ?? -999999;
          const valB = b[currentSortField] ?? -999999;
          
          if (currentSortField === 'lsr_change_pct') {
              return valA - valB;
          }
          return valB - valA;
      });

      const macroHtml = [];
      const m = data.macro || {};

      // Logo removida da barra macro (esteticamente desnecessária)

      // SPRINT 11.29: Renderização da lista de ativos fortes (Req 2 Doreto)
      if (m.strong_than_btc && m.strong_than_btc.length > 0) {
          macroHtml.push(`
              <div style="display: flex; flex-direction: column; align-items: center; border: 1px solid #3fb950; border-radius: 4px; padding: 4px 12px; background: rgba(63, 185, 80, 0.05);">
                  <div style="font-size: 0.65rem; color: var(--green); text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">💪 Strong vs BTC</div>
                  <div style="font-size: 0.8rem; font-weight: bold; color: #fff;">${m.strong_than_btc.join(' | ')}</div>
              </div>
          `);
      }

      for (const sym of ["BTCUSDT", "ETHUSDT", "BTCDOMUSDT"]) {
          const md = m[sym];
          if (md) {
              const pc = md.pc_1h != null ? fmtPct(md.pc_1h) : '—';
              const pcClass = md.pc_1h > 0 ? 'pos' : (md.pc_1h < 0 ? 'neg' : '');
              const price = sym === "BTCDOMUSDT" ? fmt(md.price || 0, 2) : fmt(md.price || 0, 0);
              const rsi = md.rsi_5m ? fmt(md.rsi_5m, 1) : '—';
              const rsiColor = md.rsi_5m > 65 ? 'pos' : (md.rsi_5m < 40 ? 'neg' : '');
              macroHtml.push(`
                  <div style="display: flex; flex-direction: column; align-items: center; min-width: 140px;">
                      <div style="font-size: 0.8rem; color: #8b949e; letter-spacing: 1px;">${sym.replace('USDT','')}</div>
                      <div style="font-size: 1.3rem; font-weight: bold; margin: 4px 0;">$${price}</div>
                      <div style="font-size: 0.85rem;">1h: <span class="${pcClass}">${pc}</span> | RSI: <span class="${rsiColor}">${rsi}</span></div>
                  </div>
              `);
          }
      }
      if (macroHtml.length > 0) {
          document.getElementById('macro-bar').innerHTML = macroHtml.join('<div style="border-left: 1px solid #30363d; height: 50px; margin-top: 5px;"></div>');
      }

      // Atualizar headers da tabela conforme TF
      document.getElementById('th-exp').textContent = 'exp (' + currentTimeframe + ')';
      document.getElementById('th-ema').textContent = 'EMA (' + currentTimeframe + ')';
      document.getElementById('th-oit').textContent = 'oi↑ (' + currentTimeframe + ')';

      // Heatmap Momentum Grid (Sprint 4C - 10x10)
      const heatmapRows = rows.slice(0, 100);
      const nowTs = Date.now() / 1000;
      const treemapHtml = heatmapRows.map(r => {
          let bg = '#161b22';
          let color = '#fff';
          
          if (r.score >= 70) { bg = '#1b4d1b'; } // Verde escuro
          else if (r.score >= 50) { bg = '#238636'; } // Verde
          else if (r.score >= 30) { bg = '#826a1b'; } // Amarelo
          else { bg = '#631c1c'; } // Vermelho
          
          // Check for very recent signals (< 60s) from the signals buffer to trigger pulse
          const isRecent = (data.signals || []).some(s => s.symbol === r.symbol && (nowTs - s.logged_at) < 60);
          const pulseClass = isRecent ? 'pulse-signal' : '';
          
          // SPRINT 6.25: Borda mais espessa para ativos de Elite (Score > 90)
          const borderStyle = r.score > 90 ? 'border: 2px solid var(--green); box-shadow: 0 0 6px rgba(63, 185, 80, 0.4);' : 'border: 1px solid rgba(255,255,255,0.05);';
          
          return `<div class="hm-box ${pulseClass}" style="background: ${bg}; color: ${color}; ${borderStyle}" 
                       title="Score: ${r.score}/100 | 15m: ${fmtPct(r.pc_15m)} | OI Δ%: ${fmtChgPct(r.oi_change_pct)}">
              ${r.symbol.replace('USDT', '')}
              <div class="val">${r.score}</div>
          </div>`;
      });
      // Heatmap strip compacto (max ~64px): top 40 por score
      const strip = document.getElementById('heatmap-strip');
      if (strip) {
        strip.innerHTML = heatmapRows.slice(0, 40).map(r => {
          let bg = '#161b22';
          if (r.score >= 70) bg = '#1b4d1b';
          else if (r.score >= 50) bg = '#238636';
          else if (r.score >= 30) bg = '#826a1b';
          else bg = '#631c1c';

          const isRecent = (data.signals || []).some(s => s.symbol === r.symbol && (nowTs - s.logged_at) < 60);
          const pulse = isRecent ? 'animation: pulse 1s infinite;' : '';
          
          // SPRINT 6.25: Borda verde brilhante para Elite
          const eliteBorder = r.score > 90 ? 'border: 2px solid var(--green); box-shadow: 0 0 4px var(--green);' : 'border: 1px solid rgba(255,255,255,0.1);';

          return `<div style="
            background:${bg};
            ${pulse}
            ${eliteBorder}
            min-width:66px; height:30px;
            display:flex; flex-direction:column;
            align-items:center; justify-content:center;
            border-radius:4px; cursor:pointer;
            font-size:10px; line-height:1.2;" title="Score: ${r.score}/100">
              <span style="color:#fff;font-weight:600;">${r.symbol.replace('USDT','')}</span>
              <span style="color:#aaa;">${r.score}</span>
            </div>`;
        }).join('');
      }

      try {
      const strongCard = document.getElementById('strong-signals-card');
      const urlParams = new URLSearchParams(window.location.search);
      const debugStrong = urlParams.get('debugStrong') === '1';
      const srows = (debugStrong
        ? rows.slice(0, 1)
        : rows.filter(r =>
            r.exp_btc != null && r.exp_btc >= 0.012
            && (r.exp || 0) >= 0.02
            && (r.cvd_change_pct || 0) >= 10
          ).slice(0, 8));

      const stbody = document.getElementById('strong-rows');
      if (srows.length > 0) {
        stbody.innerHTML = srows.map(r => {
          let sc = r.score >= 80 ? '#3fb950' : (r.score >= 50 ? '#d29922' : '#e6edf3');
          const cvdChgCls = chgPctClass(r.cvd_change_pct, 'cvd');
          return `<tr style="background: rgba(${r.exp_btc >= 0.3 ? '63,185,80' : '210,153,34'},0.1);">
            <td title="Vol 1h: $${fmt(r.volume_1h / 1e6, 1)}M | Spread: ${fmt(r.bid_ask_spread, 3)}% | T/s: ${fmt(r.trades_second, 1)}"><b>${r.symbol.replace('USDT','')}</b></td>
            <td class="${cellHighlight(r,'score', 80, 50)}">${fmtScore(r)}</td>
            <td class="${cvdChgCls === 'pos' ? (r.cvd_change_pct >= 100 ? 'cell-glow' : 'cell-hot') : ''}" style="font-weight:bold">${fmtChgPct(r.cvd_change_pct)} ${r.cvd_streak?fmtStreak(r.cvd_streak):''}</td>
            <td class="${cellHighlight(r,'oi_change_pct', 5, 1)}">${fmtChgPct(r.oi_change_pct, 2)}</td>
            <td class="${cellHighlight(r,'lsr_change_pct', -10, -5)}">${fmtChgPct(r.lsr_change_pct)}</td>
            <td class="${r.exp_btc>=0?'pos':'neg'}">${r.exp_btc>=0?'+':''}${fmt(r.exp_btc,4)}</td>
            <td style="text-align:center">${fmt(r.trades_1m, 0)}</td>
            <td style="text-align:center; white-space:nowrap; min-width:44px;" title="T.Lvl (0-4) | T/min (5m): ${r.trades_minute_5m != null ? fmt(r.trades_minute_5m,1) : '—'}">${tradesLvlBadge(r.trades_level)}</td>
            <td class="${cellHighlight(r,'rsi_5m', 60, 50)}" style="text-align:center; white-space:nowrap; min-width:60px;">${r.rsi_5m != null ? fmt(r.rsi_5m,1) : '—'}</td>
            <td class="status-cell ${statusClass[r.status]||''}" style="font-weight:bold; text-align:center; white-space:nowrap; min-width:95px;">${statusLabel[r.status]||r.status}</td>
          </tr>`;
        }).join('');
      } else {
        stbody.innerHTML = '<tr><td colspan="10" class="meta" style="text-align:center; padding:12px;">Aguardando ignição institucional (ativos descolados do BTC)...</td></tr>';
      }
      const tbody = document.getElementById('rows');
      
      if (isWarmup) {
        const pct = Math.max(0, Math.min(100, Math.round(data.warmup_pct || 0)));
        tbody.innerHTML = [
          '<tr><td colspan="99" style="padding:16px; text-align:center">',
          '<div style="background:#1a1a1a; border:1px solid #d4a017; border-radius:6px; padding:12px; max-width:460px; margin:0 auto">',
          '<div style="color:#d4a017; font-weight:600; margin-bottom:8px">⏳ Aquecendo Motor — ' + String(Math.ceil(data.warmup_remaining)) + 's restantes</div>',
          '<div style="background:#333; border-radius:3px; height:6px">',
          '<div style="background:#d4a017; width:' + String(pct) + '%; height:6px; border-radius:3px; transition:width 1s"></div>',
          '</div>',
          '<div style="color:#555; font-size:10px; margin-top:6px">Indicadores calibrando — sinais bloqueados durante este período</div>',
          '</div>',
          '</td></tr>'
        ].join('');
      } else {
        tbody.innerHTML = rows.map((r, idx) => {
        let scoreColor = r.score >= 80 ? 'color: #3fb950; font-weight: bold;' : (r.score >= 50 ? 'color: #d29922;' : 'color: #8b949e;');
        const rc = rowClass(r);
        const isTop = idx < 5;
        return `
        <tr class="${rc}">
            <td title="Vol 1h: $${fmt(r.volume_1h / 1e6, 1)}M | Spread: ${fmt(r.bid_ask_spread, 3)}% | T/s: ${fmt(r.trades_second, 1)}">
            <span class="fav-star ${favorites.has(r.symbol)?'active':''}" onclick="toggleFav('${r.symbol}')">★</span>
            <b>${r.symbol.replace('USDT','')}</b>
          </td>
          <td>${fmt(r.price, 4)}</td>
          <td class="${r.pc_24h > 0 ? 'pos' : (r.pc_24h < 0 ? 'neg' : '')}" style="font-weight:700">${fmtPct(r.pc_24h)}</td>
          <td class="${cellHighlight(r,'score', 90, 75)}">${fmtScore(r)}</td>
          <td class="${cellHighlight(r,'cvd_change_pct', 50, 20)} ${chgPctClass(r.cvd_change_pct,'cvd')}" style="font-weight:700">${fmtChgPct(r.cvd_change_pct)}</td>
          <td>${isTop ? `<canvas id="cvd-spk-${r.symbol}" width="40" height="14"></canvas>` : ''}</td>
          <td class="${cellHighlight(r,'oi_change_pct', 5, 1)}">${fmtChgPct(r.oi_change_pct, 2)}</td>
          <td>${isTop ? `<canvas id="oi-spk-${r.symbol}" width="40" height="14"></canvas>` : ''}</td>
          <td class="${cellHighlight(r,'lsr_change_pct', -10, -5)}">${fmtChgPct(r.lsr_change_pct)}</td>
          <td class="${r.oi_accel==null?'':(r.oi_accel>0?'pos':'neg')}">${r.oi_accel==null?'—':((r.oi_accel>0?'+':'')+fmt(r.oi_accel,3))}</td>
          <td class="${r.exp==null?'':(r.exp>=0?'pos':'neg')}" title="1m: ${fmt(r.exp_1m,4)} | 1h: ${r.exp_1h}">${r.exp==null?'—':(r.exp>=0?'+':'')+fmt(r.exp,4)}</td>
          <td class="${r.exp_btc==null?'':(r.exp_btc>=0?'pos':'neg')}">${r.exp_btc==null?'—':(r.exp_btc>=0?'+':'')+fmt(r.exp_btc,4)}</td>
          <td style="text-align:center" title="15m: ${r.ema_trend_15m} | 1h: ${r.ema_trend_1h}">${fmtEMA(r.ema_trend)}</td>
          <td class="${r.ob_imbalance > 1.5 ? 'pos' : (r.ob_imbalance < 0.5 ? 'neg' : '')}" title="Order Book Bid/Ask Ratio">${fmt(r.ob_imbalance, 2)}</td>
          <td class="${r.funding_rate > 0.0003 ? 'neg' : (r.funding_rate < -0.0001 ? 'pos' : '')}" title="Funding Rate">${r.funding_rate ? fmt(r.funding_rate * 100, 4) + '%' : '—'}</td>
          <td>${fmtOI(r.oi_notional_m)}</td>
          <td class="${r.oi_trend==null?'':(r.oi_trend>=0?'pos':'neg')}" title="1m: ${fmt(r.oi_trend_1m,2)} | 1h: ${fmt(r.oi_trend_1h,2)}">${r.oi_trend==null?'—':(r.oi_trend>=0?'+':'')+fmt(r.oi_trend,2)}</td>
          <td class="${r.lsr==null?'':(r.lsr<1?'pos':'neg')}" title="${r.lsr_is_proxy ? 'Estimado por Taker Vol' : 'Oficial Binance'}">${r.lsr_is_proxy ? '~' : ''}${fmt(r.lsr, 2)}</td>
          <td class="${r.lsr_trend==null?'':(r.lsr_trend<0?'pos':'neg')}" title="1m: ${fmt(r.lsr_trend_1m,2)} | 1h: ${fmt(r.lsr_trend_1h,2)}">${r.lsr_trend==null?'—':(r.lsr_trend>=0?'+':'')+fmt(r.lsr_trend,2)}</td>
          <td class="${r.liq_short_1m > 10000 ? 'liq-blink' : ''}" style="color:#d29922; font-weight:bold; transition: background 0.3s;">${r.liq_short_1m > 0 ? '$' + fmt(r.liq_short_1m, 0) : '—'}</td>
          <td class="${r.trades_10s > 25 ? 'pos' : ''}">${r.trades_10s > 0 ? fmt(r.trades_10s, 0) : '—'}</td>
          <td>${fmt(r.trades_1m, 0)}</td>
          <td style="text-align:center; white-space:nowrap; min-width:44px;" title="T.Lvl (0-4) | T/min (5m): ${r.trades_minute_5m != null ? fmt(r.trades_minute_5m,1) : '—'}">${tradesLvlBadge(r.trades_level)}</td>
          <td class="${r.rsi_5m==null?'':(r.rsi_5m > 65 ? 'pos' : r.rsi_5m < 40 ? 'neg' : '')}" style="white-space:nowrap; min-width:58px; text-align:center">${r.rsi_5m != null ? fmt(r.rsi_5m, 1) : '—'}</td>
          <td class="${statusClass[r.status]||''}" style="font-weight:bold; white-space:nowrap; min-width:95px; text-align:center">${statusLabel[r.status]||r.status}</td>
        </tr>`;
      }).join('');
      }

      rows.slice(0, 5).forEach(r => {
        drawSpark(`cvd-spk-${r.symbol}`, r.cvd_hist, '#d29922');
        drawSpark(`oi-spk-${r.symbol}`, r.oi_hist, '#58a6ff');
      });
      } catch (err) {
        console.error("Erro ao renderizar tabelas:", err);
      }
      // === SEÇÃO DE PAPER TRADING ===

      const paper = data.paper || {};
      const pst = paper.stats || {};
      
      const initialCapInput = document.getElementById('initialCapitalInput');
      const rskPctInput = document.getElementById('riskPctInput');
      const maxPosInput = document.getElementById('maxPosInput');

      // Render stats panel
      const statsPanel = document.getElementById('paper-stats-panel');
      const statsHtml = [];
      
      // Capital metrics
      const currentCapital = paper.current_capital || 0;
      const initialCapital = paper.initial_capital || 0;
      const riskPct = (paper.risk_pct_per_trade || 0) * 100;
      const totalReturnPct = ((currentCapital - initialCapital) / initialCapital * 100);
      const riskPerTrade = currentCapital * (paper.risk_pct_per_trade || 0);
      
      statsHtml.push(`
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
          <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Capital Atual</div>
          <div style="font-size: 1.8rem; font-weight: bold; color: ${currentCapital >= initialCapital ? '#3fb950' : '#f85149'};">
            $${fmt(currentCapital, 2)}
          </div>
        </div>
      `);
      
      statsHtml.push(`
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
          <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Retorno Total</div>
          <div style="font-size: 1.8rem; font-weight: bold; color: ${totalReturnPct >= 0 ? '#3fb950' : '#f85149'};">
            ${totalReturnPct >= 0 ? '+' : ''}${fmt(totalReturnPct, 2)}%
          </div>
        </div>
      `);
      
      statsHtml.push(`
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
          <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Risco/Trade</div>
          <div style="font-size: 1.4rem; font-weight: bold; color: #d29922;">
            ${fmt(riskPct, 0)}% ($${fmt(riskPerTrade, 2)})
          </div>
        </div>
      `);
      
      statsHtml.push(`
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
          <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Total Trades</div>
          <div style="font-size: 1.4rem; font-weight: bold; color: #e6edf3;">${(pst.closed_count||0) + (pst.open_count||0)}</div>
        </div>
      `);
      
      statsHtml.push(`
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
          <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Win Rate</div>
          <div style="font-size: 1.4rem; font-weight: bold; color: ${(pst.win_rate_pct||0) >= 50 ? '#3fb950' : '#f85149'};">${(pst.win_rate_pct||0)}%</div>
        </div>
      `);
      
      statsHtml.push(`
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
          <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Wins / Losses</div>
          <div style="font-size: 1.4rem; font-weight: bold;">
            <span style="color: #3fb950;">${pst.wins||0}</span>
            <span style="color: #8b949e;"> / </span>
            <span style="color: #f85149;">${pst.losses||0}</span>
          </div>
        </div>
      `);
      
      statsPanel.innerHTML = statsHtml.join('');
      
      // Update capital and risk inputs from current paper state
      if (initialCapInput && paper.initial_capital != null && document.activeElement !== initialCapInput) {
        initialCapInput.value = paper.initial_capital;
      }
      if (rskPctInput && paper.risk_pct_per_trade != null && document.activeElement !== rskPctInput) {
        rskPctInput.value = (paper.risk_pct_per_trade * 100).toFixed(1);
      }
      const levInput = document.getElementById('leverageInput'); // SPRINT 11.28
      if (levInput && paper.leverage != null && document.activeElement !== levInput) { // SPRINT 11.28
        levInput.value = paper.leverage; // SPRINT 11.28
      }
      if (maxPosInput && paper.max_open_positions != null && document.activeElement !== maxPosInput) {
        maxPosInput.value = paper.max_open_positions;
      }
      
      document.getElementById('paper-meta').textContent =
        'Abertas: ' + (pst.open_count||0) + ' | Win rate ' + (pst.win_rate_pct||0) + '%';

      // Sprint 9.6.4: exibir apenas top 5 trades abertos por PnL%
      const openTrades = (paper.open || []);
      const openCount = openTrades.length;
      const wr = pst.win_rate_pct || 0;

      const paperOpenBadge = document.getElementById('paper-open-count-badge');
      if (paperOpenBadge) paperOpenBadge.textContent = `${openCount} abertos`;

      const paperWrBadge = document.getElementById('paper-wr-header-badge');
      if (paperWrBadge) {
        paperWrBadge.textContent = `WR ${wr}%`;
        paperWrBadge.style.color = wr >= 50 ? '#3fb950' : '#f85149';
      }

      const topOpen = openTrades
        .slice()
        .sort((a, b) => ((b.live && b.live.pnl_pct) || 0) - ((a.live && a.live.pnl_pct) || 0))
        .slice(0, 5);

      const paperRows = topOpen.concat((paper.closed_recent || []).slice(0, 8));
      const tbodyPaper = document.getElementById('paper-rows');

      // 4.2 LIVE Long — render mínimo (read-only)
      const live = data.live || {};
      const livePositions = Array.isArray(live.positions) ? live.positions : [];
      const tbodyLive = document.getElementById('live-rows');
      if (tbodyLive) {
        const liveStats = {
          open_count: livePositions.length || 0,
        };

        // Badge/Meta básicas (não dependem de shape avançado)
        const liveMeta = document.getElementById('live-meta');
        const liveStatsPanel = document.getElementById('live-stats-panel');
        const liveWrBadge = document.getElementById('live-wr-header-badge');
        const liveOpenBadge = document.getElementById('live-open-count-badge');

        // SPRINT 11.25: Injeção de Telemetria Financeira LIVE
        const apiOk = live.api_status && live.api_status.ok;
        const apiDot = document.getElementById('live-api-dot');
        const apiText = document.getElementById('live-api-text');
        if (apiDot) apiDot.style.background = apiOk ? 'var(--green)' : 'var(--red)';
        if (apiText) apiText.textContent = apiOk ? 'API ONLINE' : 'API OFFLINE';

        const balVal = document.getElementById('live-balance-val');
        if (balVal) {
            const walBal = live.balance && live.balance.totalWalletBalance;
            if (walBal != null && walBal > 0) {
                balVal.textContent = `$${fmt(walBal, 2)}`;
                balVal.style.color = 'var(--green)';
            } else if (balVal.textContent === '$—') {
                balVal.textContent = '⏳';
                balVal.style.color = '#888';
            }
        }
        const marginVal = document.getElementById('live-margin-val');
        if (marginVal) {
            const marBal = live.balance && live.balance.totalMarginBalance;
            if (marBal != null && marBal > 0) {
                marginVal.textContent = `$${fmt(marBal, 2)}`;
                marginVal.style.color = 'var(--yellow)';
            } else if (marginVal.textContent === '$—') {
                marginVal.textContent = '⏳';
                marginVal.style.color = '#888';
            }
        }
        // Atualiza o input de capital com o saldo real da Binance
        const capitalInput = document.getElementById('liveInitialCapitalInput');
        if (capitalInput && live.balance && live.balance.totalWalletBalance) {
            const realBalance = live.balance.totalWalletBalance;
            const currentValue = parseFloat(capitalInput.value) || 0;
            
            // Sempre atualiza se o valor atual for maior que o saldo real (segurança)
            // ou se for o valor padrão (1000)
            if (currentValue > realBalance || currentValue === 1000) {
                capitalInput.value = realBalance.toFixed(2);
                capitalInput.max = realBalance.toFixed(2); // Impede valor acima do saldo
            }
        }

        if (liveOpenBadge) liveOpenBadge.textContent = String(liveStats.open_count) + ' abertos';
        if (liveWrBadge) liveWrBadge.textContent = (live.api_status && live.api_status.ok) ? 'WR ?%' : 'WR —';

        if (liveMeta) {
          liveMeta.textContent =
            (live.api_status && live.api_status.ok)
              ? ('API OK • ' + new Date().toLocaleTimeString())
              : 'API OFF/erro';
        }

        // SPRINT 12: Atualiza dashboard de oportunidades (sinais bloqueados)
        updateRefusalStats();

        // SPRINT 12.20: Renderizar métricas do LiveTracker (ROI, tempo, funding, fees)
        if (data.live_tracker) {
          const lt = data.live_tracker;
          const ltStats = lt.stats || {};
          const ltCapital = lt.capital || {};

          // Atualiza badge de Win Rate LIVE
          if (liveWrBadge && ltStats.total_trades > 0) {
            liveWrBadge.textContent = `WR ${fmt(ltStats.win_rate, 1)}%`;
          }

          // Atualiza painel de estatísticas LIVE com cards idênticos ao PAPER (layout + campos),
          // mas alimentados com dados reais do LiveTracker.
          if (liveStatsPanel) {
            const liveBalance = (live && live.balance) ? live.balance : {};
            const liveInitialInputEl = document.getElementById('liveInitialCapitalInput');
            const liveRiskInputEl = document.getElementById('liveRiskPctInput');

            const currentCapital = (liveBalance.totalWalletBalance != null ? liveBalance.totalWalletBalance : (ltCapital.current || 0));

            // Capital inicial e risco/trade devem refletir o que o painel LIVE sincroniza (saldo Binance imediato)
            const initialCapital = liveInitialInputEl ? (parseFloat(liveInitialInputEl.value) || 0) : (ltCapital.initial || 0);

            const liveRiskPctPerTrade = liveRiskInputEl ? ((parseFloat(liveRiskInputEl.value) || 0) / 100) : 0;
            const riskPct = liveRiskPctPerTrade * 100;
            const riskPerTrade = currentCapital * liveRiskPctPerTrade;

            const totalReturnPct = initialCapital > 0 ? ((currentCapital - initialCapital) / initialCapital * 100) : 0;

            // Wins/Losses/WIN rate vêm do LiveTracker (stats de trades fechados)
            const winRatePct = ltStats.win_rate_pct || 0;
            const wins = ltStats.wins || 0;
            const losses = ltStats.losses || 0;
            const totalTrades = ltStats.total_trades || 0;

            liveStatsPanel.innerHTML = `
              <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
                <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Capital Atual</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: ${currentCapital >= initialCapital ? '#3fb950' : '#f85149'};">
                  $${fmt(currentCapital, 2)}
                </div>
              </div>

              <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
                <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Retorno Total</div>
                <div style="font-size: 1.8rem; font-weight: bold; color: ${totalReturnPct >= 0 ? '#3fb950' : '#f85149'};">
                  ${totalReturnPct >= 0 ? '+' : ''}${fmt(totalReturnPct, 2)}%
                </div>
              </div>

              <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
                <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Risco/Trade</div>
                <div style="font-size: 1.4rem; font-weight: bold; color: #d29922;">
                  ${fmt(riskPct, 0)}% ($${fmt(riskPerTrade, 2)})
                </div>
              </div>

              <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
                <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Total Trades</div>
                <div style="font-size: 1.4rem; font-weight: bold; color: #e6edf3;">
                  ${totalTrades}
                </div>
              </div>

              <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
                <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Win Rate</div>
                <div style="font-size: 1.4rem; font-weight: bold; color: ${winRatePct >= 50 ? '#3fb950' : '#f85149'};">
                  ${fmt(winRatePct, 1)}%
                </div>
              </div>

              <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px;">
                <div style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">Wins / Losses</div>
                <div style="font-size: 1.4rem; font-weight: bold;">
                  <span style="color: #3fb950;">${wins}</span>
                  <span style="color: #8b949e;"> / </span>
                  <span style="color: #f85149;">${losses}</span>
                </div>
              </div>
            `;
          }

          // Atualiza tabela de trades LIVE com métricas completas (funding, fees, ROI)
          if (lt.closed && lt.closed.length > 0) {
            const tbodyClosed = document.getElementById('live-closed-rows');
            if (tbodyClosed) {
              tbodyClosed.innerHTML = lt.closed.slice(0, 10).map(function(t) {
                const exit = t.exit || {};
                const entry = t.entry || {};
                const roiClass = exit.roi_pct > 0 ? 'pos' : (exit.roi_pct < 0 ? 'neg' : '');
                const pnlClass = exit.pnl_pct > 0 ? 'pos' : (exit.pnl_pct < 0 ? 'neg' : '');

                return '<tr>' +
                  '<td>' + t.symbol + '</td>' +
                  '<td>' + fmt(entry.price, 4) + '</td>' +
                  '<td>' + fmt(exit.price, 4) + '</td>' +
                  '<td>' + fmt(exit.duration_sec / 60, 1) + 'm</td>' +
                  '<td class="' + pnlClass + '">' + fmt(exit.pnl_pct, 2) + '%</td>' +
                  '<td>' + fmt(exit.pnl_usdt, 2) + '</td>' +
                  '<td class="' + roiClass + '">' + fmt(exit.roi_pct, 2) + '%</td>' +
                  '<td>' + fmt(exit.fee_usdt, 4) + '</td>' +
                  '<td>' + fmt(exit.funding_fee_usdt, 4) + '</td>' +
                  '<td>' + fmt(exit.total_fees_usdt, 4) + '</td>' +
                  '<td>' + (exit.reason || '—') + '</td>' +
                  '</tr>';
              }).join('');
            }
          }

          // Atualiza posições abertas LIVE com funding fees acumulados
          if (lt.open && Object.keys(lt.open).length > 0) {
            const openTrades = Object.values(lt.open);
            const tbodyOpen = document.getElementById('live-open-rows');
            if (tbodyOpen) {
              tbodyOpen.innerHTML = openTrades.map(function(t) {
                const entry = t.entry || {};
                const live = t.live || {};

                return '<tr>' +
                  '<td>' + t.symbol + '</td>' +
                  '<td>' + fmt(entry.price, 4) + '</td>' +
                  '<td>' + fmt(live.last_price, 4) + '</td>' +
                  '<td>' + fmt(live.duration_sec / 60, 1) + 'm</td>' +
                  '<td>' + fmt(live.pnl_pct, 2) + '%</td>' +
                  '<td>' + fmt(live.pnl_usdt, 2) + '</td>' +
                  '<td>' + fmt(live.funding_fee_usdt, 4) + '</td>' +
                  '<td>' + fmt(entry.quantity, 4) + '</td>' +
                  '<td>' + fmt(entry.notional_usdt, 2) + '</td>' +
                  '<td>' + fmt(entry.usdt_margin, 2) + '</td>' +
                  '</tr>';
              }).join('');
            }
          }
        }

        if (!livePositions.length) {
          tbodyLive.innerHTML = '<tr><td colspan="17" class="meta">Nenhuma posição LIVE</td></tr>';
        } else {
          const safe = (v) => (v == null ? '—' : v);
          tbodyLive.innerHTML = livePositions.slice(0, 8).map(function(p) {
            // shape tolerante: o backend pode mandar poucos campos e a UI ainda renderiza
            const sym = p.symbol || p.pair || p.side || '—';
            const entryPrice = p.entry_price ?? p.entry?.price ?? p.entryPrice ?? null;
            const currentPrice = p.current_price ?? p.current?.price ?? p.last_price ?? null;
            const qty = p.size ?? p.quantity ?? p.qty ?? null;
            const notional = p.notional ?? p.notional_usdt ?? null;
            const margin = p.margin ?? p.usdt_margin ?? null;
            const lev = p.leverage ?? null;
            const risk = p.risk_pct ?? p.risk ?? null;
            const pnlPct = p.pnl_pct ?? p.pnlPct ?? null;
            const pnlUsd = p.pnl_usdt ?? p.pnl_usdt ?? null;
            const mfe = p.mfe_pct ?? null;
            const mae = p.mae_pct ?? null;
            const sl = p.sl_price ?? p.sl ?? null;
            const tp = p.tp_price ?? p.tp ?? null;
            const dur = p.duration_sec ?? null;
            const quality = p.quality ?? p.entry_quality ?? '—';

            // SPRINT 11.34: Renderização de Slippage (Ficção baseada no entry vs signal se disponível)
            // Como o monitor lê da Binance, o 'signal_price' pode não estar no objeto p. 
            // Se não estiver, mostramos '—'.
            const sigPrice = p.expected_price ?? null;
            const slippage = (sigPrice && entryPrice) ? ((entryPrice / sigPrice - 1) * 100).toFixed(3) + '%' : '—';
            const slipClass = parseFloat(slippage) > 0.1 ? 'neg' : 'pos';

            return '<tr>' +
              '<td>' + sym + '</td>' +
              '<td>' + safe(entryPrice) + '</td>' +
              '<td class="' + slipClass + '">' + slippage + '</td>' +
              '<td>' + safe(currentPrice) + '</td>' +
              '<td>' + safe(qty) + '</td>' +
              '<td>' + safe(notional) + '</td>' +
              '<td>' + safe(margin) + '</td>' +
              '<td>' + safe(lev) + '</td>' +
              '<td>$' + fmt(p.fee_entry, 3) + '</td>' +
              '<td>$' + fmt(p.fee_exit, 3) + '</td>' +
              '<td>' + safe(risk) + '</td>' +
              '<td>' + safe(pnlPct) + '</td>' +
              '<td>' + safe(pnlUsd) + '</td>' +
              '<td>' + safe(mfe) + '</td>' +
              '<td>' + safe(mae) + '</td>' +
              '<td>' + safe(sl) + '</td>' +
              '<td>' + safe(tp) + '</td>' +
              '<td>' + safe(dur) + '</td>' +
              '<td>' + safe(quality) + '</td>' +
              '<td>' + '<button class="btn-danger" style="padding:2px 6px; font-size:9px" data-sym="' + sym + '" data-mode="live" onclick="closeTrade(this.dataset.sym, this.dataset.mode)">Fechar</button>' + '</td>' +
              '</tr>';
          }).join('');
        }
      }
      if (!paperRows.length) {
        // --- PAINEL DE STATUS DO SISTEMA (quando não há trades abertos) ---
        var rs = refusalStatsCache;
        var totalAnalyzed = rs.total_signals || 0;
        var totalBlocked = rs.count || 0;
        var blockRate = totalAnalyzed > 0 ? (totalBlocked / totalAnalyzed * 100).toFixed(1) : '—';
        var topReasons = rs.reasons ? Object.entries(rs.reasons).sort((a,b)=>b[1]-a[1]).slice(0,3) : [];
        var ghosts = (data.ghosts || []).slice(0,4);
        var recentSignals = (data.signals || []).slice(0,3);
        var statusColor = totalAnalyzed > 0 ? '#3fb950' : '#8b949e';
        var statusText = totalAnalyzed > 0 ? '🟢 Analisando sinais' : '🟡 Aquecendo...';

        var topCandidatesHtml = ghosts.length
          ? ghosts.map(function(g){
              return '<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:10px;background:#1f2d3a;border:1px solid #264f78;font-size:11px;font-weight:700;">'
                + g.symbol.replace('USDT','') + ' <span style="color:#58a6ff;">'+Math.round(g.score||0)+'</span>'
                + '<span style="color:#f85149;font-size:9px;">'+((g.reason||'').split('_').slice(0,2).join(' '))+'</span>'
                + '</span>';
            }).join(' ')
          : '<span style="color:#8b949e;font-size:11px;">aguardando dados...</span>';

        var topReasonsHtml = topReasons.length
          ? topReasons.map(function(r){
              return '<div style="display:flex;justify-content:space-between;font-size:10px;padding:1px 0;">'
                + '<span style="color:#8b949e;">'+r[0].replace(/_/g,' ')+'</span>'
                + '<span style="color:#f85149;font-weight:700;">'+r[1]+'</span>'
                + '</div>';
            }).join('')
          : '<div style="font-size:10px;color:#8b949e;">aguardando...</div>';

        var recentSignalsHtml = recentSignals.length
          ? recentSignals.map(function(s){
              return '<span style="font-size:10px;color:#3fb950;font-weight:700;">🔥 '
                + s.symbol.replace('USDT','') + ' ('+Math.round(s.score||0)+')</span>';
            }).join(' &nbsp;')
          : '<span style="font-size:10px;color:#8b949e;">nenhum sinal aprovado ainda</span>';

        tbodyPaper.innerHTML = '<tr><td colspan="18" style="padding:0;">'
          + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;background:#21262d;">'

          // Coluna 1 — Status do sistema
          + '<div style="padding:16px;background:#0d1117;">'
          + '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#8b949e;font-weight:700;margin-bottom:8px;">Status do Sistema</div>'
          + '<div style="font-size:13px;font-weight:700;color:'+statusColor+';margin-bottom:8px;">'+statusText+'</div>'
          + '<div style="font-size:11px;color:#8b949e;margin-bottom:4px;">Analisados (1h): <b style="color:#e6edf3;">'+totalAnalyzed+'</b></div>'
          + '<div style="font-size:11px;color:#8b949e;margin-bottom:4px;">Bloqueados: <b style="color:#f85149;">'+totalBlocked+' ('+blockRate+'%)</b></div>'
          + '<div style="font-size:11px;color:#8b949e;">Aprovados: <b style="color:#3fb950;">'+(totalAnalyzed-totalBlocked)+'</b></div>'
          + '<div style="margin-top:8px;">'+recentSignalsHtml+'</div>'
          + '</div>'

          // Coluna 2 — Top motivos de bloqueio
          + '<div style="padding:16px;background:#0d1117;">'
          + '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#8b949e;font-weight:700;margin-bottom:8px;">Top Motivos de Bloqueio</div>'
          + topReasonsHtml
          + '</div>'

          // Coluna 3 — Top candidatos (ghosts)
          + '<div style="padding:16px;background:#0d1117;">'
          + '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#8b949e;font-weight:700;margin-bottom:8px;">Top Candidatos</div>'
          + '<div style="display:flex;flex-wrap:wrap;gap:4px;">'+topCandidatesHtml+'</div>'
          + '</div>'

          + '</div>'
          + '</td></tr>';
      } else {
        tbodyPaper.innerHTML = paperRows.map(function(t) {
          var live = t.live || {}, ex = t.exit || {}, q = t.quality || {};
          var entry = t.entry || {};
          var sig = entry.signal || {};
          var pnl = t.status === 'open' ? live.pnl_pct : ex.pnl_pct;
          var cls = (pnl||0) >= 0 ? 'pos' : 'neg';
          var cur = t.status === 'open' ? live.last_price : ex.price;
          var qual = t.status === 'open'
            ? (q.favorable_early
                ? '<span style="color:#ff6b00; font-size:10px; font-weight:900;">⚡early</span>'
                : 'on')
            : (q.entry_assertiveness || ex.reason || '');
          var pnl_usdt = t.status === 'open' ? live.pnl_usdt : ex.pnl_usdt;
          var sl_price = (t.targets && t.targets.sl_price) != null ? t.targets.sl_price : '';
          var tp_price = (t.targets && t.targets.tp_price) != null ? t.targets.tp_price : '';
          var tempo_sec = live.duration_sec != null ? live.duration_sec : '—';
          var risk_val = sig.kelly_risk_applied ? (sig.kelly_risk_applied * 100).toFixed(1) + '%' : '—';
          var fee_in = entry.fee_usdt || 0;
          var fee_out = ex.fee_usdt || 0;
          var margin_val = entry.initial_usdt_margin ?? ((entry.initial_quantity != null && entry.price != null) ? ((entry.initial_quantity * entry.price) / (entry.leverage || 10)) : entry.usdt_margin);
          var sltp_str = (sl_price!=='' ? fmt(sl_price,4) : '—') + ' / ' + (tp_price!=='' ? fmt(tp_price,4) : '—');

          // Nova ordem: Símbolo | PnL% | PnL$ | MFE | [sec] MAE | Margem | [sec] Entrada | Atual | Size | Notional | Alav | Fee In | Fee Out | Risk% | SL/TP | Tempo | Qual | Ação
          return '<tr>'
            + '<td><b>'+t.symbol.replace('USDT','')+'</b></td>'
            + '<td class="'+cls+'" style="font-weight:700;">'+fmt(pnl)+'%</td>'
            + '<td>'+fmt(pnl_usdt,2)+'</td>'
            + '<td style="color:#3fb950;">'+fmt(live.mfe_pct)+'%</td>'
            + '<td class="col-sec-paper">'+fmt(live.mae_pct)+'%</td>'
            + '<td style="color:var(--yellow);font-weight:600;">$'+fmt(margin_val,2)+'</td>'
            + '<td class="col-sec-paper">'+fmt(entry.price,4)+'</td>'
            + '<td class="col-sec-paper">'+fmt(cur,4)+'</td>'
            + '<td class="col-sec-paper">'+fmt(entry.current_quantity,4)+'</td>'
            + '<td class="col-sec-paper">$'+fmt((entry.initial_notional_usdt ?? (entry.notional_usdt)),1)+'</td>'
            + '<td class="col-sec-paper">'+(entry.leverage||10)+'x</td>'
            + '<td class="col-sec-paper">$'+fmt(fee_in,3)+'</td>'
            + '<td class="col-sec-paper">'+(t.status==='open'?'—':'$'+fmt(fee_out,3))+'</td>'
            + '<td class="col-sec-paper" style="color:var(--yellow);">'+risk_val+'</td>'
            + '<td style="font-size:10px;">'+sltp_str+'</td>'
            + '<td>'+(tempo_sec!=='—' ? fmt(tempo_sec,0)+'s' : '—')+'</td>'
            + '<td>'+qual+'</td>'
            + '<td>'+(t.status==='open' ? '<button class="btn-danger" style="padding:2px 6px;font-size:9px" data-sym="'+t.symbol+'" data-mode="paper" onclick="closeTrade(this.dataset.sym,this.dataset.mode)">Fechar</button>' : '—')+'</td>'
            + '</tr>';
        }).join('');
      }

      // Render Post-Trade Analysis (Sprint 6.42)
      const postTradeBody = document.getElementById('post-trade-rows');
      const recentlyClosed = (paper.closed_recent || []).slice(0, 10);
      
      if (!recentlyClosed.length) {
        postTradeBody.innerHTML = '<tr><td colspan="12" class="meta">Nenhum fechamento recente monitorado.</td></tr>';
      } else {
        postTradeBody.innerHTML = recentlyClosed.map(function(t) {
          const pt = t.post_trade || {};
          const exit = t.exit || {};
          const drift = pt.current_drift || 0;
          const driftCls = drift > 0 ? 'pos' : (drift < 0 ? 'neg' : '');
          
          const fmtCell = (val) => {
            if (val == null) return '<span class="cell-dim">...</span>';
            const cls = val > 0 ? 'pos' : 'neg';
            return `<span class="${cls}" style="font-weight:600;">${val > 0 ? '+' : ''}${val.toFixed(2)}%</span>`;
          };

          const impact = drift > 2 ? '❌ Saiu Cedo' : (drift < -2 ? '✅ Saída Perfeita' : '⚖️ Neutro');

          return `<tr>
            <td><b>${t.symbol.replace('USDT','')}</b></td>
            <td style="font-size:0.7rem; text-transform:uppercase; color:var(--muted);">${exit.reason || '—'}</td>
            <td>${fmt(exit.price, 4)}</td>
            <td class="${driftCls}" style="font-weight:bold; font-size:1rem;">${drift > 0 ? '+' : ''}${drift.toFixed(2)}%</td>
            <td>${fmtCell(pt['5m'])}</td><td>${fmtCell(pt['15m'])}</td>
            <td>${fmtCell(pt['30m'])}</td><td>${fmtCell(pt['60m'])}</td><td>${fmtCell(pt['4h'])}</td><td>${fmtCell(pt['12h'])}</td><td>${fmtCell(pt['24h'])}</td>
            <td style="font-weight:bold; color:var(--yellow);">${impact}</td>
          </tr>`;
        }).join('');
      }

      if (paper.capital_history) {
        updateEquityChart(paper.capital_history);
        updateRiskChart(paper.capital_history);
        updateDrawdownChart(paper.capital_history);
      }
      if (data.liq_history) {
        updateLiquidationChart(data.liq_history);
      }
      if (paper.stats) {
        updateWinRateChart(paper.stats);
      }

      // --- Panela de Sinais Recentes ---
      const sigEl = document.getElementById('signals');
      if (!data.signals || !data.signals.length) {
        sigEl.innerHTML = '<div class="sig meta">Nenhum sinal ainda</div>';
      } else {
        sigEl.innerHTML = data.signals.map(s => {
          const scoreColor = (s.score||0) >= 95 ? '#3fb950' : (s.score||0) >= 90 ? '#d29922' : '#8b949e';
          const relax = s.relax_label && s.relax_label !== 'NORMAL'
            ? `<span style="font-size:9px;color:#58a6ff;margin-left:4px;">${s.relax_label}</span>` : '';
          return `<div class="sig">
          <b>${s.symbol.replace('USDT','')}</b>
          <span style="font-size:11px;font-weight:900;color:${scoreColor};margin-left:6px;">${Math.round(s.score||0)}</span>${relax}
          <span style="color:#8b949e;font-size:10px;margin-left:4px;">@ ${fmt(s.price,4)}</span>
          <br/>exp ${s.exp!=null?(s.exp>=0?'+':'')+fmt(s.exp,4):'—'} | oi ${s.oi_trend!=null?(s.oi_trend>=0?'+':'')+fmt(s.oi_trend,2):'—'} | lsr ${s.lsr_trend!=null?(s.lsr_trend>=0?'+':'')+fmt(s.lsr_trend,2):'—'} | CVD ${fmtCVD(s.cvd_1m)}
          <span class="meta">${new Date(s.logged_at*1000).toLocaleTimeString()}</span>
        </div>`;
        }).join('');
      }

      const ghostEl = document.getElementById('ghosts');
      if (data.ghosts && data.ghosts.length) {
        // Filtra e ordena: prioriza score alto, exclui score_below_sieve com score < 70
        const meaningfulGhosts = data.ghosts
          .filter(g => (g.score||0) >= 70 || (g.reason && g.reason !== 'score_below_sieve'))
          .sort((a,b) => (b.score||0) - (a.score||0))
          .slice(0, 8);

        if (!meaningfulGhosts.length) {
          ghostEl.innerHTML = '<div class="sig meta">Nenhum candidato de alta qualidade ainda</div>';
        } else {
          ghostEl.innerHTML = meaningfulGhosts.map(g => {
            const sc = g.score || 0;
            const scoreColor = sc >= 90 ? '#d29922' : sc >= 80 ? '#58a6ff' : '#8b949e';
            const reasonLabel = (g.reason || '—').replace(/_/g, ' ');
            return `<div class="sig ghost-sig">
              <b style="color:var(--yellow)">${g.symbol.replace('USDT','')}</b>
              <span style="font-size:11px;font-weight:900;color:${scoreColor};margin-left:6px;">${Math.round(sc)}</span>
              <span class="meta" style="float:right">${new Date(g.logged_at*1000).toLocaleTimeString()}</span>
              <br/><span style="color:#f85149;font-size:10px;">⛔ ${reasonLabel}</span>
            </div>`;
          }).join('');
        }
      } else {
        ghostEl.innerHTML = '<div class="sig meta">Nenhum fantasma detectado</div>';
      }
    }

    const paperBtn = document.getElementById('paperBtn');
    const paperDelayMin = document.getElementById('paperDelayMin');
    const modeToggle = document.getElementById('modeToggle');
    const initialCapitalInput = document.getElementById('initialCapitalInput');
    const riskPctInput = document.getElementById('riskPctInput');
    const leverageInput = document.getElementById('leverageInput');
    const liveLeverageInput = document.getElementById('liveLeverageInput'); // SPRINT 11.28
    const maxPosInput = document.getElementById('maxPosInput');
    const updateCapitalBtn = document.getElementById('updateCapitalBtn');
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    // Toggle do painel de configurações avançadas do Live
    function toggleLiveConfig() {
      var panel = document.getElementById('live-config-panel');
      var btn   = document.getElementById('live-config-toggle');
      if (!panel) return;
      var visible = panel.style.display !== 'none';
      if (visible) {
        panel.style.display = 'none';
        btn.textContent = '⚙ Configurações avançadas';
        btn.style.color = '#8b949e';
      } else {
        panel.style.display = 'grid';
        btn.textContent = '⚙ Fechar configurações';
        btn.style.color = '#f85149';
        btn.style.borderColor = '#f85149';
      }
    }

    // Toggle de colunas secundárias na tabela Paper
    var _paperColsExpanded = false;
    function togglePaperCols() {
      _paperColsExpanded = !_paperColsExpanded;
      var wrap = document.getElementById('paper-table-wrap');
      var btn  = document.getElementById('paper-col-toggle');
      if (_paperColsExpanded) {
        wrap.classList.add('expanded');
        btn.textContent = '⊖ Compactar colunas';
        btn.style.color = '#58a6ff';
        btn.style.borderColor = '#58a6ff';
      } else {
        wrap.classList.remove('expanded');
        btn.textContent = '⊕ Expandir colunas';
        btn.style.color = '#8b949e';
        btn.style.borderColor = '#30363d';
      }
    }

    // SPRINT 12: Dashboard de oportunidades - atualiza estatísticas de recusas
    let refusalStatsCache = { count: 0, reasons: {}, lastUpdate: 0 };
    
    async function updateRefusalStats() {
      const now = Date.now();
      // Atualiza a cada 30 segundos para não sobrecarregar
      if (now - refusalStatsCache.lastUpdate < 30000) {
        renderRefusalStats();
        return;
      }
      
      try {
        const res = await fetch('/api/refusal-stats');
        if (res.ok) {
          const data = await res.json();
          refusalStatsCache = {
            count: data.count || 0,
            reasons: data.reasons || {},
            total_signals: data.total_signals || 0,
            lastUpdate: now
          };
          renderRefusalStats();
        }
      } catch (e) {
        console.warn('Failed to fetch refusal stats:', e);
      }
    }
    
    function renderRefusalStats() {
      const countEl = document.getElementById('refusal-count');
      const rateEl = document.getElementById('refusal-rate');
      const topEl = document.getElementById('top-refusals');
      
      if (countEl) countEl.textContent = refusalStatsCache.count;
      
      if (rateEl && refusalStatsCache.total_signals > 0) {
        const rate = Math.min(100, (refusalStatsCache.count / refusalStatsCache.total_signals * 100)).toFixed(1);
        rateEl.textContent = `${rate}% dos sinais`;
      }
      
      if (topEl) {
        const reasons = Object.entries(refusalStatsCache.reasons)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5);
        
        if (reasons.length === 0) {
          topEl.textContent = '—';
        } else {
          topEl.innerHTML = reasons.map(([reason, count]) => 
            `<div style="display:flex; justify-content:space-between; margin-bottom:2px;">
              <span>${reason}</span>
              <span style="color:var(--muted)">${count}</span>
            </div>`
          ).join('');
        }
      }
    }

    if (modeToggle) {
      modeToggle.addEventListener('click', async () => {
        const currentMode = modeToggle.textContent.toLowerCase();
        const newMode = currentMode === 'paper' ? 'live' : 'paper';
        try {
          const res = await fetch('/api/set-mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: newMode })
          });
          const j = await res.json().catch(() => ({}));
          if (!res.ok || j.ok === false) {
            console.warn('toggle mode failed', j);
          }
        } catch (e) {
          console.warn('toggle mode error', e);
        }
      });
    }

    if (paperBtn) {
      paperBtn.addEventListener('click', async () => {
        if (!confirm("Deseja resetar os trades paper e iniciar uma nova coleta?")) return;
        
        const delayMin = paperDelayMin ? Number(paperDelayMin.value || 0) : 0;
        const delayMs = Math.max(0, delayMin) * 60 * 1000;

        try {
          // 1) reset puro
          const resetRes = await fetch('/api/reset-paper', { method: 'POST' });
          const resetJ = await resetRes.json().catch(() => ({}));
          if (!resetRes.ok || resetJ.ok === false) {
            console.warn('reset-paper failed', resetJ);
          }

          // 2) esperar período de população
          if (delayMs > 0) {
            await sleep(delayMs);
          }

          // 3) habilitar paper
          const setRes = await fetch('/api/set-mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'paper' })
          });
          const setJ = await setRes.json().catch(() => ({}));
          if (!setRes.ok || setJ.ok === false) {
            console.warn('set-mode failed', setJ);
          }
        } catch (e) {
          console.warn('reset+paper flow error', e);
        }
      });
    }

    const hardResetBtn = document.getElementById('hardResetBtn');
    if (hardResetBtn) {
      hardResetBtn.addEventListener('click', async () => {
        const confirmed = confirm("🚨 ATENÇÃO: RESET COMPLETO 🚨\\n\\nIsso apagará:\\n- Histórico de 100+ Trades\\n- Curva de Equity e Estatísticas\\n- Cache de Métricas (Novo Warmup de 5 min)\\n\\n(Reset principal — seguro, repetível.)\\n\\nTEM CERTEZA? Essa ação não pode ser desfeita.");
        if (!confirmed) return;
        const deepClean = confirm("Deep clean opcional (rastro/debug): apagar também logs de rastro/debug? (Poucas vezes, se você quiser controle total)");
        
        try {
          const res = await fetch('/api/hard-reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deep_clean: deepClean })
          });
          const j = await res.json().catch(() => ({}));
          if (res.ok && j.ok) {
            alert("✅ Hard Reset concluído com sucesso! O sistema está em estado puro.");
            location.reload(); 
          } else {
            alert("❌ Falha no Reset: " + (j.error || "Erro desconhecido"));
          }
        } catch (e) {
          console.error("Hard reset error", e);
        }
      });
    }

    if (updateCapitalBtn) {
      updateCapitalBtn.addEventListener('click', async () => {
        try {
          // Consolidado: usa endpoint único /api/set-live-settings
          const initialCapital = initialCapitalInput ? parseFloat(initialCapitalInput.value) : 12;
          const riskPct = riskPctInput ? parseFloat(riskPctInput.value) : 5;
          const leverage = leverageInput ? parseInt(leverageInput.value) : 8;
          const maxPos = 3; // Valor padrão, pode ser ajustado se houver input

          const res = await fetch('/api/set-live-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              usdt_amount: initialCapital,
              risk_pct: riskPct,
              leverage: leverage,
              max_pos: maxPos
            })
          });

          const j = await res.json().catch(() => ({}));
          if (!res.ok || j.ok === false) {
            console.warn('set-live-settings failed', j);
          } else {
            console.log('✅ Configurações LIVE atualizadas:', { initialCapital, riskPct, leverage, maxPos });
          }
        } catch (e) {
          console.warn('update capital/risk error', e);
        }
      });
    }



    const log = (...args) => console.log('[Dashboard]', ...args);
    let ws;

    // WS resilience (Roadmap 12.5/12.6): WS canal principal + polling fallback
    let wsRetries = 0;
    const WS_RETRY_MAX = 20;
    const WS_RETRY_BASE_MS = 1500;
    const WS_RETRY_MULT = 1.5;

    let pollingActive = false;
    let pollTimer = null;

    function stopPolling() {
      pollingActive = false;
      if (pollTimer) {
        try { clearTimeout(pollTimer); } catch (e) {}
        pollTimer = null;
      }
    }

    async function pollSnapshotOnce() {
      try {
        // Roadmap 12.5: se o WS voltou, desliga polling imediatamente (evita redundância)
        try {
          if (ws && ws.readyState === WebSocket.OPEN) {
            wsRetries = 0;
            stopPolling();
            return;
          }
        } catch (e) {
          // ignore
        }

        const res = await fetch('/api/snapshot', { cache: 'no-store' });
        if (!res.ok) throw new Error('snapshot http ' + res.status);
        const snap = await res.json();
        scheduleRender(snap);
      } catch (e) {
        // silencioso: polling leve durante falhas
      }
    }

    function startPolling() {
      if (pollingActive) return;
      pollingActive = true;

      const tick = async () => {
        if (!pollingActive) return;
        await pollSnapshotOnce();
        pollTimer = setTimeout(tick, 2500);
      };

      tick();
    }

    function scheduleReconnect(reason) {
      // Mantém visão do boot via polling
      startPolling();

      wsRetries = wsRetries + 1;
      const delay = Math.min(WS_RETRY_BASE_MS * Math.pow(WS_RETRY_MULT, wsRetries), 30000);

      // Estado visual
      const btn = document.getElementById('wsReconnect');
      if (btn) btn.style.display = 'inline-block';

      if (wsRetries > WS_RETRY_MAX) {
        if (btn) btn.textContent = 'Erro WS persistente — recarregar página';
        return;
      }

      setTimeout(() => {
        try { connect(); } catch (e) { /* ignore */ }
      }, delay);
    }


    document.getElementById('sortSelect').addEventListener('change', (e) => {
      currentSortField = e.target.value;
    });

    document.getElementById('volFilterCheck').addEventListener('change', (e) => {
      hideLowVol = e.target.checked;
    });
    document.getElementById('volThresholdInput').addEventListener('change', (e) => {
      volThreshold = parseFloat(e.target.value) || 0;
    });

    document.addEventListener('visibilitychange', () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'visibility', state: document.visibilityState }));
      }
    });

    const exitBtn = document.getElementById('exitBtn');
    if (exitBtn) {
      exitBtn.addEventListener('click', async () => {
        const confirmed = confirm("🛑 ENCERRAR BOT 🛑\\n\\nIsso vai parar o engine e encerrar o programa de forma graciosa (equivalente ao CTRL+C). \\n\\nTem certeza?");
        if (!confirmed) return;

        try {
          document.getElementById('meta').textContent = 'Encerrando...';
          const res = await fetch('/api/exit', { method: 'POST' });
          const j = await res.json().catch(() => ({}));
          if (!res.ok || j.ok === false) {
            console.warn('exit failed', j);
          }
        } catch (e) {
          console.error('exit failed', e);
        }
      });
    }

    // SPRINT 12.18: Event Listener para Compound
    const liveCompoundBtn = document.getElementById('liveCompoundBtn');
    if (liveCompoundBtn) {
                liveCompoundBtn.addEventListener('click', async () => {
            const isEnabled = liveCompoundBtn.textContent.includes('OFF');
            try {
                const res = await fetch('/api/set-live-compound', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled: isEnabled })
                });
                const j = await res.json();
                if (!res.ok || !j.ok) {
                    console.error('Compound toggle failed', j);
                    return;
                }
                const on = Boolean(j.compound_enabled);
                liveCompoundBtn.textContent = `Compound: ${on ? 'ON' : 'OFF'}`;
                if (on) {
                    liveCompoundBtn.style.background = '#1f3d2a';
                    liveCompoundBtn.style.border = '1px solid var(--green)';
                    liveCompoundBtn.style.color = 'var(--green)';
                } else {
                    liveCompoundBtn.style.background = '#3d1f1f';
                    liveCompoundBtn.style.border = '1px solid var(--red)';
                    liveCompoundBtn.style.color = 'var(--red)';
                }
            } catch (e) { console.error('Compound toggle error', e); }
        });
    }

    // SPRINT 12.18: Event Listener para configurações LIVE (risco, alavancagem, max positions)
    const updateLiveBtn = document.getElementById('updateLiveBtn');
    if (updateLiveBtn) {
        updateLiveBtn.addEventListener('click', async () => {
            const usdtAmount = parseFloat(document.getElementById('liveInitialCapitalInput').value) || 12;
            const riskPct = parseFloat(document.getElementById('liveRiskPctInput').value) || 5;
            const leverage = parseInt(document.getElementById('liveLeverageInput').value) || 8;
            const maxPos = parseInt(document.getElementById('liveMaxPosInput').value) || 3;
            try {
                const res = await fetch('/api/set-live-settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        usdt_amount: usdtAmount,
                        risk_pct: riskPct,
                        leverage: leverage,
                        max_pos: maxPos
                    })
                });
                const j = await res.json();
                if (!res.ok || !j.ok) {
                    console.error('Live settings update failed', j);
                    alert('Erro ao atualizar configurações LIVE: ' + (j.error || 'Desconhecido'));
                    return;
                }
                alert('Configurações LIVE atualizadas com sucesso!');
            } catch (e) {
                console.error('Live settings update error', e);
                alert('Erro ao atualizar configurações LIVE: ' + e.message);
            }
        });
    }

    // SPRINT 12.21: Event Listener para configurações avançadas LIVE
    const updateLiveAdvancedBtn = document.getElementById('updateLiveAdvancedBtn');
    // AUTO-PILOT: Toggle para desabilitar/habilitar campos SL/TP
    const autoPilotCheck = document.getElementById('liveAutoPilotCheck');
    const autoPilotHint = document.getElementById('autoPilotHint');
    const slInput = document.getElementById('liveSlPctInput');
    const tpInput = document.getElementById('liveTpPctInput');
    
    if (autoPilotCheck) {
        autoPilotCheck.addEventListener('change', () => {
            const isAutoPilot = autoPilotCheck.checked;
            if (slInput) slInput.disabled = isAutoPilot;
            if (tpInput) tpInput.disabled = isAutoPilot;
            if (autoPilotHint) autoPilotHint.style.display = isAutoPilot ? 'inline' : 'none';
            
            if (isAutoPilot) {
                if (slInput) slInput.style.opacity = '0.5';
                if (tpInput) tpInput.style.opacity = '0.5';
            } else {
                if (slInput) slInput.style.opacity = '1';
                if (tpInput) tpInput.style.opacity = '1';
            }
        });
    }

    if (updateLiveAdvancedBtn) {
        updateLiveAdvancedBtn.addEventListener('click', async () => {
            const autoPilotEnabled = document.getElementById('liveAutoPilotCheck').checked || false;
            const slPct = parseFloat(document.getElementById('liveSlPctInput').value) || 1.5;
            const tpPct = parseFloat(document.getElementById('liveTpPctInput').value) || 5;
            const maxHoldMin = parseInt(document.getElementById('liveMaxHoldInput').value) || 0;
            const signalMode = document.getElementById('liveSignalModeInput').value || 'conservative';
            const trailingEnabled = document.getElementById('liveTrailingCheck').checked || false;
            const kellyEnabled = document.getElementById('liveKellyCheck').checked || false;
            try {
                const res = await fetch('/api/set-live-advanced', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        auto_pilot: autoPilotEnabled,
                        sl_pct: slPct,
                        tp_pct: tpPct,
                        max_hold_min: maxHoldMin,
                        signal_mode: signalMode,
                        trailing_enabled: trailingEnabled,
                        kelly_enabled: kellyEnabled
                    })
                });
                const j = await res.json();
                if (!res.ok || !j.ok) {
                    console.error('Update live advanced failed', j);
                    alert('Erro ao atualizar configurações avançadas: ' + (j.error || 'Unknown error'));
                    return;
                }
                const msg = autoPilotEnabled
                    ? 'AUTO-PILOT ativado! Motor gerenciará SL/TP dinamicamente baseado em ATR (R:R 3:1).'
                    : 'Configurações avançadas LIVE atualizadas com sucesso!';
                alert(msg);
            } catch (e) { console.error('Update live advanced error', e); alert('Erro ao atualizar configurações avançadas'); }
        });
    }

    // SPRINT 12.21: Carregar configurações avançadas LIVE ao inicializar
    async function loadLiveAdvancedConfig() {
        try {
            const res = await fetch('/api/live-advanced-config');
            const j = await res.json();
            if (j.ok) {
                const slInput = document.getElementById('liveSlPctInput');
                const tpInput = document.getElementById('liveTpPctInput');
                const maxHoldInput = document.getElementById('liveMaxHoldInput');
                const signalModeInput = document.getElementById('liveSignalModeInput');
                const trailingCheck = document.getElementById('liveTrailingCheck');
                const kellyCheck = document.getElementById('liveKellyCheck');
                const autoPilotCheck = document.getElementById('liveAutoPilotCheck');
                const autoPilotHint = document.getElementById('autoPilotHint');

                if (slInput) slInput.value = j.sl_pct.toFixed(1);
                if (tpInput) tpInput.value = j.tp_pct.toFixed(1);
                if (maxHoldInput) maxHoldInput.value = j.max_hold_min;
                if (signalModeInput) signalModeInput.value = j.signal_mode;
                if (trailingCheck) trailingCheck.checked = j.trailing_enabled;
                if (kellyCheck) kellyCheck.checked = j.kelly_enabled || false;

                // AUTO-PILOT
                const isAutoPilot = j.auto_pilot || false;
                if (autoPilotCheck) autoPilotCheck.checked = isAutoPilot;
                if (isAutoPilot) {
                    if (slInput) { slInput.disabled = true; slInput.style.opacity = '0.5'; }
                    if (tpInput) { tpInput.disabled = true; tpInput.style.opacity = '0.5'; }
                    if (autoPilotHint) autoPilotHint.style.display = 'inline';
                }

                // F-01: persistência do cockpit Live — campos que não eram carregados no boot
                const capitalInput = document.getElementById('liveInitialCapitalInput');
                const riskInput = document.getElementById('liveRiskPctInput');
                const leverageInput = document.getElementById('liveLeverageInput');
                const maxPosInput = document.getElementById('liveMaxPosInput');
                const compoundBtn = document.getElementById('liveCompoundBtn');

                if (capitalInput && j.usdt_amount != null) capitalInput.value = j.usdt_amount.toFixed(2);
                if (riskInput && j.risk_pct != null) riskInput.value = j.risk_pct.toFixed(1);
                if (leverageInput && j.leverage != null) leverageInput.value = j.leverage;
                if (maxPosInput && j.max_open_positions != null) maxPosInput.value = j.max_open_positions;

                // Compound: restaura estado visual do botão
                if (compoundBtn && j.compound_enabled != null) {
                    const on = j.compound_enabled;
                    compoundBtn.textContent = `Compound: ${on ? 'ON' : 'OFF'}`;
                    compoundBtn.style.background = on ? '#1f3d2a' : '#3d1f1f';
                    compoundBtn.style.border = `1px solid ${on ? 'var(--green)' : 'var(--red)'}`;
                    compoundBtn.style.color = on ? 'var(--green)' : 'var(--red)';
                }
            }
        } catch (e) { console.error('Erro ao carregar configurações avançadas LIVE:', e); }
    }
    loadLiveAdvancedConfig();

    // F-01: carrega configurações Paper salvas antes do primeiro WS update
    (async function loadPaperConfig() {
        try {
            const res = await fetch('/api/paper-config');
            const j = await res.json();
            if (j.ok) {
                const capEl = document.getElementById('initialCapitalInput');
                const rskEl = document.getElementById('riskPctInput');
                const levEl = document.getElementById('leverageInput');
                const mxpEl = document.getElementById('maxPosInput');
                if (capEl && document.activeElement !== capEl) capEl.value = j.initial_capital.toFixed(2);
                if (rskEl && document.activeElement !== rskEl) rskEl.value = j.risk_pct.toFixed(1);
                if (levEl && document.activeElement !== levEl) levEl.value = j.leverage;
                if (mxpEl && document.activeElement !== mxpEl) mxpEl.value = j.max_open_positions;
            }
        } catch (e) { console.error('Erro ao carregar configurações Paper:', e); }
    })();

    // Anti-flicker: debounce render calls to one per animation frame.
    // Prevents double-renders when WS and polling both fire simultaneously.
    let _rafId = null;
    let _pendingData = null;
    function scheduleRender(data) {
      _pendingData = data;
      if (_rafId) return;
      _rafId = requestAnimationFrame(() => {
        _rafId = null;
        const d = _pendingData;
        _pendingData = null;
        if (d) { try { render(d); } catch(e) { console.error('[render]', e); } }
      });
    }

    function connect() {
      const conn    = document.getElementById('conn');
      const label   = document.getElementById('connLabel');
      const proto   = location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl   = `${proto}://${location.host}/ws`;
      log('[WS] connecting to', wsUrl);

      try {
        ws = new WebSocket(wsUrl);
      } catch(e) {
        log('[WS] constructor error', e);
        scheduleReconnect('constructor_error');
        return;
      }

      ws.onopen = () => {
        log('[WS] open');
        wsRetries = 0;
        stopPolling();  // WS conectou — polling redundante desligado imediatamente
        conn.innerHTML = '<span class="dot ok"></span><span id="connLabel" style="margin-left:4px">live</span>';
        const btn = document.getElementById('wsReconnect');
        if (btn) btn.style.display = 'none';
      };
      ws.onerror = (e) => {
        log('[WS] error event', e);
        console.error('[WS] error', e);
      };
      ws.onclose = (e) => {
        log('[WS] close code='+e.code+' reason='+e.reason+' clean='+e.wasClean);
        conn.innerHTML = '<span class="dot bad"></span><span id="connLabel" style="margin-left:4px">offline</span>';
        const btn = document.getElementById('wsReconnect');
        if (btn) btn.style.display = 'inline-block';
        scheduleReconnect('ws_close');
      };
      ws.onmessage = (ev) => {
        let parsed;
        try {
          parsed = JSON.parse(ev.data);
        } catch (ex) {
          log('[WS] JSON parse error', ex);
          return;
        }
        scheduleRender(parsed);
      };
    }

    // Start polling immediately to avoid blank UI if WS is slow/failed on boot.
    // Polling stops automatically once WS becomes OPEN (see pollSnapshotOnce()).
    startPolling();
    connect();
  </script>
</body>
</html>"""


def create_app(
    state: BotState,
    signals: SqueezeIgnition, # SPRINT 12.20: Injeção de dependência para métricas rápidas
    on_set_mode: Optional[Callable[[str], Any]] = None,
    on_reset_paper: Optional[Callable[[], Any]] = None,
    on_hard_reset: Optional[Callable[..., Any]] = None,
    on_update_paper_settings: Optional[Callable[[float, float, int, int], Any]] = None,
    on_update_live_settings: Optional[Callable[[float, float, int, int], Any]] = None,
    on_update_live_advanced: Optional[Callable[[bool, float, float, int, str, bool, bool], Any]] = None,  # SPRINT 12.21: auto_pilot, sl_pct, tp_pct, max_hold_min, signal_mode, trailing_enabled, kelly_enabled
    on_exit: Optional[Callable[[], Any]] = None, # SPRINT EXIT
    on_toggle_live_compound: Optional[Callable[[bool], Any]] = None,
    on_close_trade: Optional[Callable[[str, str], Any]] = None,
    on_close_all_live: Optional[Callable[[], Any]] = None,
    live_tracker: Optional[Any] = None,  # SPRINT 12.20: LiveTracker para modo LIVE
    engine: Optional[Any] = None,
) -> FastAPI:
    app = FastAPI(title="SqueezeSniper V4", docs_url=None, redoc_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse(_DASHBOARD_HTML)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        # SPRINT 6.49: Resolve o erro 404 de favicon no log do terminal
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/logo.png")
    async def logo():
        """SPRINT 12: Serve o logo.png do Sniper."""
        from pathlib import Path
        logo_path = Path("assets/logo.png")
        if not logo_path.exists():
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return FileResponse(logo_path, media_type="image/png")

    @app.get("/api/snapshot")
    async def snapshot():
        """SPRINT 12.62: Snapshot completo para carga inicial (REST)."""
        snap = state.snapshot()
        if hasattr(state, "_live_closed_recent"):
            if "live" not in snap: snap["live"] = {}
            snap["live"]["closed_recent"] = getattr(state, "_live_closed_recent")
        
        # SPRINT 12.18/63: Injeta estado do compound e LiveTracker no snapshot REST
        snap["compound_enabled"] = getattr(state, "compound_enabled", False)
        
        if live_tracker:
            try:
                # Garante que os cards subam mesmo se o WS ainda não conectou
                snap["live_tracker"] = live_tracker.get_snapshot()
            except Exception as e:
                logger.warning("Erro no snapshot do LiveTracker (REST): %s", e)

        # SPRINT 12.64: Garante que o trading_mode seja respeitado fielmente
        snap["trading_mode"] = getattr(state, "trading_mode", "paper")
        return snap

    @app.post("/api/set-mode")
    async def set_mode(request: Request, payload: dict):
        ip = _http_guard(request)
        _http_rate_limit(f"set-mode:{ip}", limit=5, window_seconds=10.0)

        if on_set_mode is None:
            return {"ok": False, "error": "set-mode handler not configured"}
        mode = str((payload or {}).get("mode") or "").strip().lower()
        if mode not in ("paper", "live"):
            return {"ok": False, "error": "invalid mode"}
        return on_set_mode(mode)

    @app.post("/api/hard-reset")
    async def hard_reset(request: Request):
        ip = _http_guard(request)

        if on_hard_reset is None:
            return {"ok": False, "error": "hard-reset handler not configured"}

        try:
            payload = await request.json()
        except Exception:
            payload = {}
        deep_clean = bool(payload.get("deep_clean", False))

        return on_hard_reset(deep_clean=deep_clean)

    @app.post("/api/close-trade")
    async def close_trade(request: Request, payload: dict):
        ip = _http_guard(request)
        _http_rate_limit(f"close-trade:{ip}", limit=5, window_seconds=10.0)
        if on_close_trade is None:
            return {"ok": False, "error": "close-trade handler not configured"}
        symbol = str(payload.get("symbol", "")).strip().upper()
        mode = str(payload.get("mode", "")).strip().lower()
        return on_close_trade(symbol, mode)

    @app.post("/api/close-all-live")
    async def close_all_live(request: Request):
        ip = _http_guard(request)
        _http_rate_limit(f"close-all-live:{ip}", limit=1, window_seconds=30.0)
        if on_close_all_live is None:
            return {"ok": False, "error": "close-all-live handler not configured"}
        return on_close_all_live()

    @app.post("/api/reset-paper")
    async def reset_paper(request: Request):
        ip = _http_guard(request)
        _http_rate_limit(f"reset-paper:{ip}", limit=1, window_seconds=60.0)

        if on_reset_paper is None:
            return {"ok": False, "error": "reset-paper handler not configured"}
        return on_reset_paper()

    @app.post("/api/exit")
    async def exit_bot(request: Request):
        ip = _http_guard(request)
        _http_rate_limit(f"exit:{ip}", limit=1, window_seconds=60.0)

        if on_exit is None:
            # Fallback: simula Ctrl+C (gracioso) via SIGINT no processo principal
            try:
                lock_pid_path = Path("logs/instance_lock_main.pid")
                pid_txt = lock_pid_path.read_text(encoding="utf-8").strip() if lock_pid_path.exists() else ""
                pid = int(pid_txt) if pid_txt else None
                if pid is None:
                    return {"ok": False, "error": "exit handler not configured and main pid not found"}
                os.kill(pid, signal.SIGINT)
                return {"ok": True, "signal_sent": "SIGINT", "pid": pid}
            except Exception as e:
                return {"ok": False, "error": f"exit fallback failed: {e}"}
        return on_exit()

    @app.post("/api/set-paper-settings")
    async def set_paper_settings(request: Request, payload: dict):
        ip = _http_guard(request)
        _http_rate_limit(f"set-paper-settings:{ip}", limit=2, window_seconds=10.0)
        if on_update_paper_settings is None:
            return {"ok": False, "error": "set-paper-settings handler not configured"}
        try:
            return on_update_paper_settings(
                float(payload.get("initial_capital", 1000)),
                float(payload.get("risk_pct", 5.0)),
                int(payload.get("leverage", 10)),
                int(payload.get("max_pos", 5))
            )
        except Exception as e: return {"ok": False, "error": str(e)}

    @app.post("/api/set-live-settings")
    async def set_live_settings(request: Request, payload: dict): # SPRINT 11.28: New handler for live settings
        ip = _http_guard(request)
        _http_rate_limit(f"set-live-settings:{ip}", limit=2, window_seconds=10.0)
        if on_update_live_settings is None:
            return {"ok": False, "error": "set-live-settings handler not configured"}
        try:
            usdt_amount = float(payload.get("usdt_amount", 0))
            risk_pct = float(payload.get("risk_pct", 0))
            leverage = int(payload.get("leverage", 0))
            max_pos = int(payload.get("max_pos", 0))
            return on_update_live_settings(usdt_amount, risk_pct, leverage, max_pos)
        except Exception as e:
            logger.exception("set-live-settings handler error: %s", e)
            return {"ok": False, "error": str(e)}

    @app.get("/api/paper-config")
    async def get_paper_config():
        """F-01: Retorna configurações Paper salvas em preferences.json para preencher cockpit no boot."""
        try:
            from config import load_preferences, resolve_preferences_path
            prefs = load_preferences(resolve_preferences_path())
            paper_node = prefs.get("paper") or {}
            return {
                "ok": True,
                "initial_capital": float(paper_node.get("initial_capital", 1000.0)),
                "risk_pct": float(paper_node.get("risk_pct_per_trade", 0.05)) * 100,
                "leverage": int(paper_node.get("leverage", 10)),
                "max_open_positions": int(paper_node.get("max_open_positions", 20)),
            }
        except Exception as e:
            logger.exception("Erro ao buscar configurações Paper: %s", e)
            return {"ok": False, "error": str(e)}

    @app.get("/api/live-advanced-config")
    async def get_live_advanced_config():
        """SPRINT 12.21: Retorna configurações avançadas LIVE atuais (incluindo AUTO-PILOT)."""
        try:
            from config import load_preferences, resolve_preferences_path
            
            prefs = load_preferences(resolve_preferences_path())
            live_cfg = prefs.get("live") or {}
            exec_p = live_cfg.get("execution") or {}
            signal_p = live_cfg.get("signal") or {}
            
            return {
                "ok": True,
                "auto_pilot": bool(live_cfg.get("auto_pilot", False)),
                "sl_pct": float(exec_p.get("sl_pct", 0.015)) * 100,
                "tp_pct": float(exec_p.get("tp_pct", 0.05)) * 100,
                "max_hold_min": int(exec_p.get("max_hold_seconds", 0)) / 60,
                "signal_mode": str(signal_p.get("signal_mode", "conservative")),
                "trailing_enabled": bool(exec_p.get("sl_trailing_swing_low", True)),
                "kelly_enabled": bool(exec_p.get("kelly_enabled", False)),
                # F-01: campos de persistência do cockpit Live
                "usdt_amount": float(live_cfg.get("usdt_amount", 20.0)),
                "risk_pct": float(live_cfg.get("risk_pct_per_trade", 0.03)) * 100,
                "leverage": int(live_cfg.get("leverage", 8)),
                "max_open_positions": int(live_cfg.get("max_open_positions", 3)),
                "compound_enabled": bool(live_cfg.get("compound_enabled", False)),
            }
        except Exception as e:
            logger.exception("Erro ao buscar configurações avançadas LIVE: %s", e)
            return {"ok": False, "error": str(e)}

    @app.post("/api/set-live-advanced")
    async def set_live_advanced(request: Request, payload: dict):
        """SPRINT 12.21: API para configurações avançadas LIVE (SL, TP, Max Hold, Signal Mode, Trailing, Kelly, AUTO-PILOT)."""
        ip = _http_guard(request)
        _http_rate_limit(f"set-live-advanced:{ip}", limit=2, window_seconds=10.0)
        if on_update_live_advanced is None:
            return {"ok": False, "error": "set-live-advanced handler not configured"}
        try:
            auto_pilot = bool(payload.get("auto_pilot", False))
            sl_pct = float(payload.get("sl_pct", 0))
            tp_pct = float(payload.get("tp_pct", 0))
            max_hold_min = int(payload.get("max_hold_min", 0))
            signal_mode = str(payload.get("signal_mode", "conservative"))
            trailing_enabled = bool(payload.get("trailing_enabled", False))
            kelly_enabled = bool(payload.get("kelly_enabled", False))
            return on_update_live_advanced(auto_pilot, sl_pct, tp_pct, max_hold_min, signal_mode, trailing_enabled, kelly_enabled)
        except Exception as e:
            logger.exception("set-live-advanced handler error: %s", e)
            return {"ok": False, "error": str(e)}

    @app.post("/api/set-live-compound")
    async def set_live_compound(request: Request, payload: dict):
        """SPRINT 12.18: API para alternar juros compostos."""
        ip = _http_guard(request)
        if on_toggle_live_compound is None:
            return {"ok": False, "error": "handler not configured"}
        enabled = bool(payload.get("enabled", False))
        return on_toggle_live_compound(enabled)
    @app.get("/api/data-health")
    async def data_health():
        """P0.1: Retorna saúde de dados (completude de métricas) para auditoria."""
        try:
            if engine and engine.store:
                health = engine.store.get_data_health_summary()
                return {"ok": True, **health}
            return {"ok": False, "error": "Engine not available"}
        except Exception as e:
            logger.exception("Erro ao buscar data health: %s", e)
            return {"ok": False, "error": str(e)}


    @app.get("/api/refusal-stats")
    async def refusal_stats():
        """SPRINT 12.20: Retorna estatísticas via memória (Zero Disk I/O)."""
        stats = signals.get_refusal_stats()
        return {
            "count": stats["total_blocked"],
            "reasons": stats["top_motivos"],
            "total_signals": stats["total_analyzed"]
        }

    @app.post("/api/save-preferences")
    async def save_preferences(request: Request, payload: dict):
        """
        Salva preferências em preferences.json com backup automático.
        Garante que mudanças persistam após reinícios, quedas, refreshs.
        """
        _http_guard(request)
        _http_rate_limit(f"save-prefs-{_http_client_ip(request)}", limit=10, window_seconds=60)

        import json
        import shutil
        from pathlib import Path
        from datetime import datetime

        prefs_path = Path("preferences.json")
        
        try:
            # Validação básica do payload
            if not isinstance(payload, dict):
                raise ValueError("Payload deve ser um objeto JSON")
            
            # Validação de estrutura mínima
            required_keys = ["trading_mode", "paper", "live"]
            for key in required_keys:
                if key not in payload:
                    raise ValueError(f"Chave obrigatória ausente: {key}")
            
            # Validação de Paper e Live
            for mode in ["paper", "live"]:
                if not isinstance(payload[mode], dict):
                    raise ValueError(f"Bloco '{mode}' deve ser um objeto")
                if "signal" not in payload[mode] or "execution" not in payload[mode]:
                    raise ValueError(f"Bloco '{mode}' deve conter 'signal' e 'execution'")
            
            # Backup automático antes de salvar
            if prefs_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = Path(f"preferences.json.backup_{timestamp}")
                shutil.copy2(prefs_path, backup_path)
                logger.info(f"✅ Backup criado: {backup_path}")

                # Mantém apenas últimas 5 versões de backup
                backups = sorted(Path(".").glob("preferences.json.backup_*"))
                if len(backups) > 5:
                    for old_backup in backups[:-5]:
                        old_backup.unlink()
                        logger.debug(f"🗑️ Backup antigo removido: {old_backup}")
            
            # Salva novo arquivo
            with prefs_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            
            logger.info("✅ Preferências salvas com sucesso em preferences.json")
            
            return {
                "success": True,
                "message": "Preferências salvas com sucesso",
                "file": str(prefs_path),
                "timestamp": datetime.now().isoformat()
            }
        
        except ValueError as e:
            logger.error(f"❌ Validação falhou: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"❌ Erro ao salvar preferências: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao salvar: {str(e)}")
    
    @app.get("/api/load-preferences")
    async def load_preferences(request: Request):
        """
        Carrega preferências atuais de preferences.json
        """
        _http_guard(request)

        import json
        from pathlib import Path

        prefs_path = Path("preferences.json")

        try:
            if not prefs_path.exists():
                raise FileNotFoundError("preferences.json não encontrado")
            
            with prefs_path.open("r", encoding="utf-8") as f:
                prefs = json.load(f)
            
            return {
                "success": True,
                "preferences": prefs,
                "file": str(prefs_path)
            }
        
        except Exception as e:
            logger.error(f"❌ Erro ao carregar preferências: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao carregar: {str(e)}")
    
    @app.get("/api/list-backups")
    async def list_backups(request: Request):
        """
        Lista backups disponíveis de preferences.json
        """
        _http_guard(request)

        from pathlib import Path
        from datetime import datetime

        try:
            backups = sorted(Path(".").glob("preferences.json.backup_*"), reverse=True)
            
            backup_list = []
            for backup in backups:
                stat = backup.stat()
                backup_list.append({
                    "filename": backup.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            return {
                "success": True,
                "backups": backup_list,
                "count": len(backup_list)
            }
        
        except Exception as e:
            logger.error(f"❌ Erro ao listar backups: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao listar: {str(e)}")
    
    @app.post("/api/restore-backup")
    async def restore_backup(request: Request, payload: dict):
        """
        Restaura um backup específico de preferences.json
        """
        _http_guard(request)
        _http_rate_limit(f"restore-{_http_client_ip(request)}", limit=5, window_seconds=60)

        import shutil
        from pathlib import Path

        try:
            filename = payload.get("filename")
            if not filename:
                raise ValueError("Nome do arquivo de backup não fornecido")

            backup_path = Path(filename)
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup não encontrado: {filename}")

            prefs_path = Path("preferences.json")

            # Backup do arquivo atual antes de restaurar
            if prefs_path.exists():
                shutil.copy2(prefs_path, "preferences.json.before_restore")
            
            # Restaura backup
            shutil.copy2(backup_path, prefs_path)
            
            logger.info(f"✅ Backup restaurado: {filename}")
            
            return {
                "success": True,
                "message": f"Backup restaurado: {filename}",
                "restored_from": str(backup_path)
            }
        
        except Exception as e:
            logger.error(f"❌ Erro ao restaurar backup: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao restaurar: {str(e)}")


    # SPRINT 11.28: Removed individual set-initial-capital, set-risk-pct, set-leverage, set-max-pos handlers.
    # They are replaced by set-paper-settings and set-live-settings.

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        peer_host = websocket.client.host if websocket.client else "unknown"
        await websocket.accept()
        logger.info(f"✅ WebSocket CONECTADO: Enviando dados para {peer_host}")
        _dash_diag(f"WS accepted peer_host={peer_host}")

        # Dados de controle da conexão
        conn_ctx = {"interval": 1.0}

        async def send_loop():
            while True:
                try:
                    # SPRINT 6.51: Deep Copy via Thread para evitar RuntimeError de mutação no JSON
                    import json
                    # Diagnostics: log imediato do ciclo de envio (primeira vez + após snapshot)
                    try:
                        now_ts0 = time.time()
                        if not conn_ctx.get("first_send_diag_done", False):
                            conn_ctx["first_send_diag_done"] = True
                            _dash_diag(
                                "WS send_loop first tick peer_host=%s interval=%.2fs uptime=%ss warmup_remaining=%.1fs"
                                % (
                                    peer_host,
                                    conn_ctx.get("interval", 1.0),
                                    int(now_ts0 - state.boot_started_at),
                                    getattr(state, "warmup_remaining", 0.0),
                                )
                            )
                    except Exception:
                        pass

                    # SPRINT 11.22: Snapshot com try/except para não derrubar o WS por erro de I/O lateral
                    try:
                        raw_snap = await asyncio.to_thread(state.snapshot)
                    except Exception as e:
                        logger.debug("Falha temporária no snapshot (I/O Lock): %s", e)
                        await asyncio.sleep(0.5)
                        continue

                    try:
                        # evita logar payload gigante; log apenas tamanho aproximado e warmup
                        approx_len = 0
                        try:
                            approx_len = len(raw_snap) if isinstance(raw_snap, dict) else 0
                        except Exception:
                            approx_len = 0
                        _dash_diag(
                            "WS snapshot ready peer_host=%s warmup_remaining=%.1fs approx_rows=%s"
                            % (peer_host, float(getattr(state, "warmup_remaining", 0.0)), approx_len)
                        )
                    except Exception:
                        pass

# Evita deep-copy caro (json dumps/loads) que pode travar quando snapshot cresce.
                    snap = raw_snap

                    # SPRINT 12.48: Garante sincronia do Compound via WebSocket no root
                    snap["compound_enabled"] = getattr(state, "compound_enabled", False)

                    # SPRINT 12.20: Adicionar dados do LiveTracker ao snapshot
                    if live_tracker:
                        try:
                            live_snapshot = live_tracker.get_snapshot()
                            snap["live_tracker"] = live_snapshot
                        except Exception as e:
                            logger.warning(f"Erro ao obter snapshot do LiveTracker: {e}")

                    await websocket.send_json(snap)

                    try:
                        warmup_remaining = float(snap.get("warmup_remaining") or 0.0)
                    except Exception:
                        warmup_remaining = 0.0

                    try:
                        if warmup_remaining <= 0.0:
                            if not conn_ctx.get("warmup_done_ts"):
                                conn_ctx["warmup_done_ts"] = time.time()
                            done_age = time.time() - conn_ctx["warmup_done_ts"]
                            conn_ctx["interval"] = 3.0 if done_age < 60.0 else 2.0
                        else:
                            conn_ctx["interval"] = 1.5
                    except Exception:
                        pass

                    try:
                        now_ts = time.time()
                        last = conn_ctx.get("last_send_diag_ts", 0.0)
                        if now_ts - last >= 60.0:
                            conn_ctx["last_send_diag_ts"] = now_ts
                            _dash_diag(
                                "WS sent snapshot peer_host=%s interval=%.2fs uptime=%ss warmup_remaining=%.1fs"
                                % (
                                    peer_host,
                                    conn_ctx.get("interval", 1.0),
                                    int(now_ts - state.boot_started_at),
                                    warmup_remaining,
                                )
                            )
                    except Exception:
                        pass

                    await asyncio.sleep(conn_ctx["interval"])
                except (WebSocketDisconnect, asyncio.CancelledError):
                    _dash_diag(f"WS disconnected peer_host={peer_host}")
                    return
                except RuntimeError as exc:
                    logger.warning("⚠️ [WS] RuntimeError during snapshot/send: %s — retrying", exc)
                    _dash_diag(f"WS RuntimeError during snapshot/send peer_host={peer_host}: {type(exc).__name__}: {exc}")
                    await asyncio.sleep(0.2)
                    continue
                except AssertionError:
                    _dash_diag(f"WS AssertionError during send peer_host={peer_host} (connection closing)")
                    return
                except Exception as exc:
                    _dash_diag(f"WS send_loop Exception peer_host={peer_host}: {type(exc).__name__}: {exc}")
                    logger.warning("⚠️ [WS] send err: %s", exc)
                    await asyncio.sleep(0.5)
                    try:
                        if websocket.client_state.name != "CONNECTED":
                            return
                    except Exception:
                        return

        # Rodar o loop de envio em background e usar o loop principal para receber comandos
        sender_task = asyncio.create_task(send_loop())

        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "visibility":
                    is_visible = data.get("state") == "visible"
                    conn_ctx["interval"] = 1.0 if is_visible else 10.0
                    logger.debug(f"WS {peer_host} visibility: {data.get('state')} (interval={conn_ctx['interval']}s)")
        except (WebSocketDisconnect, RuntimeError):
            print(f"[WS] disconnected from {peer_host}", flush=True)
        finally:
            _dash_diag(f"WS finally peer_host={peer_host} (cancelling sender_task)")
            # Cancelar o sender primeiro evita race: ele pode estar tentando enviar enquanto o socket fecha.
            sender_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sender_task
            # Depois fechamos o websocket (só para garantir limpeza)
            with contextlib.suppress(Exception):
                await websocket.close()
            _dash_diag(f"WS closed peer_host={peer_host}")

    return app


def _find_chrome(explicit_path: Optional[str] = None) -> Optional[Path]:
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            return p
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _server_ready(url: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.25)
    return False


def _open_chrome_when_ready(
    url: str,
    *,
    chrome_path: Optional[str] = None,
    wait_timeout: float = 90.0,
) -> None:
    logger.info("Aguardando dashboard em %s para abrir o Chrome…", url)

    # Roadmap 12.1: dashboard.enabled=true => falha fatal se não ficar pronto.
    if not _server_ready(url, timeout=wait_timeout):
        logger.error("❌ [DASHBOARD FATAL] Não respondeu em %.1fs — encerrando processo: %s", wait_timeout, url)
        _dash_diag(f"Dashboard fatal: server not ready url={url} timeout={wait_timeout}")
        os._exit(2)

    chrome = _find_chrome(chrome_path)
    try:
        if chrome:
            subprocess.Popen(
                [str(chrome), "--new-window", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            logger.info("Chrome aberto: %s", url)
            return
        registered = webbrowser.get("chrome")
        registered.open(url, new=1)
        logger.info("Chrome (webbrowser) aberto: %s", url)
    except webbrowser.Error:
        webbrowser.open(url)
        logger.info("Navegador padrão aberto: %s", url)
    except Exception as e:
        logger.warning("Falha ao abrir Chrome: %s — acesse %s", e, url)


def run_dashboard_thread(
    state: BotState,
    signal_engine: SqueezeIgnition, # Injeção SPRINT 12.20
    host: str = "0.0.0.0",
    port: int = 8765,
    auto_open: bool = True,
    browser: str = "chrome",
    chrome_path: Optional[str] = None,
    on_set_mode: Optional[Callable[[str], Any]] = None,
    on_reset_paper: Optional[Callable[[], Any]] = None,
    on_hard_reset: Optional[Callable[[], Any]] = None, # SPRINT 6.45
    on_update_paper_settings: Optional[Callable[[float, float, int, int], Any]] = None,
    on_update_live_settings: Optional[Callable[[float, float, int, int], Any]] = None,
    on_update_live_advanced: Optional[Callable[[bool, float, float, int, str, bool, bool], Any]] = None,  # SPRINT 12.21: auto_pilot, sl_pct, tp_pct, max_hold_min, signal_mode, trailing_enabled, kelly_enabled
    on_exit: Optional[Callable[[], Any]] = None, # SPRINT EXIT
    on_toggle_live_compound: Optional[Callable[[bool], Any]] = None,
    on_close_trade: Optional[Callable[[str, str], Any]] = None,
    on_close_all_live: Optional[Callable[[], Any]] = None,
    live_tracker: Optional[Any] = None,  # SPRINT 12.20: LiveTracker para modo LIVE
    engine: Optional[Any] = None,
) -> threading.Thread:
    """
    Uvicorn em thread separada — evita travar o event loop do bot no Windows.
    """
    app = create_app(state, signals=signal_engine, on_set_mode=on_set_mode, on_reset_paper=on_reset_paper,
                     on_hard_reset=on_hard_reset,
                     on_update_paper_settings=on_update_paper_settings,
                     on_update_live_settings=on_update_live_settings,
                     on_update_live_advanced=on_update_live_advanced,
                     on_exit=on_exit,
                     on_toggle_live_compound=on_toggle_live_compound,
                     on_close_trade=on_close_trade,
                     on_close_all_live=on_close_all_live,
                     live_tracker=live_tracker,  # SPRINT 12.20: Passar LiveTracker para o app
                     engine=engine,
                     )
    # Para o browser, usamos 127.0.0.1 (mesmo que ouça em 0.0.0.0) para garantir acesso local/port forwarding
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"

    def _serve():
        _dash_diag(f"Dashboard thread starting url={url} host={host} port={port}")
        logger.info("Dashboard web em %s", url)
        try:
            _dash_diag("Calling uvicorn.run(...)")
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
                access_log=True,
                # SPRINT 11.1: Desabilitado ping para evitar desconexões por lag de CPU em laptops
                ws_ping_interval=None,
                ws_ping_timeout=None,
            )
            _dash_diag("uvicorn.run exited normally.")
        except Exception as e:
            _dash_diag(f"uvicorn.run crashed: {type(e).__name__}: {e}")
            logger.exception("uvicorn.run crashed: %s", e)

    if auto_open:
        path = chrome_path if chrome_path else None
        if browser.lower() == "chrome":
            threading.Thread(
                target=_open_chrome_when_ready,
                args=(url,),
                kwargs={"chrome_path": path},
                name="ChromeLauncher",
                daemon=True,
            ).start()
        else:

            def _open_default() -> None:
                if _server_ready(url):
                    webbrowser.open(url)
                    logger.info("Navegador aberto: %s", url)

            threading.Thread(target=_open_default, name="BrowserLauncher", daemon=True).start()

    thread = threading.Thread(target=_serve, name="WebDashboard", daemon=True)
    thread.start()
    return thread
