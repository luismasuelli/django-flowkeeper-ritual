# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-09-26 00:57
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ouroboros', '0004_auto_20160814_2347'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nodeinstance',
            name='node_spec',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='ouroboros.NodeSpec'),
        ),
    ]
