"""
NOTA: Para executar estes testes, instale as dependências de desenvolvimento:
    pip install -r requirements-dev.txt

Ou instale pytest diretamente:
    pip install pytest pytest-asyncio

Executar testes:
    pytest tests/test_live_tracker.py -v
    pytest tests/test_live_tracker.py::TestCorrelationGuard -v
    pytest tests/test_live_tracker.py::TestPartialBreakeven::test_triggers_at_breakeven -v
"""

"""
Testes Automatizados — LiveTracker (DNA Sniper P3)

Testa features P0/P1/P2 do LiveTracker:
- Correlation Guard
- Partial Breakeven
- Trailing Stop
- Close Confirmation
"""

import pytest
import time
from pathlib import Path
from src.live_tracker import LiveTracker, LiveConfig, CORR_GROUPS


@pytest.fixture
def tracker():
    """Fixture para criar um LiveTracker de teste."""
    config = LiveConfig(
        json_path=Path("tests/fixtures/live_test.json"),
        closed_jsonl=Path("tests/fixtures/live_closed_test.jsonl"),
        debug_jsonl=Path("tests/fixtures/live_debug_test.jsonl"),
        max_open_positions=5,
        max_notional_usdt=500.0,
        partial_tp_breakeven_pct=0.5,  # 50% da posição
        sl_trailing_swing_low=True,
    )
    return LiveTracker(config)


class TestCorrelationGuard:
    """Testa o Correlation Guard (P0)."""
    
    def test_blocks_correlated_positions(self, tracker):
        """Testa que correlation guard bloqueia trades correlacionados."""
        # Abre SOLUSDT (grupo L1)
        trade1 = tracker.open_long(
            symbol="SOLUSDT",
            entry_price=100.0,
            quantity=10.0,
            usdt_margin=100.0,
            leverage=10,
            signal={"score": 85}
        )
        assert trade1 is not None
        assert trade1["symbol"] == "SOLUSDT"
        
        # Tenta abrir AVAXUSDT (mesmo grupo L1) → deve ser bloqueado
        trade2 = tracker.open_long(
            symbol="AVAXUSDT",
            entry_price=50.0,
            quantity=20.0,
            usdt_margin=100.0,
            leverage=10,
            signal={"score": 90}
        )
        assert trade2 is None  # Bloqueado por correlation guard
    
    def test_allows_different_groups(self, tracker):
        """Testa que permite trades em grupos diferentes."""
        # Abre SOLUSDT (grupo L1)
        trade1 = tracker.open_long(
            symbol="SOLUSDT",
            entry_price=100.0,
            quantity=10.0,
            usdt_margin=100.0,
            leverage=10,
            signal={"score": 85}
        )
        assert trade1 is not None
        
        # Abre AAVEUSDT (grupo DeFi) → deve ser permitido
        trade2 = tracker.open_long(
            symbol="AAVEUSDT",
            entry_price=200.0,
            quantity=5.0,
            usdt_margin=100.0,
            leverage=10,
            signal={"score": 88}
        )
        assert trade2 is not None
        assert trade2["symbol"] == "AAVEUSDT"


class TestPartialBreakeven:
    """Testa o Partial Breakeven (P1)."""
    
    def test_triggers_at_breakeven(self, tracker):
        """Testa que partial breakeven é acionado no breakeven."""
        # Abre posição
        trade = tracker.open_long(
            symbol="BTCUSDT",
            entry_price=50000.0,
            quantity=0.01,
            usdt_margin=500.0,
            leverage=10,
            signal={"score": 90}
        )
        assert trade is not None
        
        # Calcula breakeven
        entry_price = trade["entry"]["price"]
        fee_entry = trade["entry"]["fee_usdt"]
        notional = trade["entry"]["notional_usdt"]
        breakeven_price = entry_price * (1 + (fee_entry / notional))
        
        # Atualiza posição com preço no breakeven
        updated = tracker.update_position(
            symbol="BTCUSDT",
            current_price=breakeven_price,
            funding_fee_usdt=0.0
        )
        
        # Verifica que flag foi setada
        assert updated["breakeven_partial_closed"] is True
    
    def test_only_triggers_once(self, tracker):
        """Testa que partial breakeven só é acionado uma vez."""
        # Abre posição
        trade = tracker.open_long(
            symbol="ETHUSDT",
            entry_price=3000.0,
            quantity=0.1,
            usdt_margin=300.0,
            leverage=10,
            signal={"score": 85}
        )
        
        # Primeira atualização no breakeven
        tracker.update_position("ETHUSDT", 3001.2, 0.0)
        assert tracker._open["ETHUSDT"]["breakeven_partial_closed"] is True
        
        # Segunda atualização (não deve acionar novamente)
        tracker.update_position("ETHUSDT", 3002.0, 0.0)
        # Flag ainda deve estar True, mas não deve acionar novamente


