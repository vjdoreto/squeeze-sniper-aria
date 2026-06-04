# 🔧 Harmonização de Preferências - SqueezeSniper V4

**Data**: 2026-06-02  
**Versão**: 4.1.1  
**Objetivo**: Eliminar duplicidade e ambiguidade na estrutura de configurações

---

## 🔍 Problema Identificado

### **Duplicidade Crítica**
O arquivo `preferences.json` continha **blocos duplicados** que criavam ambiguidade:

```json
{
    "paper": {
        "signal": {
            "min_rsi_5m": 65.0,  // ← Definido aqui
            "cvd_streak_min": 4,
            // ...
        }
    },
    "live": {
        "signal": {
            "min_rsi_5m": 70.0,  // ← Definido aqui
            "cvd_streak_min": 4,
            // ...
        }
    },
    "signal": {  // ← DUPLICIDADE! Bloco global conflitante
        "min_rsi_5m": 65.0,
        "cvd_streak_min": 4,
        // ...
    }
}
```

### **Impacto**
- ❌ **Ambiguidade**: Qual valor usar? Global ou específico do modo?
- ❌ **Conflito de Leitura**: `config.py` usa fallback `prefs.get("signal")` que pode sobrescrever valores específicos
- ❌ **Manutenção Difícil**: Mudanças precisam ser feitas em 3 lugares
- ❌ **Risco de Inconsistência**: Paper e Live podem ficar desalinhados

---

## ✅ Solução Implementada

### **1. Remoção de Blocos Globais Duplicados**

**ANTES** (preferences.json linhas 92-103):
```json
{
    "paper": { "signal": {...} },
    "live": { "signal": {...} },
    "signal": {  // ← REMOVIDO
        "min_rsi_5m": 65.0,
        "cvd_streak_min": 4,
        "min_exp": 0.04,
        "min_trades_1m": 2,
        "max_bid_ask_spread": 0.2,
        "min_vol_adaptive_ratio": 0.7,
        "min_oi_accel": 0.0
    },
    "execution": {  // ← REMOVIDO
        "tp_pct": 0.15
    }
}
```

**DEPOIS**:
```json
{
    "paper": {
        "signal": {
            "min_rsi_5m": 65.0,  // ← Único lugar
            "cvd_streak_min": 4,
            "min_exp": 0.04,
            "min_trades_1m": 2,
            "max_bid_ask_spread": 0.2,
            "min_vol_adaptive_ratio": 0.7,
            "min_oi_accel": 0.0,
            // ... outros parâmetros
        }
    },
    "live": {
        "signal": {
            "min_rsi_5m": 70.0,  // ← Único lugar (mais rigoroso)
            "cvd_streak_min": 4,
            "min_exp": 0.05,
            "min_trades_1m": 5,
            "max_bid_ask_spread": 0.15,
            "min_vol_adaptive_ratio": 0.7,
            "min_oi_accel": 0.0,
            // ... outros parâmetros
        }
    }
}
```

### **2. Parâmetros Movidos para Blocos Específicos**

Parâmetros que estavam no bloco global foram **distribuídos** para `paper.signal` e `live.signal`:

| Parâmetro | Paper | Live | Razão da Diferença |
|-----------|-------|------|-------------------|
| `min_rsi_5m` | 65.0 | 70.0 | Live exige RSI mais forte |
| `max_bid_ask_spread` | 0.2% | 0.15% | Live exige liquidez maior |
| `cvd_streak_min` | 4 | 4 | Igual (consistência) |
| `min_oi_accel` | 0.0 | 0.0 | Igual (desabilitado) |
| `min_vol_adaptive_ratio` | 0.7 | 0.7 | Igual (70% do volume 24h) |

---

## 📊 Estrutura Final Harmonizada

### **Hierarquia Clara**
```
preferences.json
├── trading_mode: "paper" | "live"
├── top_n: 100
├── oi_poll_seconds: 10
├── fit_score_min: 20
├── dashboard: {...}
├── logging: {...}
├── paper:
│   ├── enabled: true
│   ├── max_open_positions: 20
│   ├── signal:  ← TODOS os parâmetros de sinal aqui
│   │   ├── min_exp: 0.04
│   │   ├── min_rsi_5m: 65.0
│   │   ├── max_bid_ask_spread: 0.2
│   │   └── ... (12 parâmetros)
│   └── execution:  ← TODOS os parâmetros de execução aqui
│       ├── sl_pct: 0.05
│       ├── tp_pct: 0.15
│       └── ... (8 parâmetros)
└── live:
    ├── usdt_amount: 0.05
    ├── max_open_positions: 3
    ├── signal:  ← TODOS os parâmetros de sinal aqui
    │   ├── min_exp: 0.05
    │   ├── min_rsi_5m: 70.0
    │   ├── max_bid_ask_spread: 0.15
    │   └── ... (12 parâmetros)
    └── execution:  ← TODOS os parâmetros de execução aqui
        ├── sl_pct: 0.05
        ├── tp_pct: 0.15
        └── ... (8 parâmetros)
```

