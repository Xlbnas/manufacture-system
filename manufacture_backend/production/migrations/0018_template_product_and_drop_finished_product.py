from django.db import migrations, models


def fill_product_template_keys(apps, schema_editor):
    Product = apps.get_model('production', 'Product')
    for p in Product.objects.all():
        key = (getattr(p, 'production_template_key', None) or '').strip()
        if not key:
            p.production_template_key = f'legacy_{p.pk}'
            p.save(update_fields=['production_template_key'])


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0017_product_production_template_key'),
    ]

    operations = [
        migrations.RunPython(fill_product_template_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='production_template_key',
            field=models.CharField(
                help_text='与生产页的模板 radio 取值一致（如 f116、erDai），每条 Product 对应一条模板线',
                max_length=50,
                unique=True,
                verbose_name='排产模板键',
            ),
        ),
        migrations.RemoveField(
            model_name='productionplandetail',
            name='finished_product',
        ),
    ]
