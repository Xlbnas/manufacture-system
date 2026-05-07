from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


class Factory(models.Model):
    name = models.CharField(max_length=100, verbose_name='工厂名称')
    location = models.CharField(max_length=100, verbose_name='地区')
    workshop = models.CharField(max_length=50, verbose_name='车间')

    def __str__(self):
        return f'{self.location}{self.workshop}'

    class Meta:
        verbose_name = '工厂'
        verbose_name_plural = '工厂'


class Supplier(models.Model):
    SUPPLIER_TYPE_CHOICES = (
        ('辅料', '辅料'),
        ('坯布', '坯布'),
        ('染厂', '染厂'),
        ('布厂', '布厂'),
    )
    name = models.CharField(max_length=100, verbose_name='供应商名称')
    type = models.CharField(max_length=10, choices=SUPPLIER_TYPE_CHOICES, verbose_name='供应商类型')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '供应商'
        verbose_name_plural = '供应商'


class WarehouseNode(models.Model):
    WAREHOUSE_TYPE_CHOICES = (
        ('factory', '工厂仓'),
        ('local', '本地仓'),
    )
    name = models.CharField(max_length=100, verbose_name='仓库名称', unique=True)
    warehouse_type = models.CharField(max_length=20, choices=WAREHOUSE_TYPE_CHOICES, verbose_name='仓库类型')
    factory = models.ForeignKey(Factory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='所属工厂')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '仓库主数据'
        verbose_name_plural = '仓库主数据'


class Material(models.Model):
    MATERIAL_TYPE_CHOICES = (
        ('raw_fabric', '坯布'),
        ('dyed_fabric', '染色布'),
        ('accessory', '辅料'),
    )
    type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES, verbose_name='物料类型')
    name = models.CharField(max_length=100, verbose_name='物料名称')
    color = models.CharField(max_length=50, verbose_name='颜色', blank=True, null=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='数量', default=Decimal('0.00'))
    unit = models.CharField(max_length=10, verbose_name='单位')
    stock_date = models.DateField(verbose_name='入库日期')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, verbose_name='供应商', blank=True, null=True)
    warehouse = models.ForeignKey(WarehouseNode, on_delete=models.SET_NULL, verbose_name='所属仓库', blank=True, null=True)
    attachment = models.FileField(
        upload_to='material_attachments/',
        blank=True,
        null=True,
        verbose_name='附件',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'doc', 'docx', 'xlsx', 'xls']
            )
        ],
    )
    source_material = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='来源坯布')
    remark = models.TextField(blank=True, default='', verbose_name='备注')

    def __str__(self):
        return f'{self.get_type_display()}-{self.name}'

    class Meta:
        verbose_name = '物料库存'
        verbose_name_plural = '物料库存'


class DyeingOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('receiving', '到货中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    )
    raw_material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name='dyeing_orders', verbose_name='坯布')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='dyeing_orders', verbose_name='染厂')
    output_name = models.CharField(max_length=100, verbose_name='染色布名称')
    output_color = models.CharField(max_length=50, verbose_name='颜色')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='约定产量')
    received_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='已到货数量', default=Decimal('0.00')
    )
    output_warehouse = models.ForeignKey(WarehouseNode, on_delete=models.PROTECT, verbose_name='入库仓')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    dyed_material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_by_dyeing_order')
    lost_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='产出损耗（约定未到货部分）', default=Decimal('0.00')
    )
    loss_note = models.CharField(max_length=500, verbose_name='损耗备注', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'染色单#{self.id}'

    class Meta:
        verbose_name = '染色单'
        verbose_name_plural = '染色单'


class DyeingReceipt(models.Model):
    """染色单分批到货；每批计入本单已收并累加染色布库存（不扣减坯布库存行）。"""
    order = models.ForeignKey(DyeingOrder, on_delete=models.CASCADE, related_name='receipts', verbose_name='染色单')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='本批到货米数')
    receipt_date = models.DateField(verbose_name='到货日期')
    note = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '染色到货记录'
        verbose_name_plural = '染色到货记录'
        ordering = ['-id']


