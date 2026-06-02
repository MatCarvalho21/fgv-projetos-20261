# Assignment 2 — Task 1: Origem incremental e watermark

Pipeline que prepara o banco `classicmodels` (RDS MySQL) para cargas incrementais. Reutiliza a infra do Assignment 1 (RDS provisionado na Task 1 do A1).

## Estrutura

```
matheus_carvalho/
├── scripts/
│   ├── init_watermark.py              # Cria/inicializa tabela etl_watermark
│   ├── simulate_new_orders.py         # Simula chegada de novos pedidos
│   └── validate_incremental_source.py # Valida que a origem está pronta para ETL
├── tests/
│   └── run_pipeline.sh                # Fluxo completo de validação (4 passos)
├── db_config.py                       # Helper de conexão com o RDS
├── requirements.txt                   # Dependências Python
└── README.md                          # Este arquivo
```

## Pré-requisitos

- Python 3.10+
- RDS MySQL ativo com o banco `classicmodels` carregado (A1 / Task 1)
- Credenciais configuradas (ver seção abaixo)

```bash
pip install -r requirements.txt
```

## Configuração de credenciais

O `db_config.py` suporta duas formas de configuração (em ordem de prioridade):

### 1. AWS Secrets Manager (recomendado)

Defina a variável de ambiente `SECRET_ARN` com o ARN do secret que contém as credenciais do RDS:

```bash
export SECRET_ARN="arn:aws:secretsmanager:us-east-1:123456789:secret:classicmodels-xyz"
export AWS_REGION="us-east-1"        # opcional, default: us-east-1
export AWS_PROFILE="projetos"        # se necessário
```

O secret deve conter um JSON com as chaves: `host`, `port`, `username`, `password`, `dbname`.

### 2. Variáveis de ambiente / rds_connection.env (fallback)

Se `SECRET_ARN` não estiver definido, o helper lê do arquivo `assignment_1/task_1/rds_connection.env` ou de variáveis de ambiente:

```bash
export RDS_HOST="classicmodels-db.xxxxx.us-east-1.rds.amazonaws.com"
export RDS_PORT="3306"
export RDS_DB="classicmodels"
export RDS_USER="admin"
export RDS_PASSWORD="..."    # nunca commitar!
```

> ⚠️ **Não commitar senhas ou o arquivo `.env` no repositório.**

## Uso

### 1. Inicializar watermark

Cria a tabela `etl_watermark` e insere o registro baseline com `MAX(orders.orderDate)`:

```bash
python scripts/init_watermark.py
```

Idempotente — pode re-executar sem problemas.

### 2. Simular novos pedidos

```bash
# 5 pedidos (default), sem seed
python scripts/simulate_new_orders.py

# 10 pedidos com seed para reprodutibilidade
python scripts/simulate_new_orders.py --count 10 --seed 42

# Preview sem inserir (dry-run)
python scripts/simulate_new_orders.py --count 5 --dry-run
```

**Parâmetros:**

| Flag | Descrição | Default |
|------|-----------|---------|
| `--count N` | Número de pedidos a criar | `5` |
| `--seed S` | Seed para reprodutibilidade | `None` |
| `--dry-run` | Preview sem inserir no banco | `False` |

**O que o simulador faz:**
- Escolhe `customerNumber` e `productCode` existentes no banco
- Insere em `orders` com `orderDate` estritamente posterior ao watermark/MAX(orderDate)
- Insere linhas em `orderdetails` com `quantityOrdered * priceEach > 0`
- Varia status entre `In Process` (60%), `Shipped` (30%), `On Hold` (10%)
- Preenche `shippedDate` para pedidos com status `Shipped`
- **NÃO** atualiza `etl_watermark` (responsabilidade do Glue na Task 2)

### 3. Validar origem incremental

```bash
python scripts/validate_incremental_source.py
```

**5 checks executados:**

| # | Check | Critério |
|---|-------|----------|
| 1 | `etl_watermark` existe | Tabela + registro `classicmodels_sales` presentes |
| 2 | Watermark não NULL | `last_processed_order_date` tem valor |
| 3 | Dados pendentes | `MAX(orderDate) > watermark` |
| 4 | Integridade | Todo `orderNumber` tem linhas em `orderdetails` |
| 5 | Consistência | `quantityOrdered > 0` e `priceEach > 0` em `orderdetails` |

Exit code `0` = todas as checagens passaram. Exit code `1` = falha.

## Fluxo completo (recomendado)

```bash
bash tests/run_pipeline.sh
```

Executa os 4 passos do fluxo sugerido no enunciado:

```
1. init_watermark              → cria/atualiza etl_watermark com baseline
2. validate_incremental_source → deve passar (baseline coerente)
3. simulate_new_orders --count 5 --seed 42  → insere pedidos novos
4. validate_incremental_source → deve passar (há dados pendentes)
```

## O que esta tarefa NÃO faz

- Não altera o star schema no S3 (isso é Task 2)
- Não agenda o Glue (isso é Task 2)
- Não commita credenciais ou dumps completos do banco
