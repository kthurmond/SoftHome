# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-06 03:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MachineInterface', '0006_auto_20170206_0315'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sensor',
            name='state',
            field=models.DecimalField(decimal_places=2, max_digits=8),
        ),
    ]
