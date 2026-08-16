from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_alembic_upgrade_creates_enterprise_tables(tmp_path):
    database_path = tmp_path / "migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    assert {
        "users",
        "knowledge_bases",
        "documents",
        "knowledge_base_documents",
        "departments",
        "user_departments",
        "knowledge_base_user_permissions",
        "knowledge_base_role_permissions",
        "knowledge_base_department_permissions",
        "chat_conversations",
        "chat_messages",
            "audit_logs",
            "document_versions",
            "document_index_tasks",
            "evaluation_datasets",
            "evaluation_cases",
            "evaluation_runs",
            "evaluation_results",
            "alembic_version",
    }.issubset(inspect(engine).get_table_names())
    with engine.connect() as connection:
        revision = connection.execute(text("select version_num from alembic_version")).scalar_one()
    assert revision == "20260813_0007"
    chat_columns = {column["name"] for column in inspect(engine).get_columns("chat_messages")}
    evaluation_columns = {
        column["name"] for column in inspect(engine).get_columns("evaluation_results")
    }
    token_columns = {"llm_model", "prompt_tokens", "completion_tokens", "total_tokens"}
    assert token_columns.issubset(chat_columns)
    assert token_columns.issubset(evaluation_columns)


def test_access_migration_preserves_existing_user_catalog_access(tmp_path):
    database_path = tmp_path / "seeded-migration.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "20260718_0002")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users
                    (username, password_hash, role, is_active, created_at, updated_at)
                VALUES
                    ('admin', 'hash', 'admin', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO knowledge_bases
                    (name, collection_name, created_by_id, created_at, updated_at)
                VALUES
                    ('existing', 'existing_collection', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            )
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        grant = connection.execute(
            text(
                """
                SELECT role, permission
                FROM knowledge_base_role_permissions
                WHERE knowledge_base_id = 1
                """
            )
        ).one()
    assert grant == ("user", "query")
