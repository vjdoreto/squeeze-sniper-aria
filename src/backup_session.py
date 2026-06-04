import logging
import os
import stat
import shutil
from datetime import datetime
from pathlib import Path

_log = logging.getLogger("BackupSession").info


def _force_remove(func, path, _exc):
    """Handler para rmtree no Windows: remove flag read-only antes de deletar."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def create_backup():
    # SPRINT 6.39: Conta trades reais para nomear a pasta dinamicamente
    closed_path = Path("logs/paper_closed.jsonl")
    trade_count = 0
    if closed_path.exists():
        with open(closed_path, "r", encoding="utf-8") as f:
            trade_count = sum(1 for line in f if line.strip())

    # Nome da pasta de backup com data e hora
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/session_{timestamp}_{trade_count}trades")
    # SPRINT 6.40: Pasta fixa para o backup mais recente (sobrescreve)
    latest_dir = Path("backups/LATEST_SESSION")
    
    # Arquivos e pastas a serem salvos
    to_backup = [
        Path("logs/paper_closed.jsonl"),
        Path("logs/signals.jsonl"),
        Path("logs/signal_refusals.jsonl"),
        Path("logs/paper_opportunities.json"),
        Path("logs/paper_opportunities.csv"),
        Path("logs/metric_state.json"),
        Path("logs/history"),
        Path("preferences.json"),
        Path("docs/Engenheiro e DNA do Sniper.md"),
        Path("docs/CHANGELOG.md"),
        Path("docs/ROADMAP_LIVE_V4.2.5_2026-06-02.md"),
    ]
    
    _log(f"[BACKUP] Iniciando: {backup_dir}")

    if not backup_dir.exists():
        backup_dir.mkdir(parents=True)

    if latest_dir.exists():
        shutil.rmtree(latest_dir, onexc=_force_remove)
    latest_dir.mkdir(parents=True)

    for item in to_backup:
        if not item.exists():
            _log(f"[BACKUP] Aviso: {item} nao encontrado, pulando...")
            continue

        dest = backup_dir / item.name
        dest_latest = latest_dir / item.name

        try:
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
                shutil.copytree(item, dest_latest, dirs_exist_ok=True)
                _log(f"[BACKUP] Pasta copiada: {item}")
            else:
                shutil.copy2(item, dest)
                shutil.copy2(item, dest_latest)
                _log(f"[BACKUP] Arquivo copiado: {item}")
        except Exception as e:
            _log(f"[BACKUP] Erro ao copiar {item}: {e}")

    _log(f"[BACKUP] Concluido: {backup_dir.resolve()}")

if __name__ == "__main__":
    create_backup()