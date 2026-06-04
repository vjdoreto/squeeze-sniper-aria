from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

class Dashboard:
    def __init__(self):
        self.console = Console()

    def create_table(self, market_data):
        table = Table(
            title=f"🚀 SqueezeSniper-V4 | {datetime.now().strftime('%H:%M:%S')}",
            box=box.DOUBLE_EDGE,
            header_style="bold cyan"
        )

        table.add_column("Símbolo", justify="left", style="bold white")
        table.add_column("Preço", justify="right")
        table.add_column("exp_btc", justify="right")
        table.add_column("exp", justify="right")
        table.add_column("OI(5m)", justify="right")
        table.add_column("oi_trend", justify="right")
        table.add_column("LSR", justify="right")
        table.add_column("lsr_trend", justify="right")
        table.add_column("TRADES(1m)", justify="right")
        table.add_column("CVD/1min", justify="right")
        table.add_column("Status", justify="center")

        active_symbols = []
        for symbol, d in market_data.items():
            if d.get("price") and d.get("oi", 0) > 0:
                oi_trend = d.get("oi_trend:5m", 0)
                active_symbols.append((symbol, d, oi_trend))

        active_symbols.sort(key=lambda x: x[2] if x[2] else 0, reverse=True)

        for symbol, d, oi_trend in active_symbols[:25]:
            exp = d.get("exp:5m", 0)
            exp_btc = d.get("exp_btc:5m")
            lsr_trend = d.get("lsr_trend:5m")
            lsr_raw = d.get("lsr")
            cvd = d.get("volume_delta_1min", 0)
            trades_1m = d.get("trades_count_1min", 0)

            # Helper para Vivacidade das Células (Heatmap)
            def heatmap(val, threshold=1.0, invert=False):
                if val is None: return "—"
                v = val * (-1 if invert else 1)
                if v > threshold * 3: style = "bold white on green"
                elif v > threshold: style = "black on green"
                elif v > 0: style = "green"
                elif v < -threshold * 3: style = "bold white on red"
                elif v < -threshold: style = "black on red"
                else: style = "red"
                return f"[{style}]{val:+.2f}[/]"

            price = d.get("price") or 0
            oi_coin = d.get("oi", 0) or 0
            oi_notional_m = (oi_coin * price) / 1e6 if price and oi_coin else None
            oi_str = "—" if oi_notional_m is None else f"{oi_notional_m:.2f}M"

            status = "[white]Monitorando..."
            
            # Squeeze conditions (DNA Sniper)
            if exp > 0.5 and oi_trend > 0.1 and lsr_trend is not None and lsr_trend < -0.05:
                status = "[bold blink yellow]🔥 SQUEEZE!"
            elif exp > 0 and oi_trend > 0:
                status = "[green]🚀 Potencial"
            
            exp_btc_str = heatmap(exp_btc, threshold=1.0)
            exp_str = heatmap(exp, threshold=1.5)

            oi_arrow = "↑" if oi_trend > 0 else ("↓" if oi_trend < 0 else "→")
            oi_trend_str = f"{heatmap(oi_trend, threshold=0.5)} {oi_arrow}"

            # DNA LSR Visual: Fundo colorido baseado na saúde (LSR < 1 é combustível para LONG)
            if lsr_raw is None:
                lsr_raw_str = "—"
            else:
                # Forçamos a conversão para float para silenciar o Pylance e garantir comparação segura
                lsr_val_f = float(lsr_raw)
                lsr_tag = "bold white on green" if lsr_val_f < 0.8 else ("black on green" if lsr_val_f < 1.0 else ("bold white on red" if lsr_val_f > 1.5 else "red"))
                lsr_raw_str = f"[{lsr_tag}]{lsr_val_f:.2f}[/]"
            
            # Proteção contra None no trend para evitar erros de comparação (Optional operand)
            lsr_t_val = lsr_trend if lsr_trend is not None else 0.0
            lsr_arrow = "↓" if lsr_t_val < 0 else ("↑" if lsr_t_val > 0 else "→")
            lsr_trend_str = f"{heatmap(lsr_trend, threshold=0.5, invert=True)} {lsr_arrow}"

            cvd_tag = "bold green" if cvd > 50000 else ("green" if cvd > 0 else ("bold red" if cvd < -50000 else "red"))
            cvd_str = f"[{cvd_tag}]{cvd:,.0f}[/]"

            table.add_row(
                symbol,
                f"{d['price']:,.2f}",
                exp_btc_str,
                exp_str,
                oi_str,
                oi_trend_str,
                lsr_raw_str,
                lsr_trend_str,
                f"{trades_1m:,.0f}",
                cvd_str,
                status
            )

        return table

    def render(self, market_data):
        return Panel(
            self.create_table(market_data),
            title="[bold green]Rastro Institucional Monitor[/]",
            border_style="bright_blue"
        )
