# Fixes PostgreSQL users.id sequence after data import / manual inserts
# (avoids IntegrityError: duplicate key on users_pkey).

from django.db import migrations


def sync_users_id_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('SELECT MAX(id) FROM users')
        max_id = cursor.fetchone()[0]
        cursor.execute("SELECT pg_get_serial_sequence('users', 'id')")
        seq = cursor.fetchone()[0]
        if not seq:
            return
        if max_id is None:
            cursor.execute('SELECT setval(%s::regclass, 1, false)', [seq])
        else:
            cursor.execute('SELECT setval(%s::regclass, %s, true)', [seq, max_id])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(sync_users_id_sequence, migrations.RunPython.noop),
    ]
