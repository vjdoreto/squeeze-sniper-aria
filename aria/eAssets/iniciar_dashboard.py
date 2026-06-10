"""
iniciar_dashboard.py — Launcher do eAssets Dashboard
Doreto Squeeze Sniper · v2.0 · 09/06/2026

Inicia UM único processo (server.py) e abre o browser.
O server.py já faz tudo: monitor de arquivos + fetch macro + cálculo dos indicadores.
"""

import subprocess
import webbrowser
import time
import sys
from pathlib import Path

BASE_PATH = Path(__file__).parent
HTML_FILE = BASE_PATH / "doreto-squeeze-sniper.html"
SERVER    = BASE_PATH / "server.py"


def launch():
    print("🔥 Iniciando eAssets Dashboard Server v2.0...")

    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    print(f"⏳ Servidor iniciado (PID {proc.pid}) — aguardando 3s...")
    time.sleep(3)

    print(f"🌐 Abrindo dashboard: {HTML_FILE.as_uri()}")
    webbrowser.open(HTML_FILE.absolute().as_uri())

    print("✅ Pronto! Feche a janela do servidor para encerrar.")


if __name__ == "__main__":
    launch()
