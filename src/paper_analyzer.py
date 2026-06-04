import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("PaperAnalyzer")


@dataclass
class AnalysisResult:
    total_trades: int
    win_rate: float
    avg_pnl: float
    avg_mfe: float
    avg_mae: float
    suggestions: List[str]
    parameter_changes: Dict[str, Any]
    win_rate_per_symbol: Dict[str, float]


class PaperAnalyzer:
    def __init__(
        self,
        paper_closed_jsonl_path: Path = Path("logs/paper_closed.jsonl"),
        min_trades_for_calibration: int = 30,
    ):
        self.paper_closed_jsonl_path = paper_closed_jsonl_path
        self.min_trades_for_calibration = min_trades_for_calibration
        self.last_analysis_trades = 0

    def load_trades(self) -> List[Dict]:
        """Carrega trades fechados do JSONL."""
        try:
            if not self.paper_closed_jsonl_path.exists():
                return []
            
            closed_trades = []
            with open(self.paper_closed_jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    closed_trades.append(json.loads(line))
            
            return closed_trades
        except Exception as e:
            logger.error("Erro ao carregar trades: %s", e)
            return []

    def analyze_trades(self, closed_trades: List[Dict]) -> AnalysisResult:
        """Analisa os trades fechados e retorna o resultado com sugestões."""
        if not closed_trades:
            return AnalysisResult(
                total_trades=0,
                win_rate=0.0,
                avg_pnl=0.0,
                avg_mfe=0.0,
                avg_mae=0.0,
                suggestions=["Nenhum trade fechado ainda para análise."],
                parameter_changes={},
                win_rate_per_symbol={}
            )

        total = len(closed_trades)
        wins = [t for t in closed_trades if t.get("exit", {}).get("pnl_pct", 0) >= 0]
        losses = [t for t in closed_trades if t.get("exit", {}).get("pnl_pct", 0) < 0]
        win_rate = (len(wins) / total) * 100 if total > 0 else 0.0

        avg_pnl = sum(t.get("exit", {}).get("pnl_pct", 0) for t in closed_trades) / total
        avg_mfe = sum(t.get("live", {}).get("mfe_pct", 0) for t in closed_trades) / total
        avg_mae = sum(t.get("live", {}).get("mae_pct", 0) for t in closed_trades) / total

        suggestions, parameter_changes, win_rate_per_sym = self._generate_suggestions(closed_trades, wins, losses, win_rate)

        return AnalysisResult(
            total_trades=total,
            win_rate=win_rate,
            avg_pnl=avg_pnl,
            avg_mfe=avg_mfe,
            avg_mae=avg_mae,
            suggestions=suggestions,
            parameter_changes=parameter_changes,
            win_rate_per_symbol=win_rate_per_sym
        )

    def _generate_suggestions(
        self,
        closed_trades: List[Dict],
        wins: List[Dict],
        losses: List[Dict],
        win_rate: float
    ) -> Tuple[List[str], Dict[str, Any], Dict[str, float]]:
        """Gera sugestões com base nos padrões dos trades."""
        suggestions = []
        # Inicializa params com tipo anônimo para não gerar erro de atribuição
        params: Dict[str, Any] = {}
        signal_params: Dict[str, Any] = {}
        exec_params: Dict[str, Any] = {}
        params["signal"] = signal_params
        params["execution"] = exec_params
        params["blacklist"] = []

        # Cálculo de estatísticas por Símbolo (ROADMAP Sprint 10 / 10.2)
        # Blacklist automática (PaperAnalyzer):
        #   1) Pelo menos 2 trades no símbolo
        #   2) WR < 35%
        #   3) Avg PnL < -0.5%  (média de exit.pnl_pct)
        sym_stats: Dict[str, Dict[str, float]] = {}
        for t in closed_trades:
            sym = t["symbol"]
            if sym not in sym_stats:
                sym_stats[sym] = {"w": 0.0, "t": 0.0, "pnl_sum": 0.0}
            pnl_pct = float(t.get("exit", {}).get("pnl_pct", 0.0) or 0.0)

            sym_stats[sym]["t"] += 1.0
            sym_stats[sym]["pnl_sum"] += pnl_pct
            if pnl_pct >= 0:
                sym_stats[sym]["w"] += 1.0

        win_rate_per_sym = {
            s: round((d["w"] / d["t"]) * 100.0, 1) if d["t"] > 0 else 0.0
            for s, d in sym_stats.items()
        }

        to_blacklist = [
            s
            for s, data in sym_stats.items()
            if data["t"] >= 2
            and (data["w"] / data["t"]) < 0.35
            and (data["pnl_sum"] / data["t"]) < -0.5
        ]

        if to_blacklist:
            suggestions.append(f"🚫 Blacklist automática (Sprint 10): {', '.join(to_blacklist)}")
            params["blacklist"] = to_blacklist

        # 1. Análise de vitória
        if win_rate < 30:
            suggestions.append(f"⚠️ Win rate baixa ({win_rate:.1f}%). Considere aumentar os filtros (ex: min_rsi_5m para 60, cvd_streak_min para 4).")
            params["signal"]["min_rsi_5m"] = 60.0  # type: ignore[index]
            params["signal"]["cvd_streak_min"] = 4  # type: ignore[index]
        elif win_rate > 60:
            suggestions.append(f"✅ Win rate excelente ({win_rate:.1f}%). Você pode tentar relaxar alguns filtros para capturar mais sinais.")

        # 2. Análise de exp nas vitórias vs derrotas
        if wins and losses:
            avg_exp_wins = sum(t.get("entry", {}).get("signal", {}).get("exp", 0) for t in wins) / len(wins)
            avg_exp_losses = sum(t.get("entry", {}).get("signal", {}).get("exp", 0) for t in losses) / len(losses)
            
            if avg_exp_wins > avg_exp_losses * 1.5:
                new_min_exp = round(max(0.5, avg_exp_losses * 1.2), 2)
                suggestions.append(f"💡 Trades vencedores tem exp médio ({avg_exp_wins:.2f}) muito maior que derrotas ({avg_exp_losses:.2f}). Aumente min_exp para {new_min_exp}.")
                params["signal"]["min_exp"] = new_min_exp  # type: ignore[index]

        # 3. Análise de RSI
        if wins and losses:
            def _rsi_5m(trade: Dict[str, Any]) -> float:
                metrics = trade.get("entry", {}).get("metrics", {}) or {}
                raw = metrics.get("rsi_5m", 50)
                if raw is None:
                    return 50.0
                try:
                    return float(raw)
                except Exception:
                    return 50.0

            avg_rsi_wins = sum(_rsi_5m(t) for t in wins) / len(wins)
            avg_rsi_losses = sum(_rsi_5m(t) for t in losses) / len(losses)
            
            if avg_rsi_wins > avg_rsi_losses + 5:
                new_rsi = round(max(50.0, avg_rsi_losses + 3.0), 1)
                suggestions.append(f"💡 Trades vencedores tem RSI médio ({avg_rsi_wins:.1f}) maior que derrotas ({avg_rsi_losses:.1f}). Aumente min_rsi_5m para {new_rsi}.")
                params["signal"]["min_rsi_5m"] = new_rsi  # type: ignore[index]

        # 4. Análise de CVD streak
        if wins and losses:
            avg_trades_wins = sum(t.get("entry", {}).get("metrics", {}).get("trades_1m", 0) for t in wins) / len(wins)
            avg_trades_losses = sum(t.get("entry", {}).get("metrics", {}).get("trades_1m", 0) for t in losses) / len(losses)
            
            if avg_trades_wins > avg_trades_losses * 2:
                new_trades = max(5, int(avg_trades_losses * 1.5))
                suggestions.append(f"💡 Trades vencedores tem mais trades/min ({avg_trades_wins:.0f}) que derrotas ({avg_trades_losses:.0f}). Aumente min_trades_1m para {new_trades}.")
                params["signal"]["min_trades_1m"] = new_trades  # type: ignore[index]

        # 5. Análise de MAE (Maximum Adverse Excursion)
        if closed_trades:
            high_mae_trades = [t for t in closed_trades if t.get("live", {}).get("mae_pct", 0) > 3]
            if len(high_mae_trades) > len(closed_trades) * 0.3:
                suggestions.append(f"⚠️ Muitos trades ({len(high_mae_trades)}/{len(closed_trades)}) tem MAE > 3%. Considere reduzir o SL um pouco (ex: sl_pct de 0.02 para 0.018).")
                params["execution"]["sl_pct"] = 0.018  # type: ignore[index]

        # 6. Análise de MFE (Maximum Favorable Excursion)
        if closed_trades:
            high_mfe_trades = [t for t in closed_trades if t.get("live", {}).get("mfe_pct", 0) > 5]
            if len(high_mfe_trades) > len(closed_trades) * 0.2:
                suggestions.append(f"💡 Muitos trades ({len(high_mfe_trades)}/{len(closed_trades)}) tem MFE > 5%. Considere aumentar o TP um pouco (ex: tp_pct de 0.04 para 0.05) para capturar mais lucro.")
                params["execution"]["tp_pct"] = 0.05  # type: ignore[index]

        if not suggestions:
            suggestions.append("✅ Nenhum ajuste crítico necessário no momento. Continue coletando mais dados.")

        # Limpar dicionários vazios
        final_params = {k: v for k, v in params.items() if v}

        return suggestions, final_params, win_rate_per_sym

    def run_analysis(self) -> Optional[AnalysisResult]:
        """Executa a análise completa e retorna o resultado."""
        closed_trades = self.load_trades()
        
        if len(closed_trades) < 10:
            logger.info("Ainda não há trades suficientes para análise (fechados: %d).", len(closed_trades))
            return None

        if len(closed_trades) == self.last_analysis_trades:
            logger.debug("Nenhum novo trade fechado desde a última análise.")
            return None

        self.last_analysis_trades = len(closed_trades)
        result = self.analyze_trades(closed_trades)

        # Gate F-05: só aplica calibração com amostra suficiente
        if result.total_trades < self.min_trades_for_calibration:
            result.parameter_changes = {}
            logger.info(
                "📊 [ANALYZER] Análise gerada mas calibração bloqueada — %d trades (mínimo: %d). "
                "Coletando dados sem alterar preferences.json.",
                result.total_trades,
                self.min_trades_for_calibration,
            )

        # Loga o resultado
        logger.info("=" * 60)
        logger.info("ANÁLISE DE PERFORMANCE DO PAPER TRADER")
        logger.info("=" * 60)
        logger.info(f"Total de trades fechados: {result.total_trades}")
        logger.info(f"Win rate: {result.win_rate:.1f}%")
        logger.info(f"Avg PnL: {result.avg_pnl:.2f}%")
        logger.info(f"Avg MFE: {result.avg_mfe:.2f}%")
        logger.info(f"Avg MAE: {result.avg_mae:.2f}%")
        logger.info("-" * 60)
        logger.info("SUGESTÕES:")
        for i, suggestion in enumerate(result.suggestions, 1):
            logger.info(f"  {i}. {suggestion}")
        logger.info("=" * 60)

        # Salvar sugestões estruturadas em JSON
        if result.parameter_changes:
            try:
                suggested_path = Path("preferences.suggested.json")
                suggested_path.write_text(json.dumps(result.parameter_changes, indent=2), encoding="utf-8")
                logger.info("📁 Arquivo preferences.suggested.json atualizado com novas configurações.")
            except Exception as e:
                logger.error("Erro ao salvar preferences.suggested.json: %s", e)

        return result
