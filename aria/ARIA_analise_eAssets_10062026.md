# ARIA — Análise eAssets · 10/06/2026 · 07:56 UTC

**Snapshot:** `eassets_latest.json` · 531 símbolos · Binance USDM

---

## Contexto Macro — Mercado Bearish Estrutural

| Métrica | Valor | Leitura |
|---------|-------|---------|
| EMA:4h >= +4 (bull) | 43/531 (8%) | Apenas ilhas de desacoplamento |
| EMA:4h <= -4 (bear) | 416/531 (78%) | Estrutura macro profundamente bearish |
| EXP_BTC:1h > 0 | 178/531 (33%) | Só 1/3 das altcoins resistindo ao BTC |
| LSR_trend < -0.3 | 249/531 (46%) | Pressão short presente mas não generalizada |
| RSI:1h médio | 46.4 | Abaixo de 50 — mercado exausto |

**Comparação com sessão 03/06:** hoje está estruturalmente pior. Em 03/06 tínhamos 84% com EXP_BTC:1m positivos. Hoje são apenas 33% no 1h. O dinheiro está saindo do universo cripto, não apenas rotacionando entre altcoins.

---

## Funil de Gates SS

```
531 símbolos totais
 └─ 135 passam gate combo (trades_1m >= 10 + oi_trend >= 0.008 + lsr_trend <= -0.3)
     └─ 22 passam + ema_trend_4h >= 0      ← gate ema_4h_bearish bloqueou 111 (82%)
         └─ 22 passam + rsi_5m >= 45        ← rsi_5m não adiciona filtro hoje
```

Gate `ema_4h_bearish` está funcionando como projetado: eliminou 82% dos candidatos que passariam o gate combo mas têm estrutura 4h destroçada.

---

## Tier 1 — Anomalias Institucionais (6 ativos)

| Símbolo | EMA:4h | EXP_BTC:1h | EXP_BTC:15m | EXP_BTC:5m | RSI:1h | Trades/1m |
|---------|--------|-----------|------------|-----------|--------|-----------|
| STGUSDT | +6 | +121.5 | +62.8 | +34.9 | 76 | 2771 |
| UAIUSDT | +6 | +40.6 | +25.3 | +13.3 | 74 | 119 |
| PIPPINUSDT | +4 | +33.9 | +9.8 | +9.2 | 55 | 347 |
| FOLKSUSDT | +6 | +31.3 | +9.4 | +2.6 | 59 | 70 |
| HMSTRUSDT | +6 | +22.7 | +16.2 | +9.7 | 74 | 49 |
| ??USDT* | +6 | +22.4 | +24.6 | +21.4 | 67 | 277 |

*Símbolo com caracteres Unicode no JSON — verificar nome no dashboard do bot.*

**STGUSDT** é a anomalia da sessão: EXP_BTC:1h=+121.5 com alinhamento decrescente em todos os TFs (62→34). Perfil de movimento já em andamento — squeeze provavelmente na última perna. Monitorar, não entrar.

**??USDT** é o candidato mais interessante para entrada fresca: +22.4/+24.6/+21.4 alinhados nos 3 TFs, 277 trades/min, sem o EXP:1h absurdo que indica movimento tardio.

---

## Tier 2 — Força Confirmada 3 TFs (2 ativos)

| Símbolo | EMA:4h | EXP_BTC:1h | 15m | 5m | RSI:1h |
|---------|--------|-----------|-----|-----|--------|
| KASUSDT | +4 | +9.0 | +10.2 | +6.6 | 65 |
| SOONUSDT | +6 | +7.0 | +4.3 | +5.8 | 56 |

KASUSDT mantém força consistente (presente no snapshot anterior de 07:52 também). Alinhamento limpo 3 TFs, RSI:1h=65 com espaço para subir.

---

## Standby — Divergência Temporal (1 ativo)

| Símbolo | EMA:4h | EXP_BTC:1h | 15m | 5m | RSI:1h |
|---------|--------|-----------|-----|-----|--------|
| BTWUSDT | +3 | +86.4 | +8.3 | -4.8 | 56 |

Padrão clássico da tese de divergência temporal: EXP_BTC:1h=+86.4 (movimento institucional massivo) mas 5m=-4.8 (pullback/compressão atual). Se o 5m virar positivo com EMA:4h=+3 — entrada de qualidade máxima.

**Atenção:** BTWUSDT +20% foi registrado na análise de 10/06 01:48 UTC (LSR=+18 na época, movimento já havia acontecido). Verificar se este é um segundo ciclo ou continuação do mesmo.

---

## Gate ema_4h_bearish — Validação em Tempo Real

Ativos que passariam o gate combo mas foram bloqueados corretamente:

| Símbolo | EMA:4h | EXP_BTC:1h | Trades/1m | RSI:1h |
|---------|--------|-----------|-----------|--------|
| WLFIUSDT | -6 | +11.5 | 318 | 76 |
| HIVEUSDT | -6 | +8.2 | 184 | 68 |
| TREEUSDT | -6 | +6.5 | 32 | 65 |
| WCTUSDT | -6 | +6.3 | 59 | 62 |
| IDUSDT | -6 | +5.6 | 176 | 61 |
| XMRUSDT | -6 | +5.2 | 357 | 57 |

Esses 6 teriam RSI:1h alto e EXP_BTC:1h positivo — pareceriam boas entradas superficialmente. O gate os bloqueou por estrutura 4h destroçada. Esse é exatamente o padrão dos grandes losers das sessões anteriores (WAXPUSDT -16.93% com ema4h=-6).

---

## Implicações para Gates (resposta ao Brain)

**CVD threshold:** Em macro tão bearish (78% bear, RSI:1h médio 46.4), manter `min_cvd_change_pct_no_cascade = 1.0` ou elevar para 1.5. Spikes de CVD em mercado bearish são frequentemente armadilhas. Aguardar T-01 com 20+ trades antes de qualquer ajuste.

**Trailing stop:** STGUSDT (+121.5) e BTWUSDT (+86.4) reforçam a tese de que `exp_btc_1h > 30` indica movimento multi-perna onde trailing 75% sai cedo. Não alterar antes de T-01/T-02 confirmados — risco de ampliar trailing em losers bearish é maior que o ganho potencial nos winners agora.

---

*ARIA · análise gerada por Forge via script `aria/scripts/aria_snapshot_analysis.py` · 10/06/2026*