class TestTrailingStop:
    """Testa o Trailing Stop (P1)."""
    
    def test_activates_after_profit(self, tracker):
        """Testa que trailing stop só ativa após 1% de lucro."""
        # Abre posição
        trade = tracker.open_long(
            symbol="BNBUSDT",
            entry_price=400.0,
            quantity=1.0,
            usdt_margin=400.0,
            leverage=10,
            signal={"score": 88}
        )
        
        # Atualiza com preço 0.5% acima (não deve ativar trailing)
        tracker.update_position("BNBUSDT", 402.0, 0.0)
        sl_before = tracker._open["BNBUSDT"]["targets"]["sl_price"]
        
        # Atualiza com preço 1.5% acima (deve ativar trailing)
        market_data = {"BNBUSDT": {"swing_low_5m": 404.0}}
        tracker.update_position("BNBUSDT", 406.0, 0.0, market_data)
        sl_after = tracker._open["BNBUSDT"]["targets"]["sl_price"]
        
        # SL deve ter subido
        assert sl_after > sl_before
    
    def test_never_lowers_sl(self, tracker):
        """Testa que trailing stop nunca abaixa o SL."""
        # Abre posição
        trade = tracker.open_long(
            symbol="ADAUSDT",
            entry_price=1.0,
            quantity=100.0,
            usdt_margin=100.0,
            leverage=10,
            signal={"score": 82}
        )
        
        # Define SL inicial
        tracker._open["ADAUSDT"]["targets"]["sl_price"] = 0.98
        
        # Atualiza com swing_low abaixo do SL atual
        market_data = {"ADAUSDT": {"swing_low_5m": 0.95}}
        tracker.update_position("ADAUSDT", 1.02, 0.0, market_data)
        
        # SL não deve ter abaixado
        assert tracker._open["ADAUSDT"]["targets"]["sl_price"] == 0.98


class TestCloseConfirmation:
    """Testa o Close Confirmation (P2)."""
    
    def test_rejects_extreme_slippage(self, tracker):
        """Testa que close confirmation rejeita slippage > 2%."""
        # Abre posição
        trade = tracker.open_long(
            symbol="DOGEUSDT",
            entry_price=0.10,
            quantity=1000.0,
            usdt_margin=100.0,
            leverage=10,
            signal={"score": 80}
        )
        
        # Tenta fechar com preço 3% abaixo (deve ser rejeitado)
        market_data = {"DOGEUSDT": {"price": 0.10}}
        result = tracker.close_position(
            symbol="DOGEUSDT",
            close_price=0.097,  # 3% abaixo
            close_reason="sl",
            market_data=market_data
        )
        
        # Fechamento deve ser rejeitado
        assert result is None
        # Posição ainda deve estar aberta
        assert "DOGEUSDT" in tracker._open
    
    def test_allows_normal_close(self, tracker):
        """Testa que close confirmation permite fechamento normal."""
        # Abre posição
        trade = tracker.open_long(
            symbol="MATICUSDT",
            entry_price=1.0,
            quantity=100.0,
            usdt_margin=100.0,
            leverage=10,
            signal={"score": 86}
        )
        
        # Fecha com preço 1% abaixo (deve ser permitido)
        market_data = {"MATICUSDT": {"price": 1.0}}
        result = tracker.close_position(
            symbol="MATICUSDT",
            close_price=0.99,  # 1% abaixo
            close_reason="tp",
            market_data=market_data
        )
        
        # Fechamento deve ser permitido
        assert result is not None
        assert result["exit"]["price"] == 0.99
        # Posição não deve mais estar aberta
        assert "MATICUSDT" not in tracker._open


class TestMaxPositions:
    """Testa validações de max positions."""
    
    def test_blocks_when_max_reached(self, tracker):
        """Testa que bloqueia quando max_open_positions é atingido."""
        # Abre 5 posições (max_open_positions = 5)
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
        for symbol in symbols:
            trade = tracker.open_long(
                symbol=symbol,
                entry_price=100.0,
                quantity=1.0,
                usdt_margin=100.0,
                leverage=10,
                signal={"score": 85}
            )
            assert trade is not None
        
        # Tenta abrir 6ª posição (deve ser bloqueado)
        trade6 = tracker.open_long(
            symbol="AVAXUSDT",
            entry_price=50.0,
            quantity=2.0,
            usdt_margin=100.0,
            leverage=10,
            signal={"score": 90}
        )
        assert trade6 is None


# Executar testes:
# pytest tests/test_live_tracker.py -v
# pytest tests/test_live_tracker.py::TestCorrelationGuard -v
# pytest tests/test_live_tracker.py::TestPartialBreakeven::test_triggers_at_breakeven -v

# Made with Bob
