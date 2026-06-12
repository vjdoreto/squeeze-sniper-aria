import logging
import time
import json
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("RiskManager")

# Grupos de correlação — fonte única de verdade para paper_tracker e live_tracker.
# Máximo 1 posição simultânea por grupo. Atualizar aqui reflete em ambos os modos.
CORR_GROUPS: Dict[str, List[str]] = {
    "L1":      ["SOLUSDT", "AVAXUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT",
                 "ADAUSDT", "DOTUSDT", "ATOMUSDT"],
    "DeFi":    ["AAVEUSDT", "UNIUSDT", "CRVUSDT", "COMPUSDT", "MKRUSDT", "SNXUSDT"],
    "Meme":    ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT"],
    "AI":      ["FETUSDT", "AGIXUSDT", "OCEANUSDT", "RENDERUSDT", "WLDUSDT"],
    "Gaming":  ["AXSUSDT", "SANDUSDT", "MANAUSDT", "ENJUSDT", "GALAUSDT"],
    "Layer2":  ["MATICUSDT", "ARBUSDT", "OPUSDT", "STRKUSDT", "ZKUSDT"],
    "BTC_Eco": ["WBTCUSDT", "STXUSDT", "RUNEUSDT"],
}

class DrawdownManager:
    """
    SPRINT 12.150: Gerenciador de Risco e Drawdown (DNA Sniper).
    Implementa circuit breaker e redução progressiva de risco.
    
    Regra de Ouro: Sequência de perdas = Redução imediata de exposição.
    """
    def __init__(self, max_dd_pct: float = 15.0, state_path: str = "logs/risk_state.json"):
        self.max_dd_pct = max_dd_pct
        self.state_path = Path(state_path)
        self.consecutive_losses = 0
        self.risk_multiplier = 1.0
        self.trading_paused = False
        self._load_state()
    
    def update(self, current_capital: float, peak_capital: float, last_trade_win: bool):
        # Atualiza perdas consecutivas
        if not last_trade_win:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
            
        # Cálculo de Drawdown
        dd_pct = (peak_capital - current_capital) / peak_capital * 100 if peak_capital > 0 else 0
        
        # Redução de Risco (Governança Semana 3-4)
        if self.consecutive_losses >= 3:
            self.risk_multiplier = 0.5
            logger.warning(f"⚠️ {self.consecutive_losses} LOSSES SEGUIDOS - Risco reduzido em 50%")
        elif self.consecutive_losses >= 2:
            self.risk_multiplier = 0.75
            logger.warning(f"⚠️ 2 LOSSES SEGUIDOS - Risco reduzido em 25%")
        else:
            self.risk_multiplier = 1.0
            
        # Circuit Breaker Global
        if dd_pct >= self.max_dd_pct:
            self.trading_paused = True
            logger.critical(f"🛑 CIRCUIT BREAKER ATIVO: Drawdown de {dd_pct:.2f}% atingiu limite de {self.max_dd_pct}%")
        else:
            self.trading_paused = False
            
        self._save_state()
            
    def can_trade(self) -> bool:
        return not self.trading_paused

    def reset(self) -> None:
        self.consecutive_losses = 0
        self.risk_multiplier = 1.0
        self.trading_paused = False
        try:
            self.state_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Erro ao remover risk_state: %s", e)

    def _save_state(self):
        try:
            state = {
                "consecutive_losses": self.consecutive_losses,
                "risk_multiplier": self.risk_multiplier,
                "trading_paused": self.trading_paused
            }
            self.state_path.write_text(json.dumps(state))
        except Exception as e:
            logger.error(f"Erro ao salvar risk state: {e}")

    def _load_state(self):
        if self.state_path.exists():
            try:
                state = json.loads(self.state_path.read_text())
                self.consecutive_losses = state.get("consecutive_losses", 0)
                self.risk_multiplier = state.get("risk_multiplier", 1.0)
                self.trading_paused = state.get("trading_paused", False)
            except: pass

class SymbolThrottler:
    """
    SPRINT 12.132: Throttle por Símbolo (Governança de Squeeze).
    Impede o 'over-trading' na mesma moeda em janelas curtas.
    Evita pegar o final de um movimento exausto.
    """
    def __init__(self, window_seconds: int = 3600, state_path: str = "logs/throttle_state.json"):
        self.symbol_history: Dict[str, List[float]] = {}
        self.window_seconds = window_seconds
        self.state_path = Path(state_path)
        self.max_per_window = 1
        self._load_state()

    def can_trade(self, symbol: str) -> bool:
        now = time.time()
        history = self.symbol_history.get(symbol, [])
        
        # Remove registros fora da janela
        valid_history = [ts for ts in history if now - ts < self.window_seconds]
        self.symbol_history[symbol] = valid_history
        
        if len(valid_history) >= self.max_per_window:
            return False
        return True

    def record_trade(self, symbol: str):
        now = time.time()
        if symbol not in self.symbol_history:
            self.symbol_history[symbol] = []
        self.symbol_history[symbol].append(now)
        self._save_state()

    def extend_cooldown(self, symbol: str, total_seconds: int = 14400) -> None:
        """D-HIGH-2: Cooldown estendido após SL hit (padrão 4h).
        Coloca timestamp futuro tal que o símbolo fica bloqueado por total_seconds a partir de agora.
        """
        future_ts = time.time() + total_seconds - self.window_seconds
        self.symbol_history[symbol] = [future_ts]
        self._save_state()

    def reset(self) -> None:
        self.symbol_history = {}
        try:
            self.state_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Erro ao remover throttle_state: %s", e)

    def _save_state(self):
        try:
            self.state_path.write_text(json.dumps(self.symbol_history))
        except Exception as e:
            logger.error(f"Erro ao salvar throttle state: {e}")

    def _load_state(self):
        if self.state_path.exists():
            try:
                raw = json.loads(self.state_path.read_text())
                now = time.time()
                # Filtra apenas o histórico ainda válido para a janela atual
                self.symbol_history = {
                    s: [ts for ts in history if now - ts < self.window_seconds]
                    for s, history in raw.items()
                }
            except: pass