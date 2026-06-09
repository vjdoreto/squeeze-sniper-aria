# Integração eAssets ↔ Squeeze Sniper

## Versão: 2.0 | Atualizado: 07/06/2026 (Auditado por Gemini)

---

## 📁 Estrutura de Arquivos

```
c:\Apps\#5 Squeeze Sniper-V4\eAssets\
├── Dashboard_eAssets.bat         # Arquivo principal para iniciar tudo com 1 clique
├── doreto-squeeze-sniper.html    # Dashboard eAssets modificado com auto-refresh
├── enrich_client.js              # Cliente JavaScript para integração CVD
├── enrich_server.py              # Servidor HTTP para enriquecimento de dados
├── enrich_dashboard_json.py      # Script CLI para enriquecer JSON manualmente
├── monitorar_eassets.py          # Monitorador de pasta para JSON eAssets
├── iniciar_dashboard.py          # Script Python que inicia todo o sistema
├── dados_eassets\                # Pasta para armazenar JSON eAssets
│   ├── eassets-panel-20260607-012027.json  # Seu arquivo JSON do eAssets
│   ├── eassets_latest.json       # Link para o arquivo mais recente
│   ├── eassets_consolidado_com_sniper.json # ARQUIVO MESTRE: eAssets + SS + Macro
│   └── historico\                # Backup automático de todos os downloads
└── INTEGRACAO_EASSETS_SQUEEZESNIPER.md  # Este arquivo!
```

---

## 🚀 Como Usar (Passo a Passo)

### 1. Iniciar o Sistema

Dê **duplo clique** no arquivo:

```
c:\Apps\#5 Squeeze Sniper-V4\eAssets\Dashboard_eAssets.bat
```

Isso inicia automaticamente:

- ✅ Servidor de enriquecimento CVD (porta 5001)
- ✅ Monitorador de arquivos JSON (verifica pasta a cada 2s)
- ✅ Dashboard no navegador padrão

### 2. Adicionar Dados eAssets

Salve qualquer arquivo JSON exportado do eAssets na pasta:

```
c:\Apps\#5 Squeeze Sniper-V4\eAssets\dados_eassets\
```

O monitorador detecta automaticamente o arquivo **mais recente**!

### 3. Aproveitar a Integração

- O dashboard atualiza **automaticamente a cada 2 segundos**
- Dados do Squeeze Sniper são adicionados aos ativos (CVD, Score, etc.)

---

## 🔧 Componentes do Sistema

### A. Servidor de Enriquecimento (`enrich_server.py`)

**Função**: Servidor HTTP que combina dados do eAssets com dados do Squeeze Sniper

- **Endpoints**:
  - `GET /health`: Verifica se o servidor está online
  - `POST /api/enrich-json`: Envia JSON eAssets, retorna JSON enriquecido
  - `GET /api/latest-enriched`: Retorna o JSON enriquecido mais recente
- **Porta padrão**: `127.0.0.1:5001`

### B. Monitorador de Arquivos (`monitorar_eassets.py`)

**Função**: Monitora a pasta `dados_eassets` para arquivos JSON novos/atualizados

- Verifica a cada 2 segundos
- Sempre usa o arquivo JSON mais recente
- Envia para o servidor de enriquecimento automaticamente

### C. Dashboard eAssets (`doreto-squeeze-sniper.html`)

**Modificações feitas**:

- Adicionado script de auto-refresh
- Consulta `/api/latest-enriched` a cada 2 segundos
- Atualiza automaticamente quando há dados novos

### D. Script de Inicialização (`iniciar_dashboard.py`)

**Função**: Inicia todos os componentes em segundo plano e abre o navegador

- Inicia servidor de enriquecimento
- Inicia monitorador de arquivos
- Abre dashboard no navegador padrão
- Mantém tudo rodando até fechar a janela

---

## 📊 Dados Adicionados pelo Squeeze Sniper

Para cada ativo que o Sniper tem dados, são adicionados:

| Campo | Descrição |
|-------|-----------|
| `cvd_change_pct:5m` | CVD percentual (5 minutos) |
| `cvd:5m` | CVD absoluto |
| `cvd_streak:5m` | Sequência de candles com CVD positivo |
| `squeeze_sniper_score:5m` | Score do Sniper (0-100) |
| `oi_change_pct:5m` | Variação do Open Interest |
| `lsr_change_pct:5m` | Variação do Long/Short Ratio |
| `trades_1m` | Número de trades no último minuto |
| `rsi:5m` | RSI de 5 minutos |
| `ema_trend:5m` | Tendência EMA |
| `volume_quality` | Qualidade do volume |
| `exp_btc_norm_1h` | Exposição BTC normalizada (1h) |

---

## 🔄 Próximos Passos (Automação Total)

Para remover completamente a necessidade de salvar JSON manualmente, podemos:

1. Integrar diretamente com a **API do eAssets** (quando tiver a chave)
2. Buscar os dados automaticamente a cada X segundos
3. Eliminar a etapa de salvar/exportar manualmente!

Quando você tiver a chave API e os detalhes do endpoint do eAssets, é só implementar! 😊
