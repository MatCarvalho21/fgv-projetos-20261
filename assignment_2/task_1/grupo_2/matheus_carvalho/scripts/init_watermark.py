#!/usr/bin/env python3
"""
Inicializa a tabela etl_watermark no banco classicmodels.

Idempotente:
  - Cria a tabela se não existir.
  - Insere o registro 'classicmodels_sales' se ausente.
  - Inicializa last_processed_order_date com MAX(orders.orderDate) atual.

Exit code: 0 = sucesso, 1 = falha.
"""

import logging
import sys
from pathlib import Path

# Adiciona o diretório pai ao path para importar db_config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db_config

PIPELINE_NAME = "classicmodels_sales"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("init_watermark")

# ── SQL Statements ───────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS etl_watermark (
    pipeline_name             VARCHAR(64)  NOT NULL,
    last_processed_order_date DATE         NULL,
    last_run_at               DATETIME     NULL,
    last_run_status           VARCHAR(32)  NOT NULL DEFAULT 'NEVER_RUN',
    PRIMARY KEY (pipeline_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# INSERT só se o registro ainda não existir.
# Usa INSERT IGNORE para ignorar silenciosamente duplicatas (PK).
INSERT_IF_ABSENT_SQL = """
INSERT IGNORE INTO etl_watermark
    (pipeline_name, last_processed_order_date, last_run_at, last_run_status)
VALUES (%s, %s, NULL, 'NEVER_RUN')
"""


def main() -> int:
    conn = None
    try:
        conn = db_config.get_connection(autocommit=False)
        cur = conn.cursor()

        # 1. Cria tabela
        log.info("Criando tabela etl_watermark (se não existir)...")
        cur.execute(CREATE_TABLE_SQL)

        # 2. Verifica se o registro já existe
        cur.execute(
            "SELECT last_processed_order_date FROM etl_watermark WHERE pipeline_name = %s",
            (PIPELINE_NAME,),
        )
        existing = cur.fetchone()

        if existing is None:
            # 3. Obtém MAX(orderDate) como baseline
            cur.execute("SELECT MAX(orderDate) FROM orders")
            max_date = cur.fetchone()[0]

            log.info("Inserindo registro '%s' com watermark=%s...", PIPELINE_NAME, max_date)
            cur.execute(INSERT_IF_ABSENT_SQL, (PIPELINE_NAME, max_date))
            inserted = True
        else:
            inserted = False

        conn.commit()

        # 4. Mostra estado final
        cur.execute(
            "SELECT pipeline_name, last_processed_order_date, last_run_at, last_run_status "
            "FROM etl_watermark WHERE pipeline_name = %s",
            (PIPELINE_NAME,),
        )
        row = cur.fetchone()
        cur.close()

        if row is None:
            log.error("Registro '%s' não encontrado após insert — algo deu errado.", PIPELINE_NAME)
            return 1

        pipeline, wm_date, run_at, status = row

        if inserted:
            log.info("✓ Registro CRIADO:")
        else:
            log.info("✓ Registro já existia (idempotente):")

        log.info("  pipeline_name             = %s", pipeline)
        log.info("  last_processed_order_date  = %s", wm_date)
        log.info("  last_run_at               = %s", run_at)
        log.info("  last_run_status           = %s", status)

        return 0

    except Exception as exc:
        log.exception("Falha ao inicializar watermark: %s", exc)
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return 1
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
