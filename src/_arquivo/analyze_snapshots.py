"""Analisa snapshots CSV para encontrar trades contaminados."""
import csv
from pathlib import Path

csv_file = Path("logs/history/snapshots_2026-05-30.csv")

if not csv_file.exists():
    print(f"Arquivo não encontrado: {csv_file}")
    exit(1)

rows = []
with csv_file.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"Total de linhas: {len(rows)}")

# Analisar dados
if rows:
    # Mostrar primeiras linhas para entender a estrutura
    print("\nPrimeiras 5 linhas:")
    for i, row in enumerate(rows[:5]):
        print(f"\nLinha {i}:")
        for key, value in list(row.items())[:10]:  # Mostrar apenas primeiros 10 campos
            print(f"  {key}: {value}")
