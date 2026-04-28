from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0009_transferorder_alter_material_options_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='OutboundRecord',
        ),
    ]