class WeavingOrder(models.Model):
    STATUS_CHOICES = DyeingOrder.STATUS_CHOICES
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='weaving_orders', verbose_name='布厂')
    fabric_name = models.CharField(max_length=100, verbose_name='布料名称')
    fabric_color = models.CharField(max_length=50, verbose_name='颜色', blank=True, default='')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='约定产量')
    received_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='已到货数量', default=Decimal('0.00')
    )
    unit = models.CharField(max_length=10, verbose_name='单位', default='米')
    inbound_warehouse = models.ForeignKey(WarehouseNode, on_delete=models.PROTECT, verbose_name='入库仓')
    expected_delivery = models.DateField(verbose_name='预计交期', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    raw_material = models.ForeignKey(
        Material,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_by_weaving_order',
        verbose_name='汇总坯布库存行',
    )
    note = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'布厂单#{self.id}'

    class Meta:
        verbose_name = '布厂外协单'
        verbose_name_plural = '布厂外协单'


class WeavingReceipt(models.Model):
    order = models.ForeignKey(WeavingOrder, on_delete=models.CASCADE, related_name='receipts', verbose_name='布厂单')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='本批到货米数')
    receipt_date = models.DateField(verbose_name='到货日期')
    note = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '布厂到货记录'
        verbose_name_plural = '布厂到货记录'
        ordering = ['-id']


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='产品名称', unique=True)
    colors = models.CharField(max_length=200, verbose_name='颜色选项', default='')
    specifications = models.CharField(max_length=200, verbose_name='规格参数', default='')
    production_template_key = models.CharField(
        max_length=50,
        verbose_name='排产模板键',
        unique=True,
        help_text='与生产页的模板 radio 取值一致（如 f116、erDai）；每条 Product 对应一条模板线',
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '产品'
        verbose_name_plural = '产品'


class ProductionPlan(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='产品')
    quantity = models.IntegerField(verbose_name='计划数量')
    start_date = models.DateField(verbose_name='开始日期')
    expected_end_date = models.DateField(verbose_name='预计结束日期')

    def __str__(self):
        return f'{self.product}-{self.quantity}'

    class Meta:
        verbose_name = '生产计划'
        verbose_name_plural = '生产计划'


class ProductionPlanDetail(models.Model):
    date = models.DateField(verbose_name='计划日期')
    plan_type = models.CharField(max_length=50, verbose_name='计划类型')
    name = models.CharField(max_length=200, verbose_name='计划名称')
    customer = models.CharField(max_length=100, verbose_name='客户', blank=True, default='')
    cloth_color = models.CharField(max_length=50, verbose_name='用布颜色', blank=True, default='')
    cloth_used = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='用布数量', default=Decimal('0.00'))
    cloth_remaining = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='余料数量', default=Decimal('0.00'))
    factory = models.ForeignKey(Factory, on_delete=models.SET_NULL, verbose_name='目标工厂', blank=True, null=True)
    template = models.CharField(max_length=50, verbose_name='模板类型')
    models_data = models.JSONField(verbose_name='型号数据', default=list)
    sizes_data = models.JSONField(verbose_name='尺码数据', default=list)
    size_completion = models.JSONField(
        verbose_name='各尺码已累计完工数量',
        default=list,
        help_text='结构与 sizes_data 对应：每项含 name 与 completed_quantities 数组（与 quantities 对齐）',
    )
    accessories_delivered = models.BooleanField(verbose_name='辅料已到齐', default=False)
    accessories_delivered_at = models.DateTimeField(verbose_name='辅料到齐标记时间', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return f'{self.date}-{self.name}'

    class Meta:
        verbose_name = '生产计划明细'
        verbose_name_plural = '生产计划明细'
        ordering = ['-date', '-created_at']


class ProductionProgress(models.Model):
    STATUS_CHOICES = (
        ('进行中', '进行中'),
        ('已完成', '已完成'),
        ('暂停', '暂停'),
    )
    plan = models.ForeignKey(ProductionPlan, on_delete=models.CASCADE, verbose_name='生产计划')
    current_quantity = models.IntegerField(verbose_name='当前数量')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name='状态')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return f'{self.plan}-{self.current_quantity}'

    class Meta:
        verbose_name = '生产进度'
        verbose_name_plural = '生产进度'


class Warehouse(models.Model):
    warehouse = models.ForeignKey(WarehouseNode, on_delete=models.CASCADE, related_name='stocks', verbose_name='仓库', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='产品')
    color = models.CharField(max_length=50, verbose_name='颜色')
    size = models.CharField(max_length=20, verbose_name='尺码')
    quantity = models.IntegerField(verbose_name='数量', default=0)

    def clean(self):
        if self.quantity < 0:
            raise ValidationError('库存不能为负数')

    def __str__(self):
        return f'{self.warehouse}-{self.product}-{self.color}-{self.size}-{self.quantity}'

    class Meta:
        verbose_name = '成品库存'
        verbose_name_plural = '成品库存'
        unique_together = ('warehouse', 'product', 'color', 'size')


class TransferOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('reversed', '已冲销'),
    )
    from_warehouse = models.ForeignKey(WarehouseNode, on_delete=models.PROTECT, related_name='transfer_from_orders')
    to_warehouse = models.ForeignKey(WarehouseNode, on_delete=models.PROTECT, related_name='transfer_to_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    note = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'调拨单#{self.id}'

    class Meta:
        verbose_name = '调拨单'
        verbose_name_plural = '调拨单'


class TransferOrderItem(models.Model):
    transfer_order = models.ForeignKey(TransferOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=20)
    quantity = models.IntegerField()

    class Meta:
        verbose_name = '调拨单明细'
        verbose_name_plural = '调拨单明细'


