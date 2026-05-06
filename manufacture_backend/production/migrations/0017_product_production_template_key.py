from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0016_plan_completion_and_dyeing_loss'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='production_template_key',
            field=models.CharField(
                blank=True,
                help_text='与生产页的模板 radio 取值一致（如 f116、erDai），每张排产会自动关联本产品',
                max_length=50,
                null=True,
                unique=True,
                verbose_name='排产模板键',
            ),
        ),
    ]
