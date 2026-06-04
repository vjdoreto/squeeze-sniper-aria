# Sistema de Preferências - SqueezeSniper V4

## 🎯 QUAL ARQUIVO É O OFICIAL?

O sistema usa **PRIORIDADE** para determinar qual arquivo carregar:

```
1. PREFERENCES_FILE (variável de ambiente) - se definida
2. preferences.local.json - SE EXISTIR (PRIORIDADE)
3. preferences.json - fallback padrão
```

### ⚠️ IMPORTANTE

**Se `preferences.local.json` existe, ELE É O ARQUIVO OFICIAL!**

Todas as mudanças via Dashboard são salvas nele.
Edições manuais devem ser feitas nele.

---

## 📁 ESTRUTURA DE ARQUIVOS

### preferences.local.json
- **Uso:** Configurações locais (não versionadas no Git)
- **Prioridade:** ALTA (usado se existir)
- **Git:** Ignorado (.gitignore)
- **Edição:** Via Dashboard OU manualmente

### preferences.json
- **Uso:** Configurações padrão (versionadas no Git)
- **Prioridade:** BAIXA (usado se local não existir)
- **Git:** Versionado
- **Edição:** Apenas para defaults do projeto

### preferences.suggested.json
- **Uso:** Sugestões do PaperAnalyzer
- **Prioridade:** NENHUMA (apenas referência)
- **Git:** Ignorado
- **Edição:** Gerado automaticamente

---

## 🔄 SINCRONIZAÇÃO

### Problema Comum

Você edita `preferences.json` manualmente, mas o sistema usa `preferences.local.json`.
Resultado: Suas mudanças não têm efeito!

### Solução 1: Script de Sincronização

```bash
python sync_preferences.py
```

Este script:
1. Copia `preferences.local.json` → `preferences.json`
2. Cria backup antes de sobrescrever
3. Garante que ambos fiquem idênticos

### Solução 2: Editar o Arquivo Correto

Sempre edite `preferences.local.json` se ele existir.

### Solução 3: Usar o Dashboard

O Dashboard sempre salva no arquivo correto automaticamente.

---

## 🛠️ COMO FUNCIONA

### Carregamento (config.py)

```python
def resolve_preferences_path() -> Path:
    """Local file wins (sem git); depois env; depois defaults versionados."""
    raw = os.getenv("PREFERENCES_FILE", "").strip()
    if raw:
        return Path(raw)
    if PREFERENCES_LOCAL.is_file():  # ← PRIORIDADE
        return PREFERENCES_LOCAL
    return DEFAULT_PREFERENCES_PATH
```

### Salvamento (main.py)

```python
def _save_prefs(prefs: dict):
    """Centraliza a escrita no preferences.json."""
    prefs_path = resolve_preferences_path()  # ← Usa o mesmo sistema
    # ... salva no arquivo correto
```

### Handlers do Dashboard

Todos os handlers (`_on_update_paper_settings`, `_on_update_live_settings`, etc.) usam `_save_prefs()`, garantindo que as mudanças sejam persistidas no arquivo correto.

---

## 🔍 VERIFICAÇÃO

### Ao Iniciar o Sistema

O `main.py` agora exibe:

```
================================================================================
📋 ARQUIVO DE PREFERÊNCIAS ATIVO: preferences.local.json
⚠️  IMPORTANTE: Mudanças via Dashboard salvam neste arquivo!
⚠️  Edições manuais devem ser feitas em: preferences.local.json
================================================================================
```

### Via Código

```python
from config import resolve_preferences_path

prefs_file = resolve_preferences_path()
print(f"Arquivo oficial: {prefs_file}")
```

---

## 📝 BOAS PRÁTICAS

### ✅ FAÇA

1. **Use o Dashboard** para mudanças em tempo real
2. **Edite preferences.local.json** para mudanças manuais
3. **Execute sync_preferences.py** após edições manuais
4. **Verifique o log** ao iniciar para confirmar o arquivo usado

### ❌ NÃO FAÇA

1. **Não edite preferences.json** se preferences.local.json existir
2. **Não edite ambos** sem sincronizar depois
3. **Não ignore** o aviso no log de inicialização
4. **Não delete preferences.local.json** sem motivo (ele é o oficial!)

---

## 🐛 TROUBLESHOOTING

### Problema: Mudanças não persistem

**Causa:** Você está editando o arquivo errado

**Solução:**
1. Verifique qual arquivo o sistema está usando (log de inicialização)
2. Edite o arquivo correto
3. Ou use o Dashboard

### Problema: Arquivos dessincronizados

**Causa:** Edições manuais em ambos os arquivos

**Solução:**
```bash
python sync_preferences.py
```

### Problema: Configurações voltam ao padrão

**Causa:** Sistema está lendo preferences.json mas você editou preferences.local.json (ou vice-versa)

**Solução:**
1. Identifique qual arquivo é o oficial (log)
2. Copie suas configurações para o arquivo oficial
3. Execute sync_preferences.py

---

## 🔒 SEGURANÇA

### Git Ignore

O `.gitignore` deve conter:

```
preferences.local.json
preferences.suggested.json
```

Isso garante que:
- Configurações locais não vazem para o repositório
- Cada desenvolvedor tenha suas próprias configurações
- Sugestões do analyzer não sejam versionadas

### Backups

O `_save_prefs()` usa escrita atômica:

```python
tmp_path = prefs_path.with_suffix(".tmp")
# escreve no .tmp primeiro
tmp_path.replace(prefs_path)  # substitui atomicamente
```

Isso previne corrupção se o sistema crashar durante a escrita.

---

## 📊 FLUXO COMPLETO

```
┌─────────────────────────────────────────────────────────────┐
│                    INICIALIZAÇÃO                             │
│                                                              │
│  1. resolve_preferences_path()                               │
│     ├─ PREFERENCES_FILE env? → usa                          │
│     ├─ preferences.local.json existe? → USA (OFICIAL)       │
│     └─ senão → preferences.json                             │
│                                                              │
│  2. load_preferences(path)                                   │
│     └─ Carrega JSON do arquivo determinado                  │
│                                                              │
│  3. load_config()                                            │
│     └─ Cria BotConfig com valores carregados                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    OPERAÇÃO                                  │
│                                                              │
│  Dashboard → Handler → _save_prefs()                         │
│                          │                                   │
│                          ├─ resolve_preferences_path()       │
│                          ├─ Escreve .tmp                     │
│                          └─ Substitui atomicamente           │
│                                                              │
│  Resultado: Mudanças persistidas no arquivo OFICIAL         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎓 RESUMO

1. **preferences.local.json** é o arquivo oficial (se existir)
2. **Dashboard** sempre salva no arquivo correto
3. **Edições manuais** devem ser no arquivo oficial
4. **sync_preferences.py** mantém ambos sincronizados
5. **Log de inicialização** mostra qual arquivo está ativo

---

**Data:** 2026-05-31
**Versão:** V4.1
**Autor:** Sistema de Auditoria