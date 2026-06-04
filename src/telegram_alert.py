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

    async def send_hourly_report(self, snap: Dict[str, Any]) -> None:
        """Relatório consolidado de saúde da banca e sentimento do mercado."""
        stats = snap.get("stats", {})
        text = (
            f"📊 <b>RELATÓRIO HORÁRIO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 <b>Equity:</b> ${snap.get('current_capital', 0):.2f} USDT\n"
            f"📈 <b>Win Rate:</b> {stats.get('win_rate_pct', 0)}%\n"
            f"🔄 <b>Trades:</b> {stats.get('wins')}W | {stats.get('losses')}L\n"
            f"🌡️ <b>Squeezometer:</b> {snap.get('market_squeeze_level', 0):.0f}/100"
        )
        await self._send(text)

    async def send_daily_report(self, snap: Dict[str, Any]) -> None:
        """Relatório diário consolidado com métricas de performance e sentimento."""
        stats = snap.get("stats", {})
        text = (
            f"📊 <b>RELATÓRIO DIÁRIO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 <b>Equity:</b> ${snap.get('current_capital', 0):.2f} USDT\n"
            f"📈 <b>Win Rate:</b> {stats.get('win_rate_pct', 0)}%\n"
            f"🔄 <b>Trades:</b> {stats.get('wins')}W | {stats.get('losses')}L\n"
            f"🌡️ <b>Squeezometer:</b> {snap.get('market_squeeze_level', 0):.0f}/100\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Peak Equity:</b> ${snap.get('peak_capital', 0):.2f} USDT\n"
            f"📉 <b>Drawdown:</b> {stats.get('max_drawdown_pct', 0):.2f}%\n"
            f"⏱️ <b>Uptime:</b> {snap.get('uptime_sec', 0) // 3600}h"
        )
        await self._send(text)

    async def panic_warning(self, level: float) -> None:
        """Alerta crítico de ignição institucional global."""
        text = f"🚨 <b>ALERTA DE VOLATILIDADE</b>\nSqueezometer em {level:.0f}/100! Atividade institucional extrema detectada."
        await self._send(text)
