"""
为每个工厂补全「工厂仓」仓库节点，并尝试修复 factory 外键为空的旧数据。

用法（宿主机）:
  cd manufacture_backend && python manage.py ensure_factory_warehouses

Docker Compose（项目根目录）:
  docker compose exec backend python manage.py ensure_factory_warehouses

可选:
  --dry-run  只打印将要执行的操作，不写库。
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from production.models import Factory, WarehouseNode
from production.views import ensure_factory_warehouse_for_factory


def _repair_orphan_factory_warehouses(dry_run: bool) -> tuple[int, int]:
    """
    将 warehouse_type=factory 且 factory 为空的节点，在能唯一推断时挂到工厂上
    （例如名称含「武昌」且仅有一个工厂的 location 为武昌）。
    """
    linked = 0
    skipped = 0
    orphans = list(
        WarehouseNode.objects.filter(
            warehouse_type='factory',
            factory__isnull=True,
            is_active=True,
        )
    )
    factories = list(Factory.objects.all())
    for wh in orphans:
        candidates = []
        for f in factories:
            loc = (f.location or '').strip()
            if loc and loc in wh.name:
                candidates.append(f)
        if len(candidates) != 1:
            skipped += 1
            continue
        f = candidates[0]
        if dry_run:
            print(f'[dry-run] 将仓库「{wh.name}」(id={wh.id}) 绑定工厂「{f.name}」(id={f.id})')
        else:
            wh.factory = f
            wh.save(update_fields=['factory'])
            print(f'已绑定：仓库「{wh.name}」(id={wh.id}) → 工厂「{f.name}」(id={f.id})')
        linked += 1
    return linked, skipped


class Command(BaseCommand):
    help = '为所有工厂补全工厂仓节点，并尝试修复未绑定工厂的工厂仓（旧数据）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只输出计划操作，不修改数据库',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('dry-run：不会写入数据库'))

        def run_writes():
            linked, skipped = _repair_orphan_factory_warehouses(dry_run)
            self.stdout.write(
                self.style.NOTICE(f'孤儿工厂仓：尝试绑定 {linked} 条，跳过（无法唯一推断）{skipped} 条')
            )

            created = 0
            already = 0
            for f in Factory.objects.order_by('id'):
                before = WarehouseNode.objects.filter(
                    warehouse_type='factory',
                    factory_id=f.id,
                    is_active=True,
                ).first()
                if dry_run:
                    if before:
                        already += 1
                    else:
                        stem = f'{(f.location or "").strip()}{(f.workshop or "").strip()}车间'
                        self.stdout.write(
                            self.style.NOTICE(
                                f'[dry-run] 将为工厂「{f.name}」(id={f.id}) 创建工厂仓（约「{stem}工厂仓」）'
                            )
                        )
                        created += 1
                    continue
                ensure_factory_warehouse_for_factory(f)
                after = WarehouseNode.objects.filter(
                    warehouse_type='factory',
                    factory_id=f.id,
                    is_active=True,
                ).first()
                if before:
                    already += 1
                elif after:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'已新建工厂仓「{after.name}」(id={after.id}) ← 工厂「{f.name}」(id={f.id})'
                        )
                    )

            if dry_run:
                self.stdout.write(self.style.NOTICE(f'[dry-run] 小结：将新建约 {created} 个工厂仓，已有 {already} 个工厂无需新建'))
            else:
                self.stdout.write(self.style.SUCCESS(f'完成：新建 {created} 个工厂仓，{already} 个工厂已有工厂仓'))

        if dry_run:
            run_writes()
        else:
            with transaction.atomic():
                run_writes()
