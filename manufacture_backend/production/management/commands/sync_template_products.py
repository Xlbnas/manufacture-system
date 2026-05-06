from django.core.management.base import BaseCommand

from production.template_catalog import sync_template_product_rows


class Command(BaseCommand):
    help = '为 template_catalog 中每个模板键补全一条 Product（已有则跳过，不覆盖名称）。'

    def handle(self, *args, **options):
        created = sync_template_product_rows()
        if created:
            self.stdout.write(self.style.SUCCESS(f'新建模板产品: {", ".join(created)}'))
        else:
            self.stdout.write(self.style.SUCCESS('无需新建，模板键均已存在对应 Product。'))
