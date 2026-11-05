"""MySQL persistence for model metadata and inference history."""

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pymysql
from pymysql.cursors import DictCursor

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

HISTORY_FILE = Path(settings.outputs_path).parent / "history.json"


@contextmanager
def _connection() -> Iterator[tuple[pymysql.Connection, DictCursor]]:
    connection = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        **(
            {
                "ssl_ca": str(settings.mysql_ssl_ca_path),
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
            }
            if settings.mysql_ssl_ca_path
            else {}
        ),
    )
    cursor = connection.cursor()
    try:
        yield connection, cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _insert_history(cursor: DictCursor, record: dict) -> None:
    cursor.execute(
        """
        INSERT IGNORE INTO inference_history (
            job_id, input_filename, model_filename, input_id, output_id,
            degraded_id, owner_id, degradation_mode, degradation_strength,
            status, processing_time_seconds, created_at, deleted_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            record["job_id"],
            record["input_filename"],
            record["model_filename"],
            record.get("input_id"),
            record.get("output_id"),
            record.get("degraded_id"),
            record.get("owner_id"),
            record.get("degradation_mode"),
            record.get("degradation_strength"),
            record["status"],
            record.get("processing_time_seconds"),
            record["created_at"],
            record.get("deleted_at"),
        ),
    )
    for asset_type, field in (("output", "output_ids"), ("degraded", "degraded_ids")):
        asset_ids = record.get(field) or []
        if asset_type == "output" and record.get("output_id"):
            asset_ids = list(dict.fromkeys([record["output_id"], *asset_ids]))
        if asset_type == "degraded" and record.get("degraded_id"):
            asset_ids = list(dict.fromkeys([record["degraded_id"], *asset_ids]))
        for page_index, asset_id in enumerate(asset_ids):
            cursor.execute(
                """
                INSERT IGNORE INTO inference_assets (asset_id, job_id, owner_id, asset_type, page_index)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (asset_id, record["job_id"], record.get("owner_id"), asset_type, page_index),
            )


