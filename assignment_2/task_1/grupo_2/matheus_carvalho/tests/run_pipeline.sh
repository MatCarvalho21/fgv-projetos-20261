#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Assignment 2 — Task 1: Fluxo completo de validação
#
# Executa o fluxo documentado na seção 4 do enunciado:
#   1. init_watermark      → cria/atualiza etl_watermark com baseline do A1
#   2. validate            → deve passar (baseline coerente)
#   3. simulate --count N  → insere pedidos novos
#   4. validate            → deve passar (com dados pendentes)
# ═══════════════════════════════════════════════════════════════════════

set -e
cd "$(dirname "$0")/.."

echo ""
echo "════════════════════════════════════════════════"
echo "  PASSO 1 — Inicializar watermark"
echo "════════════════════════════════════════════════"
python3 scripts/init_watermark.py

echo ""
echo "════════════════════════════════════════════════"
echo "  PASSO 2 — Validar (estado inicial / baseline)"
echo "════════════════════════════════════════════════"
python3 scripts/validate_incremental_source.py

echo ""
echo "════════════════════════════════════════════════"
echo "  PASSO 3 — Simular novos pedidos (5, seed=42)"
echo "════════════════════════════════════════════════"
python3 scripts/simulate_new_orders.py --count 5 --seed 42

echo ""
echo "════════════════════════════════════════════════"
echo "  PASSO 4 — Validar (com dados pendentes)"
echo "════════════════════════════════════════════════"
python3 scripts/validate_incremental_source.py

echo ""
echo "════════════════════════════════════════════════"
echo "  ✓ TODOS OS PASSOS CONCLUÍDOS COM SUCESSO"
echo "════════════════════════════════════════════════"
echo ""
