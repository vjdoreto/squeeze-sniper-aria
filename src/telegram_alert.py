import aiohttp
import logging
import ssl
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("TelegramAlert")

class TelegramAlert:
    """
    Motor de alertas Telegram enriquecido para o SqueezeSniper V4.
    Focado em transparência de dados (DNA Sniper) e auditoria visual rápida.
    """
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)
        self.base_url = f"https://api.telegram.org/bot{token}"

    async def _send(self, text: str) -> bool:
        if not self.enabled:
            return False
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            # P0.1 FIX: SSL context para resolver certificate verification error
            # Cria SSL context que aceita certificados (necessário para Windows com certificados desatualizados)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # SPRINT 11: Timeout de segurança para não travar o loop de trading principal
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8.0)) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        logger.error(f"Telegram API Error: {txt}")
                        return False
                    logger.info(f"✅ Telegram alert sent successfully")
                    return True
        except Exception as e:
            logger.error(f"Telegram exception: {e}")
            return False

    async def trade_open(self, trade: Dict[str, Any], mode: str = "paper") -> None:
        """Notifica abertura de posição com telemetria completa do DNA institucional."""
        entry = trade.get("entry", {})
        sig = entry.get("signal", {})
        targets = trade.get("targets", {})
        
        emoji = "🟢" if mode == "paper" else "🚀"
        type_str = "PAPER" if mode == "paper" else "LIVE"
        
        def _num(x: Any, default: float = 0.0) -> float:
            try:
                if x is None:
                    return default
                return float(x)
            except Exception:
                return default

        raw_score = sig.get("score")
        score_txt = "—"
        if raw_score is not None:
            try:
                s = float(raw_score)
                if s >= 0:
                    score_txt = f"{int(max(0, min(100, s)))}"
            except Exception:
                score_txt = "—"

        entry_price = _num(entry.get("price"), default=0.0)
        usdt_margin = _num(entry.get("usdt_margin", 0), default=0.0)
        leverage = _num(entry.get("leverage", 0), default=0.0)
        fee_in = _num(entry.get("fee_usdt", 0), default=0.0)
        qty = _num(entry.get("initial_quantity", 0), default=0.0)

        exp = _num(sig.get("exp", 0), default=0.0)
        oi_tr = _num(sig.get("oi_trend", 0), default=0.0)
        exp_btc = _num(sig.get("exp_btc", 0), default=0.0)
        trades_1m = sig.get("trades_1m", 0) or 0
        lsr_tr = _num(sig.get("lsr_trend", 0), default=0.0)
        lsr_chg_pct = _num(sig.get("lsr_change_pct", 0), default=0.0)

        sl_price = _num(targets.get("sl_price", 0), default=0.0)
        tp_price = _num(targets.get("tp_price", 0), default=0.0)

        text = (
            f"<b>{emoji} {type_str} OPEN: {trade['symbol']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Preço:</b> <code>{entry_price:.4f}</code>\n"
            f"💵 <b>Margem:</b> ${usdt_margin:.2f} ({leverage:g}x)\n"
            f"🏷️ <b>Sim Fee In:</b> ${fee_in:.4f}\n"
            f"📦 <b>Qtd:</b> {qty:.4f}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Score:</b> {score_txt}/100\n"
            f"🧬 <b>DNA:</b> EXP={exp:.4f} | OI_tr={oi_tr:.4f}\n"
            f"📈 <b>BTC_rel:</b> {exp_btc:.4f} | 📊 <b>Tr/1m:</b> {trades_1m}\n"
            f"📉 <b>LSR_tr:</b> {lsr_tr:.4f} | 📉 <b>LSR_chg:</b> {lsr_chg_pct:.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"� <b>SL:</b> <code>{sl_price:.4f}</code>\n"
            f"🎯 <b>TP:</b> <code>{tp_price:.4f}</code>\n"
            f"🆔 <code>{trade.get('id')}</code>"
        )
        await self._send(text)

    async def trade_close(self, trade: Dict[str, Any], mode: str = "paper") -> None:
        """Notifica fechamento com PnL líquido e auditoria de performance técnica."""
        entry = trade.get("entry", {})
        exit_ = trade.get("exit", {})
        qual = trade.get("quality", {})
        
        pnl_pct = exit_.get("pnl_pct", 0)
        pnl_usdt = exit_.get("pnl_usdt", 0)
        
        emoji = "✅" if pnl_pct >= 0 else "❌"
        type_str = "PAPER" if mode == "paper" else "LIVE"
        
        duration_sec = int(exit_.get("time", time.time()) - entry.get("time", time.time()))
        duration_str = f"{duration_sec // 60}m {duration_sec % 60}s"
        
        total_fees = entry.get('fee_usdt', 0) + exit_.get('fee_usdt', 0)

        text = (
            f"<b>{emoji} {type_str} CLOSE: {trade['symbol']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>PnL:</b> <b>{pnl_pct:+.2f}%</b> (${pnl_usdt:+.2f} USDT)\n"
            f"🏷️ <b>Total Fees:</b> ${total_fees:.4f}\n"
            f"🔄 <b>Preços:</b> {entry.get('price', 0):.4f} → {exit_.get('price', 0):.4f}\n"
            f"🚪 <b>Motivo:</b> <code>{exit_.get('reason', 'unknown')}</code>\n"
            f"🕒 <b>Duração:</b> {duration_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Qualidade:</b> {qual.get('entry_assertiveness', 'mixed').upper()}\n"
            f"�🔥 <b>MFE:</b> {qual.get('mfe_pct', 0):.2f}% | 🧊 <b>MAE:</b> {qual.get('mae_pct', 0):.2f}%\n"
            f"🆔 <code>{trade.get('id')}</code>"
        )
        await self._send(text)

    async def bot_startup(self, mode: str, capital: float, min_score: float, warmup_sec: int) -> None:
        """Notifica que o bot inicializou e entrou em warmup."""
        mode_str = "PAPER 📄" if mode == "paper" else "🚀 LIVE"
        text = (
            f"🟡 <b>SQUEEZE SNIPER — ONLINE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ <b>Modo:</b> {mode_str}\n"
            f"🏦 <b>Capital:</b> ${capital:.2f} USDT\n"
            f"🎯 <b>Score mínimo:</b> {min_score}/100\n"
            f"⏳ <b>Warmup:</b> {warmup_sec}s em andamento...\n"
            f"<i>Gatilho bloqueado até aquecimento completo.</i>"
        )
        await self._send(text)

    async def warmup_complete(self) -> None:
        """Notifica que o warmup de 300s foi concluído e o gatilho está liberado."""
        text = (
            f"✅ <b>GATILHO LIBERADO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Warmup de 300s concluído.\n"
            f"Bot operacional — aguardando squeeze."
        )
        await self._send(text)

    async def bot_shutdown(self, reason: str, snap: Optional[Dict[str, Any]] = None) -> None:
        """Notifica encerramento do bot com resumo da sessão."""
        text = f"🔴 <b>SQUEEZE SNIPER — OFFLINE</b>\n━━━━━━━━━━━━━━━━━━━━\n⚠️ <b>Motivo:</b> {reason}"
        if snap:
            stats = snap.get("stats", {})
            wins = stats.get("wins", 0) or 0
            losses = stats.get("losses", 0) or 0
            total = wins + losses
            wr = stats.get("win_rate_pct", 0) or 0
            capital = snap.get("current_capital", 0) or 0
            uptime_h = (snap.get("uptime_sec", 0) or 0) // 3600
            uptime_m = ((snap.get("uptime_sec", 0) or 0) % 3600) // 60
            if total > 0:
                text += (
                    f"\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"📊 <b>Sessão:</b> {wins}W / {losses}L ({wr}% WR)\n"
                    f"🏦 <b>Equity final:</b> ${capital:.2f}\n"
                    f"⏱️ <b>Uptime:</b> {uptime_h}h {uptime_m}m"
                )
            else:
                text += f"\n<i>Sem trades nesta sessão. Uptime: {uptime_h}h {uptime_m}m</i>"
        await self._send(text)

    async def drawdown_circuit_breaker(self, dd_pct: float, capital: float) -> None:
        """Alerta crítico: DrawdownManager pausou o trading."""
        text = (
            f"🚨 <b>CIRCUIT BREAKER ATIVADO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📉 <b>Drawdown:</b> {dd_pct:.1f}% (limite: 15%)\n"
            f"🏦 <b>Capital atual:</b> ${capital:.2f}\n"
            f"⛔ <b>Trading pausado.</b> Requer reset manual."
        )
        await self._send(text)

    async def send_hourly_report(self, snap: Dict[str, Any]) -> None:
        """Relatório horário: stats cumulativos da sessão + trades da última hora."""
        stats = snap.get("stats", {})
        wins = stats.get("wins", 0) or 0
        losses = stats.get("losses", 0) or 0
        total = wins + losses
        wr = stats.get("win_rate_pct", 0) or 0
        capital = snap.get("current_capital", 0) or 0
        peak = snap.get("peak_capital", 0) or 0
        dd = stats.get("max_drawdown_pct", 0) or 0
        squeeze = snap.get("market_squeeze_level", 0) or 0

        pnl_session = capital - (snap.get("initial_capital", capital) or capital)
        pnl_sign = "+" if pnl_session >= 0 else ""

        text = (
            f"📊 <b>RELATÓRIO HORÁRIO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 <b>Equity:</b> ${capital:.2f} · Peak: ${peak:.2f}\n"
            f"💰 <b>PnL sessão:</b> {pnl_sign}{pnl_session:.2f} USDT\n"
            f"📉 <b>Drawdown:</b> {dd:.2f}%\n"
            f"🔄 <b>Trades (total sessão):</b> {wins}W / {losses}L"
        )
        if total > 0:
            text += f" · {wr}% WR"
        text += f"\n🌡️ <b>Squeezometer:</b> {squeeze:.0f}/100"

        trades_1h = snap.get("trades_1h") or []
        if trades_1h:
            text += f"\n━━━━━━━━━━━━━━━━━━━━\n📋 <b>Última hora ({len(trades_1h)} trade{'s' if len(trades_1h) != 1 else ''}):</b>"
            def _fmt(p: float) -> str:
                if p == 0:
                    return "—"
                return f"{p:.8f}".rstrip("0").rstrip(".")
            for t in trades_1h[-10:]:  # máx 10 para não estourar o limite do Telegram
                entry = t.get("entry", {})
                exit_ = t.get("exit", {})
                symbol = t.get("symbol", "?").replace("USDT", "")
                pnl = exit_.get("pnl_pct", 0) or 0
                reason = exit_.get("reason", "?")
                mark = "✅" if pnl >= 0 else "❌"
                text += f"\n{mark} <code>{symbol:<8} {pnl:+.2f}%  [{reason}]</code>"
        else:
            text += "\n<i>Sem trades na última hora.</i>"
        await self._send(text)

    async def send_daily_report(self, snap: Dict[str, Any]) -> None:
        """Relatório diário completo: performance + qualidade + destaques."""
        stats = snap.get("stats", {})
        wins = stats.get("wins", 0) or 0
        losses = stats.get("losses", 0) or 0
        total = wins + losses
        wr = stats.get("win_rate_pct", 0) or 0
        capital = snap.get("current_capital", 0) or 0
        peak = snap.get("peak_capital", 0) or 0
        dd = stats.get("max_drawdown_pct", 0) or 0
        uptime_h = (snap.get("uptime_sec", 0) or 0) // 3600
        pnl_session = capital - (snap.get("initial_capital", capital) or capital)
        pnl_sign = "+" if pnl_session >= 0 else ""

        # Profit Factor
        gross_win = stats.get("gross_profit", 0) or 0
        gross_loss = abs(stats.get("gross_loss", 0) or 0)
        pf_str = f"{gross_win / gross_loss:.2f}" if gross_loss > 0 else "∞" if gross_win > 0 else "—"

        # Avg MFE / MAE
        avg_mfe = stats.get("avg_mfe_pct", 0) or 0
        avg_mae = stats.get("avg_mae_pct", 0) or 0

        text = (
            f"📅 <b>RELATÓRIO DIÁRIO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 <b>Equity:</b> ${capital:.2f} · Peak: ${peak:.2f}\n"
            f"💰 <b>PnL sessão:</b> {pnl_sign}{pnl_session:.2f} USDT\n"
            f"📉 <b>Max Drawdown:</b> {dd:.2f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔄 <b>Trades:</b> {wins}W / {losses}L ({total} total)"
        )
        if total > 0:
            text += (
                f"\n📈 <b>Win Rate:</b> {wr}%\n"
                f"⚖️ <b>Profit Factor:</b> {pf_str}\n"
                f"🔥 <b>MFE médio:</b> {avg_mfe:.2f}% · 🧊 <b>MAE médio:</b> {avg_mae:.2f}%"
            )
        else:
            text += "\n<i>Sem trades nesta sessão.</i>"

        # Melhor e pior trade
        best = snap.get("best_trade")
        worst = snap.get("worst_trade")
        if best or worst:
            text += "\n━━━━━━━━━━━━━━━━━━━━"
            if best:
                b_sym = best.get("symbol", "?").replace("USDT", "")
                b_pnl = (best.get("exit") or {}).get("pnl_pct", 0) or 0
                text += f"\n🏆 <b>Melhor:</b> {b_sym} <code>{b_pnl:+.2f}%</code>"
            if worst:
                w_sym = worst.get("symbol", "?").replace("USDT", "")
                w_pnl = (worst.get("exit") or {}).get("pnl_pct", 0) or 0
                text += f"\n💀 <b>Pior:</b> {w_sym} <code>{w_pnl:+.2f}%</code>"

        text += f"\n━━━━━━━━━━━━━━━━━━━━\n⏱️ <b>Uptime:</b> {uptime_h}h"
        await self._send(text)

    async def mode_change(self, new_mode: str) -> None:
        """Notifica troca de modo paper ↔ live via Dashboard."""
        if new_mode == "live":
            text = (
                f"🚀 <b>MODO ALTERADO → LIVE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ Bot operando com capital real.\n"
                f"<i>Ordens serão executadas na Binance.</i>"
            )
        else:
            text = (
                f"📄 <b>MODO ALTERADO → PAPER</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Simulação ativa — sem ordens reais."
            )
        await self._send(text)

    async def paper_reset(self, snap: Optional[Dict[str, Any]] = None) -> None:
        """Notifica que o paper reset foi executado via Dashboard."""
        stats = (snap or {}).get("stats", {}) or {}
        wins = stats.get("wins", 0) or 0
        losses = stats.get("losses", 0) or 0
        total = wins + losses
        capital = (snap or {}).get("current_capital", 0) or 0
        wr = stats.get("win_rate_pct", 0) or 0
        text = (
            f"🔄 <b>PAPER RESET</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Sessão encerrada:</b> {wins}W / {losses}L ({total} trades)"
        )
        if total > 0:
            text += f" · {wr}% WR"
        text += (
            f"\n🏦 <b>Capital final:</b> ${capital:.2f}"
            f"\n<i>Estado paper limpo — novo ciclo iniciado.</i>"
        )
        await self._send(text)

    async def hard_reset(self, deep_clean: bool = False, snap: Optional[Dict[str, Any]] = None) -> None:
        """Notifica que o hard reset foi executado via Dashboard."""
        capital = (snap or {}).get("current_capital", 0) or 0
        stats = (snap or {}).get("stats", {}) or {}
        wins = stats.get("wins", 0) or 0
        losses = stats.get("losses", 0) or 0
        total = wins + losses
        clean_txt = " + DEEP CLEAN" if deep_clean else ""
        text = (
            f"🔥 <b>HARD RESET{clean_txt}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Sessão encerrada:</b> {wins}W / {losses}L ({total} trades)\n"
            f"🏦 <b>Capital final:</b> ${capital:.2f}\n"
            f"⏳ <b>Warmup:</b> 300s reiniciado.\n"
            f"<i>Sistema em estado puro — aguardando squeeze.</i>"
        )
        await self._send(text)

    async def market_warming(self, level: float) -> None:
        """Alerta leve: Squeezometer ≥ 70 — mercado aquecendo."""
        text = (
            f"🟡 <b>MERCADO AQUECENDO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌡️ Squeezometer: <b>{level:.0f}/100</b>\n"
            f"Atividade institucional acima da média."
        )
        await self._send(text)

    async def panic_warning(self, level: float) -> None:
        """Alerta crítico: Squeezometer ≥ 85 — pânico institucional iminente."""
        text = (
            f"🚨 <b>SQUEEZOMETER CRÍTICO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌡️ Nível: <b>{level:.0f}/100</b>\n"
            f"Pânico institucional — squeeze pode disparar agora."
        )
        await self._send(text)
