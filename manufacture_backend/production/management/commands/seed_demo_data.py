"""
向数据库写入与前端页面一致的演示数据，便于走通工厂 / 原料 / 生产 / 调拨等流程。

用法:
  cd manufacture_backend && . .venv/bin/activate
  python manage.py seed_demo_data          # 首次写入；若已有【演示】数据则跳过
  python manage.py seed_demo_data --force # 删除所有【演示】前缀相关记录后重新写入
"""

from decimal import Decimal

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from production.models import (
    DyeingOrder,
    Factory,
    Material,
    Product,
    ProductionPlan,
    ProductionPlanDetail,
    ProductionProgress,
    Supplier,
    TransferOrder,
    TransferOrderItem,
    Warehouse,
    WarehouseNode,
    WeavingOrder,
)


DEMO = "【演示】"


def _clear_demo():
    TransferOrderItem.objects.filter(transfer_order__note__startswith=DEMO).delete()
    TransferOrder.objects.filter(note__startswith=DEMO).delete()
    # 外协单可能引用演示仓但物料名已改；按仓/供应商一并清掉，避免 PROTECT 阻止删 WarehouseNode
    WeavingOrder.objects.filter(
        Q(supplier__name__startswith=DEMO) | Q(inbound_warehouse__name__startswith=DEMO)
    ).delete()
    DyeingOrder.objects.filter(
        Q(raw_material__name__startswith=DEMO) | Q(output_warehouse__name__startswith=DEMO)
    ).delete()
    Warehouse.objects.filter(product__name__startswith=DEMO).delete()
    ProductionPlanDetail.objects.filter(name__startswith=DEMO).delete()
    ProductionProgress.objects.filter(plan__product__name__startswith=DEMO).delete()
    ProductionPlan.objects.filter(product__name__startswith=DEMO).delete()
    Material.objects.filter(name__startswith=DEMO).delete()
    Product.objects.filter(name__startswith=DEMO).delete()
    WarehouseNode.objects.filter(name__startswith=DEMO).delete()
    Supplier.objects.filter(name__startswith=DEMO).delete()
    Factory.objects.filter(name__startswith=DEMO).delete()


def _sizes_f116_one_model():
    rows = []
    template = {
        "XS": 2.820,
        "S": 2.930,
        "M": 3.040,
        "L": 3.150,
        "XL": 3.270,
        "XXL": 3.380,
    }
    qty_cycle = [12, 30, 45, 38, 22, 10]
    for i, (name, mps) in enumerate(template.items()):
        rows.append(
            {
                "name": name,
                "materialPerSet": mps,
                "quantities": [qty_cycle[i]],
                "editingMaterial": False,
                "editingQuantities": [False],
            }
        )
    return rows