def initialize() -> None:
    with _connection() as (_, cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS model_metadata (
                id CHAR(32) NOT NULL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                size BIGINT NOT NULL,
                uploaded_at VARCHAR(40) NOT NULL,
                status VARCHAR(24) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inference_history (
                job_id CHAR(32) NOT NULL PRIMARY KEY,
                input_filename VARCHAR(255) NOT NULL,
                model_filename VARCHAR(255) NOT NULL,
                input_id CHAR(32) NULL,
                output_id CHAR(32) NULL,
                degraded_id CHAR(32) NULL,
                owner_id CHAR(32) NULL,
                degradation_mode VARCHAR(32) NULL,
                degradation_strength INT NULL,
                status VARCHAR(24) NOT NULL,
                processing_time_seconds DOUBLE NULL,
                created_at VARCHAR(40) NOT NULL,
                deleted_at VARCHAR(40) NULL,
                INDEX history_owner_deleted_idx (owner_id, deleted_at),
                INDEX history_created_idx (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS data_migrations (
                name VARCHAR(100) NOT NULL PRIMARY KEY,
                applied_at VARCHAR(40) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inference_assets (
                asset_id CHAR(32) NOT NULL PRIMARY KEY,
                job_id CHAR(32) NOT NULL,
                owner_id CHAR(32) NULL,
                asset_type VARCHAR(16) NOT NULL,
                page_index INT NOT NULL DEFAULT 0,
                INDEX inference_assets_job_idx (job_id),
                INDEX inference_assets_owner_idx (owner_id),
                CONSTRAINT inference_assets_job_fk FOREIGN KEY (job_id)
                    REFERENCES inference_history(job_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute("SELECT name FROM data_migrations WHERE name = %s", ("legacy_json_import_v1",))
        if cursor.fetchone() is not None:
            return

        for metadata_file in settings.models_path.glob("*.json"):
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                cursor.execute(
                    """
                    INSERT IGNORE INTO model_metadata (id, filename, size, uploaded_at, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        metadata["id"],
                        metadata["filename"],
                        metadata["size"],
                        metadata["uploaded_at"],
                        metadata["status"],
                    ),
                )
            except (OSError, ValueError, KeyError, TypeError) as error:
                logger.warning("Skipping invalid model metadata %s: %s", metadata_file, error)

        if HISTORY_FILE.exists():
            try:
                history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                for record in history:
                    try:
                        _insert_history(cursor, record)
                    except (KeyError, TypeError) as error:
                        logger.warning("Skipping invalid history record: %s", error)
            except (OSError, ValueError) as error:
                logger.warning("Could not import legacy history file: %s", error)

        cursor.execute(
            "INSERT INTO data_migrations (name, applied_at) VALUES (%s, UTC_TIMESTAMP())",
            ("legacy_json_import_v1",),
        )


def list_models() -> list[dict]:
    with _connection() as (_, cursor):
        cursor.execute("SELECT id, filename, size, uploaded_at, status FROM model_metadata ORDER BY uploaded_at DESC")
        return list(cursor.fetchall())


def get_model(model_id: str) -> dict | None:
    with _connection() as (_, cursor):
        cursor.execute(
            "SELECT id, filename, size, uploaded_at, status FROM model_metadata WHERE id = %s",
            (model_id,),
        )
        return cursor.fetchone()


def save_model(metadata: dict) -> None:
    with _connection() as (_, cursor):
        cursor.execute(
            """
            INSERT INTO model_metadata (id, filename, size, uploaded_at, status)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE filename = VALUES(filename), size = VALUES(size),
                uploaded_at = VALUES(uploaded_at), status = VALUES(status)
            """,
            (
                metadata["id"],
                metadata["filename"],
                metadata["size"],
                metadata["uploaded_at"],
                metadata["status"],
            ),
        )


def delete_model(model_id: str) -> bool:
    with _connection() as (_, cursor):
        cursor.execute("DELETE FROM model_metadata WHERE id = %s", (model_id,))
        return cursor.rowcount == 1


def list_history() -> list[dict]:
    with _connection() as (_, cursor):
        cursor.execute("SELECT * FROM inference_history ORDER BY created_at DESC")
        records = list(cursor.fetchall())
        if not records:
            return records
        job_ids = [record["job_id"] for record in records]
        placeholders = ", ".join(["%s"] * len(job_ids))
        cursor.execute(
            f"SELECT job_id, asset_id, asset_type FROM inference_assets WHERE job_id IN ({placeholders}) ORDER BY page_index",
            tuple(job_ids),
        )
        assets: dict[str, dict[str, list[str]]] = {}
        for row in cursor.fetchall():
            assets.setdefault(row["job_id"], {}).setdefault(row["asset_type"], []).append(row["asset_id"])
        for record in records:
            record["output_ids"] = assets.get(record["job_id"], {}).get("output", [])
            record["degraded_ids"] = assets.get(record["job_id"], {}).get("degraded", [])
        return records


def user_owns_asset(asset_id: str, user_id: str) -> bool:
    with _connection() as (_, cursor):
        cursor.execute(
            """
            SELECT 1 FROM inference_history
            WHERE owner_id = %s AND (input_id = %s OR output_id = %s OR degraded_id = %s)
            LIMIT 1
            """,
            (user_id, asset_id, asset_id, asset_id),
        )
        if cursor.fetchone() is not None:
            return True
        cursor.execute(
            "SELECT 1 FROM inference_assets WHERE owner_id = %s AND asset_id = %s LIMIT 1",
            (user_id, asset_id),
        )
        return cursor.fetchone() is not None


def append_history(record: dict) -> None:
    with _connection() as (_, cursor):
        _insert_history(cursor, record)
        cursor.execute(
            "SELECT job_id FROM inference_history WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 200"
        )
        retained_ids = [row["job_id"] for row in cursor.fetchall()]
        if retained_ids:
            placeholders = ", ".join(["%s"] * len(retained_ids))
            cursor.execute(
                f"DELETE FROM inference_history WHERE deleted_at IS NULL AND job_id NOT IN ({placeholders})",
                tuple(retained_ids),
            )
        else:
            cursor.execute("DELETE FROM inference_history WHERE deleted_at IS NULL")


def set_history_deleted_at(job_id: str, deleted_at: str | None) -> bool:
    with _connection() as (_, cursor):
        cursor.execute(
            "UPDATE inference_history SET deleted_at = %s WHERE job_id = %s",
            (deleted_at, job_id),
        )
        return cursor.rowcount == 1


def permanently_delete_history(job_id: str) -> bool:
    with _connection() as (_, cursor):
        cursor.execute("DELETE FROM inference_history WHERE job_id = %s", (job_id,))
        return cursor.rowcount == 1