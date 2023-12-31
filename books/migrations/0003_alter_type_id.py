# Generated by Django 4.2.7 on 2023-12-01 16:36

from django.db import migrations, models

def set_auto_increment_start(apps, schema_editor):
    schema_editor.execute("SELECT setval('books_author_id_seq', 681, false)")


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0002_alter_author_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='type',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
        migrations.RunPython(set_auto_increment_start),
    ]
