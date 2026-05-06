# Generated manually for plan completion, accessories, dyeing loss

from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0015_outsource_mill_orders'),
    ]

    operations = [
        migrations.AddField(
            model_name='dyeingorder',
            name='lost_quantity',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=12,
                verbose_name='产出损耗（约定未到货部分）',
            ),
        ),
        migrations.AddField(
            model_name='dyeingorder',
            name='loss_note',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='损耗备注'),
        ),
        migrations.AddField(
            model_name='productionplandetail',
            name='accessories_delivered',
            field=models.BooleanField(default=False, verbose_name='辅料已到齐'),
        ),
        migrations.AddField(
            model_name='productionplandetail',
            name='accessories_delivered_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='辅料到齐标记时间'),
        ),
        migrations.AddField(
            model_name='productionplandetail',
            name='finished_product',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='production_plan_details',
                to='production.product',
                verbose_name='成品产品',
            ),
        ),
        migrations.AddField(
            model_name='productionplandetail',
            name='size_completion',
            field=models.JSONField(
                default=list,
                help_text='结构与 sizes_data 对应：每项含 name 与 completed_quantities 数组（与 quantities 对齐）',
                verbose_name='各尺码已累计完工数量',
            ),
        ),
    ]
