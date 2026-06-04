# 🔒 Sistema de Persistência Total de Configurações

**Data**: 2026-06-02  
**Versão**: 4.2.0  
**Objetivo**: Garantir que TODAS as mudanças em configurações persistam após reinícios, quedas, refreshs

---

## 🎯 Problema Resolvido

### **Antes**:
- ❌ Mudanças via Dashboard **não persistiam**
- ❌ Após reinício: configs voltavam ao padrão
- ❌ Quedas de internet: perda de ajustes
- ❌ Necessidade de edição manual do arquivo

### **Depois**:
- ✅ Mudanças via Dashboard **persistem automaticamente**
- ✅ Após reinício: configs **restauradas**
- ✅ Quedas de internet: arquivo local **não afetado**
- ✅ Backup automático antes de cada salvamento

---

## 🚀 Arquitetura do Sistema

### **Fluxo de Persistência**:
```
Dashboard (UI)
    ↓ (usuário muda config)
POST /api/save-preferences
    ↓ (validação + backup)
preferences.local.json
    ↓ (salvo em disco)
Bot reinicia
    ↓ (carrega de disco)
Configs restauradas ✅
```

### **Componentes**:
1. **API Endpoints** (4 novos):
   - `POST /api/save-preferences` → Salva configs
   - `GET /api/load-preferences` → Carrega configs
   - `GET /api/list-backups` → Lista backups
   - `POST /api/restore-backup` → Restaura backup

2. **Backup Automático**:
   - Cria backup antes de cada salvamento
   - Formato: `preferences.local.json.backup_YYYYMMDD_HHMMSS`
   - Mantém últimas **5 versões**
   - Limpeza automática de backups antigos

3. **Validação**:
   - Estrutura JSON válida
   - Chaves obrigatórias presentes
   - Blocos `paper` e `live` completos
   - Previne corrupção de arquivo

---

## 📋 Endpoints da API

### **1. POST /api/save-preferences**

**Descrição**: Salva preferências em `preferences.local.json`

**Request**:
```json
POST /api/save-preferences
Content-Type: application/json

{
    "trading_mode": "paper",
    "top_n": 100,
    "paper": {
        "signal": {
            "min_rsi_5m": 65.0,
            "min_exp": 0.04,
            // ... outros parâmetros
        },
        "execution": {
            "sl_pct": 0.05,
            "tp_pct": 0.15,
            // ... outros parâmetros
        }
    },
    "live": {
        "signal": { /* ... */ },
        "execution": { /* ... */ }
    }
}
```

**Response (Sucesso)**:
```json
{
    "success": true,
    "message": "Preferências salvas com sucesso",
    "file": "preferences.local.json",
    "timestamp": "2026-06-02T03:12:00.000Z"
}
```

**Response (Erro)**:
```json
{
    "detail": "Chave obrigatória ausente: paper"
}
```

**Validações**:
- ✅ Payload é objeto JSON
- ✅ Chaves obrigatórias: `trading_mode`, `paper`, `live`
- ✅ Blocos `paper` e `live` contêm `signal` e `execution`
- ✅ Backup criado antes de sobrescrever

**Rate Limit**: 10 requests / 60 segundos

---

### **2. GET /api/load-preferences**

**Descrição**: Carrega preferências atuais de `preferences.local.json`

**Request**:
```
GET /api/load-preferences
```

**Response**:
```json
{
    "success": true,
    "preferences": {
        "trading_mode": "paper",
        "paper": { /* ... */ },
        "live": { /* ... */ }
    },
    "file": "preferences.local.json"
}
```

---

### **3. GET /api/list-backups**

**Descrição**: Lista backups disponíveis

**Request**:
```
GET /api/list-backups
```

**Response**:
```json
{
    "success": true,
    "backups": [
        {
            "filename": "preferences.local.json.backup_20260602_031200",
            "size": 3456,
            "modified": "2026-06-02T03:12:00.000Z"
        },
        {
            "filename": "preferences.local.json.backup_20260601_150000",
            "size": 3421,
            "modified": "2026-06-01T15:00:00.000Z"
        }
    ],
    "count": 2
}
```

---

### **4. POST /api/restore-backup**

**Descrição**: Restaura um backup específico

**Request**:
```json
POST /api/restore-backup
Content-Type: application/json

{
    "filename": "preferences.local.json.backup_20260602_031200"
}
```

**Response**:
```json
{
    "success": true,
    "message": "Backup restaurado: preferences.local.json.backup_20260602_031200",
    "restored_from": "preferences.local.json.backup_20260602_031200"
}
```

**Segurança**:
- ✅ Cria backup do arquivo atual antes de restaurar
- ✅ Salvo como `preferences.local.json.before_restore`
- ✅ Rate limit: 5 requests / 60 segundos

---

## 🔒 Garantias de Persistência

### **Cenários Testados**:

#### **1. Reinício Normal**
```
1. Usuário muda config via Dashboard
2. POST /api/save-preferences
3. Arquivo salvo em disco
4. Bot reinicia (python main.py)
5. config.py carrega preferences.local.json
6. Configs restauradas ✅
```

#### **2. Queda de Internet**
```
1. Usuário muda config via Dashboard
2. POST /api/save-preferences
3. Arquivo salvo em disco (local)
4. Internet cai
5. Arquivo local não é afetado ✅
6. Bot reinicia: configs restauradas ✅
```