### **Sem Blocos Globais Duplicados**
- ❌ `"signal": {...}` global **REMOVIDO**
- ❌ `"execution": {...}` global **REMOVIDO**
- ✅ Todos os parâmetros estão **dentro** de `paper` ou `live`

---

## 🔄 Compatibilidade com config.py

### **Leitura Hierárquica Mantida**
O `config.py` já usa fallback correto (linhas 25-38):

```python
def get_mode_signal(prefs: Dict[str, Any], mode: ModeName) -> Dict[str, Any]:
    mode_node = get_mode_node(prefs, mode)
    # Prioridade: mode.signal > global signal (fallback)
    node = mode_node.get("signal") or prefs.get("signal") or {}
    return node
```

**Comportamento Após Harmonização**:
- ✅ `mode_node.get("signal")` sempre retorna o bloco correto (paper ou live)
- ✅ `prefs.get("signal")` retorna `None` (não existe mais)
- ✅ Fallback `{}` nunca é usado (sempre há `paper.signal` ou `live.signal`)

### **Sem Breaking Changes**
- ✅ Código existente continua funcionando
- ✅ Lógica de fallback preservada (mas não mais necessária)
- ✅ Todos os parâmetros estão presentes nos blocos específicos

---

## 📝 Checklist de Validação

### **1. Estrutura JSON Válida**
```bash
# Validar sintaxe JSON
python -m json.tool preferences.json > /dev/null && echo "✅ JSON válido"
python -m json.tool preferences.local.json > /dev/null && echo "✅ JSON válido"
```

### **2. Sincronização**
```bash
# Verificar se preferences.json = preferences.local.json
diff preferences.json preferences.local.json
# Resultado esperado: Nenhuma diferença
```

### **3. Parâmetros Completos**
Verificar se todos os parâmetros estão presentes em `paper.signal` e `live.signal`:

**Parâmetros Obrigatórios** (12 total):
- ✅ `min_exp`
- ✅ `min_oi_trend`
- ✅ `max_lsr_trend`
- ✅ `min_oi_change_pct`
- ✅ `max_lsr_change_pct`
- ✅ `min_cvd_change_pct`
- ✅ `cvd_streak_min`
- ✅ `min_trades_1m`
- ✅ `min_vol_adaptive_ratio`
- ✅ `min_rsi_5m`
- ✅ `max_bid_ask_spread`
- ✅ `min_oi_accel`
- ✅ `signal_mode`
- ✅ `cooldown_seconds`

### **4. Teste de Carregamento**
```bash
# Testar se config.py carrega corretamente
python -c "from config import load_config; cfg = load_config(); print(f'✅ Config carregado: mode={cfg.trading_mode}, rsi={cfg.min_rsi_5m}')"
```

**Saída Esperada**:
```
✅ Config carregado: mode=paper, rsi=65.0
```

---

## 🎯 Benefícios da Harmonização

### **1. Clareza**
- ✅ **Um único lugar** para cada parâmetro (paper ou live)
- ✅ **Sem ambiguidade** sobre qual valor usar
- ✅ **Fácil de entender** a hierarquia

### **2. Manutenção**
- ✅ **Mudanças localizadas**: Alterar Paper não afeta Live
- ✅ **Sem duplicação**: Não precisa atualizar 3 lugares
- ✅ **Menos erros**: Impossível ter valores inconsistentes

### **3. Governança**
- ✅ **Paridade Paper ↔ Live clara**: Diferenças intencionais documentadas
- ✅ **Auditável**: Fácil comparar Paper vs Live
- ✅ **Versionável**: Git diff mostra mudanças reais

### **4. Performance**
- ✅ **Leitura mais rápida**: Sem fallbacks desnecessários
- ✅ **Menos processamento**: Não precisa mesclar blocos
- ✅ **Cache eficiente**: Estrutura previsível

---

## 📚 Documentos Relacionados

1. **Sistema de Preferências**: `docs/SISTEMA_PREFERENCIAS.md`
2. **Paridade Paper ↔ Live**: `docs/PARIDADE_PAPER_LIVE.md`
3. **Changelog**: `docs/CHANGELOG.md` (v4.1.1)
4. **Config.py**: `config.py` (linhas 18-38)

---

## ✅ Status

### **Implementação**
- ✅ Blocos globais duplicados removidos
- ✅ Parâmetros movidos para blocos específicos
- ✅ `preferences.json` harmonizado
- ✅ `preferences.local.json` harmonizado
- ✅ Sincronização validada

### **Validação**
- ✅ JSON válido (sintaxe)
- ✅ Estrutura hierárquica correta
- ✅ Todos os parâmetros presentes
- ✅ Compatibilidade com `config.py` mantida

### **Documentação**
- ✅ Documento de harmonização criado
- ✅ CHANGELOG atualizado (v4.1.1)
- ✅ Paridade Paper ↔ Live documentada

---

**Harmonização Completa: SEM DUPLICIDADE, SEM AMBIGUIDADE** ✅