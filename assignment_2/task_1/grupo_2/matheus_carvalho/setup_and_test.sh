#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Setup completo: RDS + carga + Secret + Task 1
#
# Executa tudo do zero em um Learner Lab limpo:
#   1. Provisiona RDS (script A1)
#   2. Carrega banco classicmodels (script A1)
#   3. Cria Secret no Secrets Manager
#   4. Executa pipeline Task 1 (init_watermark → validate → simulate → validate)
# ═══════════════════════════════════════════════════════════════════════

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
A1_DIR="$PROJECT_ROOT/assignment_1/task_1"
A2_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  PROJECT_ROOT: $PROJECT_ROOT"
echo "  A1_DIR:       $A1_DIR"
echo "  A2_DIR:       $A2_DIR"
echo "════════════════════════════════════════════════════════"

# ── Passo 1: Provisionar RDS ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  PASSO 1 — Provisionar RDS (assignment_1/task_1)"
echo "════════════════════════════════════════════════════════"
cd "$A1_DIR/grupo_2/final"
python3 provision_rds.py
cd "$A2_DIR"

# ── Passo 2: Carregar dados ──────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  PASSO 2 — Carregar banco classicmodels"
echo "════════════════════════════════════════════════════════"
cd "$A1_DIR/grupo_2/final"
python3 load_data.py
cd "$A2_DIR"

# ── Passo 3: Criar Secret no Secrets Manager ─────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  PASSO 3 — Criar Secret no Secrets Manager"
echo "════════════════════════════════════════════════════════"

# Lê credenciais do rds_connection.env gerado pelo provision_rds.py
ENV_FILE="$A1_DIR/rds_connection.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "ERRO: $ENV_FILE não encontrado. O provision_rds.py gerou o arquivo?"
    echo "Verificando se foi gerado em outro local..."
    # provision_rds.py pode gerar no cwd
    ALT_ENV="$A1_DIR/grupo_2/final/rds_connection.env"
    if [ -f "$ALT_ENV" ]; then
        echo "Encontrado em: $ALT_ENV — copiando..."
        cp "$ALT_ENV" "$ENV_FILE"
    else
        echo "ERRO: Nenhum rds_connection.env encontrado."
        exit 1
    fi
fi

source <(grep -v '^#' "$ENV_FILE" | sed 's/^/export /')

SECRET_NAME="classicmodels-rds-credentials"
SECRET_JSON=$(cat <<EOF
{
    "host": "$RDS_HOST",
    "port": $RDS_PORT,
    "username": "$RDS_USER",
    "password": "$RDS_PASSWORD",
    "dbname": "$RDS_DB"
}
EOF
)

# Tenta criar ou atualizar o secret
SECRET_ARN=$(aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --description "Credenciais RDS classicmodels (A2 Task 1)" \
    --secret-string "$SECRET_JSON" \
    --region us-east-1 \
    --query 'ARN' --output text 2>/dev/null) || \
SECRET_ARN=$(aws secretsmanager put-secret-value \
    --secret-id "$SECRET_NAME" \
    --secret-string "$SECRET_JSON" \
    --region us-east-1 \
    --query 'ARN' --output text 2>/dev/null) || \
SECRET_ARN=$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region us-east-1 \
    --query 'ARN' --output text)

echo "SECRET_ARN=$SECRET_ARN"
export SECRET_ARN
export AWS_REGION=us-east-1

# ── Passo 4: Pipeline Task 1 ─────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  PASSO 4 — Pipeline Task 1 (init → validate → simulate → validate)"
echo "════════════════════════════════════════════════════════"

echo ""
echo "--- 4a. init_watermark ---"
cd "$A2_DIR"
python3 scripts/init_watermark.py

echo ""
echo "--- 4b. validate (baseline) ---"
python3 scripts/validate_incremental_source.py

echo ""
echo "--- 4c. simulate_new_orders (5 pedidos, seed=42) ---"
python3 scripts/simulate_new_orders.py --count 5 --seed 42

echo ""
echo "--- 4d. validate (com dados pendentes) ---"
python3 scripts/validate_incremental_source.py

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✓ SETUP COMPLETO + TASK 1 VALIDADA"
echo "════════════════════════════════════════════════════════"
echo ""
echo "  SECRET_ARN: $SECRET_ARN"
echo "  RDS_HOST:   $RDS_HOST"
echo ""