#### **3. Refresh do Dashboard**
```
1. Usuário muda config via Dashboard
2. POST /api/save-preferences
3. Arquivo salvo em disco
4. Usuário dá refresh (F5)
5. GET /api/load-preferences
6. Configs carregadas do disco ✅
```

#### **4. Crash Inesperado**
```
1. Usuário muda config via Dashboard
2. POST /api/save-preferences
3. Arquivo salvo em disco
4. Bot crasha (erro fatal)
5. Bot reinicia
6. Última versão salva é restaurada ✅
```

---

## 🎯 Independência Paper ↔ Live

### **Mudanças Isoladas**:
```json
{
    "paper": {
        "signal": {
            "min_rsi_5m": 65.0  // ← Muda aqui
        }
    },
    "live": {
        "signal": {
            "min_rsi_5m": 70.0  // ← NÃO afeta aqui
        }
    }
}
```

### **Garantias**:
- ✅ Mudanças em `paper.signal` **não afetam** `live.signal`
- ✅ Mudanças em `live.execution` **não afetam** `paper.execution`
- ✅ Cada modo tem **seus próprios parâmetros**
- ✅ Sem blocos globais duplicados (harmonizado)

---

## 🛡️ Segurança e Validação

### **Validações Implementadas**:
1. ✅ **Estrutura JSON válida**
   - Payload deve ser objeto
   - Chaves obrigatórias presentes

2. ✅ **Integridade de Dados**
   - Blocos `paper` e `live` completos
   - Sub-blocos `signal` e `execution` presentes

3. ✅ **Backup Automático**
   - Criado antes de cada salvamento
   - Mantém últimas 5 versões
   - Limpeza automática

4. ✅ **Rate Limiting**
   - Salvamento: 10 req/min
   - Restauração: 5 req/min
   - Previne abuso

5. ✅ **Autenticação**
   - HTTP Guard (IP whitelisting)
   - Dashboard Secret (opcional)

---

## 📝 Exemplo de Uso (cURL)

### **Salvar Preferências**:
```bash
curl -X POST http://localhost:8765/api/save-preferences \
  -H "Content-Type: application/json" \
  -d @preferences.local.json
```

### **Carregar Preferências**:
```bash
curl http://localhost:8765/api/load-preferences
```

### **Listar Backups**:
```bash
curl http://localhost:8765/api/list-backups
```

### **Restaurar Backup**:
```bash
curl -X POST http://localhost:8765/api/restore-backup \
  -H "Content-Type: application/json" \
  -d '{"filename": "preferences.local.json.backup_20260602_031200"}'
```

---

## 🚀 Próximos Passos (UI)

### **Fase 2: Interface no Dashboard** (Próximo Sprint)

#### **Componentes a Criar**:
1. **Botão "Configurações"** no header
2. **Modal de Edição**:
   - Abas: Paper / Live
   - Formulários para cada parâmetro
   - Validação client-side
3. **Botão "Salvar"**:
   - Chama `/api/save-preferences`
   - Feedback visual (sucesso/erro)
4. **Seção "Backups"**:
   - Lista backups disponíveis
   - Botão "Restaurar" para cada backup

#### **Mockup**:
```
┌─────────────────────────────────────┐
│ ⚙️ Configurações                    │
├─────────────────────────────────────┤
│ [Paper] [Live]                      │
│                                     │
│ Signal:                             │
│   min_rsi_5m: [65.0]               │
│   min_exp: [0.04]                  │
│   ...                               │
│                                     │
│ Execution:                          │
│   sl_pct: [0.05]                   │
│   tp_pct: [0.15]                   │
│   ...                               │
│                                     │
│ [Salvar] [Cancelar]                │
└─────────────────────────────────────┘
```

---

## 📚 Arquivos Modificados

### **Backend**:
1. ✅ `src/web_dashboard.py` (4 endpoints adicionados)
   - `POST /api/save-preferences`
   - `GET /api/load-preferences`
   - `GET /api/list-backups`
   - `POST /api/restore-backup`

### **Documentação**:
2. ✅ `docs/PERSISTENCIA_CONFIGURACOES.md` (este documento)
3. ⏳ `docs/CHANGELOG.md` (v4.2.0 - próximo)

### **Frontend** (Próximo Sprint):
4. ⏳ Dashboard UI (modal de configurações)
5. ⏳ Formulários de edição
6. ⏳ Integração com API

---

## 🎯 Status

### **Implementado** (v4.2.0):
- ✅ 4 endpoints da API
- ✅ Validação de estrutura
- ✅ Backup automático
- ✅ Rate limiting
- ✅ Documentação completa

### **Pendente** (Próximo Sprint):
- ⏳ UI no Dashboard
- ⏳ Formulários de edição
- ⏳ Feedback visual
- ⏳ Hot reload (opcional)

---

**PERSISTÊNCIA TOTAL IMPLEMENTADA: BACKEND COMPLETO** ✅

Todas as mudanças em `preferences.local.json` agora **persistem** após:
- ✅ Reinícios
- ✅ Quedas de internet
- ✅ Refreshs
- ✅ Crashes

**Próximo passo**: Criar UI no Dashboard para edição visual (Fase 2)