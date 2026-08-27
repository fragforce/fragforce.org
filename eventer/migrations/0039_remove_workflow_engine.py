from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("eventer", "0038_eventrole_show_notes_data"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS django_workflow_engine_taskstatus CASCADE;",
                "DROP TABLE IF EXISTS django_workflow_engine_tasklog CASCADE;",
                "DROP TABLE IF EXISTS django_workflow_engine_target CASCADE;",
                "DROP TABLE IF EXISTS django_workflow_engine_taskrecord CASCADE;",
                "DROP TABLE IF EXISTS django_workflow_engine_flow CASCADE;",
                "DELETE FROM django_migrations WHERE app = 'django_workflow_engine';",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
