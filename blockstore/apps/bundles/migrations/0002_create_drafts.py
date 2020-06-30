# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-03-05 14:11


from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('bundles', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Draft',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=180)),
                ('bundle', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='drafts', related_query_name='draft', to='bundles.Bundle')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='draft',
            unique_together=set([('bundle', 'name')]),
        ),
    ]
