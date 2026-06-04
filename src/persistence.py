"""Light audit trail for paper/live signals."""
import csv
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading

logger = logging.getLogger("Persistence")


class SignalJournal:
    def __init__(self, path: str = "logs/signals.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_signal(self, signal: Dict[str, Any], *, trading_mode: str) -> None:
        record = {
            "trading_mode": trading_mode,
            **signal,
        }
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error("Falha ao gravar sinal: %s", e)


class DailySnapshotLogger:
    """Grava snapshots em CSV para persistência de longo prazo e análise de rastro."""
    def __init__(self, folder: str = "logs/history"):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._last_date: Optional[str] = None
        self._lock = threading.Lock()
        self._headers = ["timestamp", "symbol", "price", "oi", "lsr", "cvd_1m", "trades_1m", "exp_btc", "lsr_change_pct", "oi_accel"]

    def _get_file(self) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = self.folder / f"snapshots_{date_str}.csv"

        # Verifica se o arquivo precisa de cabeçalho (não existe ou está vazio)
        # Isso garante resiliência caso o usuário delete o arquivo com o bot rodando
        try:
            if not file_path.exists() or (file_path.is_file() and file_path.stat().st_size == 0):
                self.folder.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(self._headers)
        except (OSError, PermissionError) as e:
            logger.error("Erro de I/O no CSV History: %s", e)
        
        self._last_date = date_str

        return file_path

    def log_snapshots(self, ts: float, symbols: List[str], data: Dict[str, Dict]):
        """Versão otimizada para ser chamada em thread, evitando travar a produção."""
        with self._lock:
            file_path = self._get_file()
            try:
                with open(file_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for s in symbols:
                        d = data.get(s, {})
                        if (d.get("price") or 0) > 0:
                            writer.writerow([
                                ts, s, d.get("price"), d.get("oi"), d.get("lsr") or 0.0,
                                d.get("volume_delta_1min", 0), d.get("trades_count_1min", 0),
                                d.get("exp_btc:5m") or 0.0,
                                d.get("lsr_change_pct:5m") or 0.0,
                                d.get("oi_accel:5m") or 0.0
                            ])
            except Exception as e:
                logger.error("Falha ao gravar CSV de snapshots: %s", e)
