#!/usr/bin/env python3
"""
Claude Hub - Automatizador para SqueezeSniper V4
Versão corrigida para Windows
"""

import json
import os
from datetime import datetime
from pathlib import Path

# === CONFIGURAÇÃO DO CAMINHO (ajustado para Windows) ===
# Tente encontrar a pasta do projeto automaticamente
possible_paths = [
    Path("C:/Apps/#5 SqueezeSniper-V4"),           # seu caminho principal
    Path.cwd(),                                    # pasta atual
    Path(__file__).parent,                         # pasta onde está o script
]

BASE_DIR = None
for p in possible_paths:
    if p.exists():
        BASE_DIR = p
        break

if not BASE_DIR:
    BASE_DIR = Path.cwd()
    print("⚠️  Não encontrei a pasta exata. Usando pasta atual.")

LOGS_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"

def load_file(filepath):
    try:
        return Path(filepath).read_text(encoding="utf-8")
    except Exception as e:
        return f"[Arquivo não encontrado: {filepath}]"

def get_recent_session_summary():
    """Tenta pegar o último resumo de trades"""
    closed_file = LOGS_DIR / "paper_closed.jsonl"
    if closed_file.exists():
        try:
            lines = closed_file.read_text(encoding="utf-8").strip().splitlines()
            return "\n".join(lines[-15:]) if lines else "Nenhuma trade recente."
        except:
            pass
    return "Nenhuma sessão recente encontrada."

def generate_package(agent: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    context = load_file(DOCS_DIR / "Engenheiro e DNA do Sniper v2.0.md")
    if context.startswith("[Arquivo não encontrado"):
        context = load_file("context.md")
    
    last_session = get_recent_session_summary()
    
    header = f"""# 📦 PACOTE PARA {agent.upper()} — SqueezeSniper V4
**Gerado em:** {now}
**Pasta base:** {BASE_DIR}
---

"""
    
    if agent == "atlas":
        content = f"""**CONTEXTO ATUAL:**\n{context[:12000]}\n\n**ÚLTIMA SESSÃO:**\n{last_session}\n\nFaça um resumo executivo + liste no máximo **3 ações prioritárias**."""
    
    elif agent == "brian":
        content = f"""**FOCO: Análise de Dados**\n\n{last_session}\n\nExtraia KPIs, compare winners vs losers e sugira ajustes baseados em números."""
    
    elif agent == "aria":
        content = f"""**FOCO: Estratégia e DNA**\n\n{last_session}\n\nSugira melhorias no score, gates, filtros ou divergência temporal."""
    
    elif agent == "forge":
        content = f"""**FOCO: Implementação**\n\nÚltima sessão: {last_session}\n\nImplemente as tarefas prioritárias e marque como feito."""
    
    else:
        content = last_session
    
    full_package = header + content
    filename = f"package_{agent}.md"
    
    Path(filename).write_text(full_package, encoding="utf-8")
    print(f"✅ Criado: {filename} ({len(full_package)//1000}k caracteres)")

def main():
    print("🚀 Claude Hub - Gerando pacotes...\n")
    print(f"📍 Usando pasta: {BASE_DIR}\n")
    
    agents = ["atlas", "brian", "aria", "forge"]
    
    for agent in agents:
        generate_package(agent)
    
    print("\n🎯 Pronto!")
    print("   Abra os arquivos `package_*.md` e copie o conteúdo para cada chat.")
    print("   Comece sempre pelo `package_atlas.md`")

if __name__ == "__main__":
    main()