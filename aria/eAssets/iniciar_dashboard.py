import subprocess
import webbrowser
import time
import os
import sys
from pathlib import Path

BASE_PATH = Path("c:/Apps/#5 SqueezeSniper-V4/eAssets")
HTML_FILE = BASE_PATH / "doreto-squeeze-sniper.html"

def launch():
    print("🔥 Iniciando Ecossistema eAssets...")
    
    # 1. Inicia o Servidor de Enriquecimento
    subprocess.Popen([sys.executable, str(BASE_PATH / "enrich_server.py")], 
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    # 2. Inicia o Monitor de Downloads/Pastas
    subprocess.Popen([sys.executable, str(BASE_PATH / "monitorar_eassets.py")], 
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    print("⏳ Aguardando inicialização dos serviços...")
    time.sleep(2)
    
    # 3. Abre o Dashboard no Navegador
    webbrowser.open(HTML_FILE.absolute().as_uri())

if __name__ == "__main__":
    launch()