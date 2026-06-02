"""
Helper de conexão com o RDS MySQL (classicmodels).

Hierarquia de credenciais:
  1. AWS Secrets Manager (se SECRET_ARN estiver definido)
  2. Variáveis de ambiente (RDS_HOST, RDS_PORT, etc.)
  3. Arquivo rds_connection.env do A1 (fallback para dev local)
"""

import json
import os
from pathlib import Path

# ── Leitura do .env (fallback) ────────────────────────────────────────────────

_ENV_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "assignment_1" / "task_1" / "rds_connection.env",
    Path(__file__).resolve().parents[4] / "assignment_1" / "task_1" / "rds_connection.env",
]


def _load_env_file() -> dict[str, str]:
    """Lê key=value de um arquivo .env, ignorando comentários e linhas vazias."""
    for candidate in _ENV_CANDIDATES:
        if candidate.is_file():
            env = {}
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("'\"")
                if key:
                    env[key] = val
            return env
    return {}


_FILE_ENV = _load_env_file()


def _get(key: str, fallback: str = "") -> str:
    """Retorna variável de ambiente ou valor do .env, com fallback."""
    return os.environ.get(key, _FILE_ENV.get(key, fallback))


# ── Secrets Manager ───────────────────────────────────────────────────────────

def _get_secret_from_aws() -> dict | None:
    """
    Tenta obter credenciais do Secrets Manager.
    Retorna None se SECRET_ARN não estiver definido.
    """
    secret_arn = _get("SECRET_ARN")
    if not secret_arn:
        return None

    import boto3

    region = _get("AWS_REGION", "us-east-1")
    client = boto3.client("secretsmanager", region_name=region)
    payload = client.get_secret_value(SecretId=secret_arn)["SecretString"]
    return json.loads(payload)


# ── Configuração ──────────────────────────────────────────────────────────────

def get_config() -> dict:
    """
    Retorna dicionário de configuração do RDS.

    Prioridade:
      1. Secrets Manager (se SECRET_ARN definido)
      2. Variáveis de ambiente / rds_connection.env
    """
    secret = _get_secret_from_aws()

    if secret is not None:
        return {
            "host":     secret["host"],
            "port":     int(secret.get("port", 3306)),
            "db":       secret.get("dbname", "classicmodels"),
            "user":     secret["username"],
            "password": secret["password"],
            "source":   "secrets_manager",
        }

    return {
        "host":     _get("RDS_HOST"),
        "port":     int(_get("RDS_PORT", "3306")),
        "db":       _get("RDS_DB", "classicmodels"),
        "user":     _get("RDS_USER", "admin"),
        "password": _get("RDS_PASSWORD"),
        "source":   "env",
    }


def get_connection(autocommit: bool = False):
    """
    Retorna uma conexão pymysql com o banco classicmodels.

    Args:
        autocommit: se True, cada statement é commitado automaticamente.
                    Para transações explícitas, use False (default).
    """
    import pymysql

    cfg = get_config()

    if not cfg["host"]:
        raise RuntimeError(
            "RDS_HOST não definido. Configure SECRET_ARN para usar Secrets Manager, "
            "ou defina RDS_HOST via variável de ambiente / rds_connection.env."
        )

    return pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["db"],
        charset="utf8mb4",
        connect_timeout=15,
        autocommit=autocommit,
    )
