from __future__ import annotations

from django.db import migrations


def enable_postgis(apps, schema_editor):  # pragma: no cover - инфраструктурная миграция
    # Выполняем только в PostgreSQL, иначе (SQLite/MySQL) — просто пропускаем
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(enable_postgis, reverse_code=migrations.RunPython.noop),
    ]