class Command(BaseCommand):
    help = "写入【演示】前缀的测试数据，覆盖工厂/供应商/仓库/物料/产品/计划/库存/调拨草稿等流程。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="删除已有【演示】数据后重新生成",
        )

    def handle(self, *args, **options):
        force = options["force"]
        if Factory.objects.filter(name__startswith=DEMO).exists() and not force:
            self.stdout.write(
                self.style.WARNING(
                    "已存在【演示】数据。若需覆盖请执行: python manage.py seed_demo_data --force"
                )
            )
            return

        with transaction.atomic():
            if force or Factory.objects.filter(name__startswith=DEMO).exists():
                _clear_demo()

            today = timezone.now().date()

            f_wuchang = Factory.objects.create(
                name=f"{DEMO}武昌 八车间",
                location="武昌",
                workshop="八",
            )
            Factory.objects.create(
                name=f"{DEMO}蔡甸 十一车间",
                location="蔡甸",
                workshop="十一",
            )
            Factory.objects.create(
                name=f"{DEMO}汉口 三车间",
                location="汉口",
                workshop="三",
            )
            Factory.objects.create(
                name=f"{DEMO}汉阳 五车间",
                location="汉阳",
                workshop="五",
            )

            sup_acc = Supplier.objects.create(name=f"{DEMO}辅料-华盛织带", type="辅料")
            sup_raw = Supplier.objects.create(name=f"{DEMO}坯布-联纺纺织", type="坯布")
            sup_dye = Supplier.objects.create(name=f"{DEMO}染厂-江南印染", type="染厂")
            sup_weave = Supplier.objects.create(name=f"{DEMO}布厂-联织布业", type="布厂")

            wh_factory = WarehouseNode.objects.create(
                name=f"{DEMO}武昌工厂仓",
                warehouse_type="factory",
                factory=f_wuchang,
            )
            wh_local = WarehouseNode.objects.create(
                name=f"{DEMO}武汉中央本地仓",
                warehouse_type="local",
                factory=None,
            )

            product = Product.objects.create(
                name=f"{DEMO}战术长裤F116",
                colors="军绿,黑色,卡其",
                specifications="S,M,L,XL,XXL",
            )

            # 染色布（生产计划选布、来料计算）
            dyed = Material.objects.create(
                type="dyed_fabric",
                name=f"{DEMO}染色布-F116斜纹",
                color="军绿",
                quantity=Decimal("1580.50"),
                unit="米",
                stock_date=today,
                supplier=sup_dye,
                warehouse=wh_factory,
                remark="演示：用于生产计划选色与耗料演算",
            )
            # 坯布（可做染色单草稿）
            raw = Material.objects.create(
                type="raw_fabric",
                name=f"{DEMO}坯布-本白斜纹",
                color="本白",
                quantity=Decimal("2000.00"),
                unit="米",
                stock_date=today,
                supplier=sup_raw,
                warehouse=wh_factory,
                remark="演示：染色单原料",
            )
            Material.objects.create(
                type="accessory",
                name=f"{DEMO}辅料-YKK拉链5号",
                color="黑色",
                quantity=Decimal("5000.00"),
                unit="条",
                stock_date=today,
                supplier=sup_acc,
                warehouse=wh_factory,
                remark="演示：辅料库存",
            )

            # 成品库存（调拨：从工厂仓到本地仓）
            for color, size, qty in [
                ("军绿", "M", 120),
                ("军绿", "L", 80),
                ("黑色", "M", 60),
            ]:
                Warehouse.objects.create(
                    warehouse=wh_factory,
                    product=product,
                    color=color,
                    size=size,
                    quantity=qty,
                )

            plan = ProductionPlan.objects.create(
                product=product,
                quantity=500,
                start_date=today,
                expected_end_date=today + timedelta(days=21),
            )
            ProductionProgress.objects.create(
                plan=plan,
                current_quantity=320,
                status="进行中",
            )

            models_data = [{"name": "F116", "color": "军绿"}]
            sizes_data = _sizes_f116_one_model()

            ProductionPlanDetail.objects.create(
                date=today,
                plan_type="F116",
                name=f"{DEMO}F116 军绿 排产单A",
                factory=f_wuchang,
                template="f116",
                models_data=models_data,
                sizes_data=sizes_data,
            )
            ProductionPlanDetail.objects.create(
                date=today,
                plan_type="二代",
                name=f"{DEMO}二代 卡其 排产单B",
                factory=f_wuchang,
                template="erDai",
                models_data=[{"name": "二代", "color": "卡其"}],
                sizes_data=[
                    {
                        "name": "M",
                        "materialPerSet": 3.29,
                        "quantities": [40],
                        "editingMaterial": False,
                        "editingQuantities": [False],
                    },
                    {
                        "name": "L",
                        "materialPerSet": 3.405,
                        "quantities": [35],
                        "editingMaterial": False,
                        "editingQuantities": [False],
                    },
                ],
            )

            # 染色单草稿（在「外协订单」登记到货或整单收齐）
            DyeingOrder.objects.create(
                raw_material=raw,
                supplier=sup_dye,
                output_name=f"{DEMO}染色布-成品",
                output_color="丛林",
                quantity=Decimal("400.00"),
                output_warehouse=wh_factory,
                status="draft",
            )

            WeavingOrder.objects.create(
                supplier=sup_weave,
                fabric_name=f"{DEMO}外协坯布-格子",
                fabric_color="本白",
                quantity=Decimal("500.00"),
                unit="米",
                inbound_warehouse=wh_factory,
                expected_delivery=timezone.now().date(),
                status="draft",
                note="演示布厂单，可在外协订单页登记到货",
            )

            order = TransferOrder.objects.create(
                from_warehouse=wh_factory,
                to_warehouse=wh_local,
                status="draft",
                note=f"{DEMO}武昌工厂仓→武汉本地仓（草稿，可点执行调拨）",
            )
            TransferOrderItem.objects.create(
                transfer_order=order,
                product=product,
                color="军绿",
                size="M",
                quantity=30,
            )
            TransferOrderItem.objects.create(
                transfer_order=order,
                product=product,
                color="军绿",
                size="L",
                quantity=20,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "演示数据已写入。请在前端查看带「【演示】」前缀的工厂/产品/仓库等；"
                "调拨页可执行草稿调拨单；生产计划页可加载演示排产。"
            )
        )
        self.stdout.write(f"  染色布 id（军绿）: {dyed.id}，坯布 id: {raw.id}，调拨单 id: {order.id}")
