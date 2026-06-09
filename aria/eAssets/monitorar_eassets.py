import os
import time
import json
import shutil
from pathlib import Path
import logging

# Configurações de Caminhos
DOWNLOADS_PATH = Path.home() / "Downloads"
DADOS_LOCAL_PATH = Path("c:/Apps/#5 SqueezeSniper-V4/eAssets/dados_eassets")
LOGS_SNIPER_PATH = Path("c:/Apps/#5 SqueezeSniper-V4/logs")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("eAssetsMonitor")

def get_latest_eassets_json(directory: Path):
    """Busca o arquivo eassets-panel-*.json mais recente na pasta."""
    files = list(directory.glob("eassets-panel-*.json"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def process_file(file_path: Path):
    """Copia o arquivo para a pasta de dados local para ser servido pelo Dashboard."""
    target = DADOS_LOCAL_PATH / "eassets_latest.json"
    history_dir = DADOS_LOCAL_PATH / "historico"
    try:
        # SPRINT E-AUTO: Garante que o arquivo não esteja sendo escrito (espera 500ms)
        initial_size = file_path.stat().st_size
        time.sleep(0.5)
        if file_path.stat().st_size != initial_size:
            return False # Ainda baixando...
        
        # Salva na pasta de trabalho do Dashboard
        shutil.copy2(file_path, target)
        
        # Cria histórico para os dados cripto não se perderem
        history_dir.mkdir(exist_ok=True)
        shutil.copy2(file_path, history_dir / file_path.name)
        
        logger.info(f"✅ Novo JSON detectado e processado: {file_path.name}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao processar arquivo: {e}")
        return False

def start_monitoring():
    DADOS_LOCAL_PATH.mkdir(parents=True, exist_ok=True)
    last_processed = None
    
    logger.info(f"👀 Monitorando Downloads em: {DOWNLOADS_PATH}")
    logger.info(f"👀 Monitorando Dados Locais em: {DADOS_LOCAL_PATH}")

    while True:
        # 1. Verifica Downloads
        latest_download = get_latest_eassets_json(DOWNLOADS_PATH)
        # 2. Verifica Pasta Local (caso o usuário jogue lá manualmente)
        latest_local = get_latest_eassets_json(DADOS_LOCAL_PATH)
        
        # Decide qual é o mais novo entre as duas pastas
        candidates = [f for f in [latest_download, latest_local] if f]
        if candidates:
            newest = max(candidates, key=os.path.getmtime)
            
            if newest != last_processed:
                if process_file(newest):
                    last_processed = newest
        
        time.sleep(2) # Pooling de 2 segundos para não fritar a CPU

if __name__ == "__main__":
    start_monitoring()