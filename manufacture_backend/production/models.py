from django.db import models
from django.utils import timezone

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
        ('面料', '面料'),
    )
    name = models.CharField(max_length=100, verbose_name='供应商名称')
    type = models.CharField(max_length=10, choices=SUPPLIER_TYPE_CHOICES, verbose_name='供应商类型')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = '供应商'
        verbose_name_plural = '供应商'

class Material(models.Model):
    MATERIAL_TYPE_CHOICES = (
        ('辅料', '辅料'),
        ('面料', '面料'),
    )
    type = models.CharField(max_length=10, choices=MATERIAL_TYPE_CHOICES, verbose_name='原料类型')
    name = models.CharField(max_length=100, verbose_name='原料名称')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='数量')
    unit = models.CharField(max_length=10, verbose_name='单位')
    stock_date = models.DateField(verbose_name='入库日期')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='供应商', blank=True, null=True)
    factory = models.ForeignKey(Factory, on_delete=models.CASCADE, verbose_name='目标工厂', blank=True, null=True)
    attachment = models.ImageField(upload_to='material_attachments/', blank=True, null=True, verbose_name='附件')
    
    def __str__(self):
        return f'{self.type}-{self.name}'
    
    class Meta:
        verbose_name = '原料'
        verbose_name_plural = '原料'

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='产品名称', unique=True)
    colors = models.CharField(max_length=200, verbose_name='颜色选项', default='')
    specifications = models.CharField(max_length=200, verbose_name='规格参数', default='')
    
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
    """详细生产计划模型，用于存储前端生产计划表格数据"""
    date = models.DateField(verbose_name='计划日期')
    plan_type = models.CharField(max_length=50, verbose_name='计划类型')
    name = models.CharField(max_length=200, verbose_name='计划名称')
    factory = models.ForeignKey(Factory, on_delete=models.SET_NULL, verbose_name='目标工厂', blank=True, null=True)
    template = models.CharField(max_length=50, verbose_name='模板类型')
    models_data = models.JSONField(verbose_name='型号数据', default=list)
    sizes_data = models.JSONField(verbose_name='尺码数据', default=list)
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

class OutboundRecord(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='产品')
    color = models.CharField(max_length=50, verbose_name='颜色', blank=True, null=True)
    size = models.CharField(max_length=50, verbose_name='尺码', blank=True, null=True)
    quantity = models.IntegerField(verbose_name='出库数量')
    outbound_date = models.DateField(verbose_name='出库日期')
    warehouse = models.CharField(max_length=100, verbose_name='仓库')
    
    def __str__(self):
        return f'{self.product}-{self.quantity}-{self.outbound_date}'
    
    class Meta:
        verbose_name = '出库记录'
        verbose_name_plural = '出库记录'

class Warehouse(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='产品')
    color = models.CharField(max_length=50, verbose_name='颜色')
    size = models.CharField(max_length=20, verbose_name='尺码')
    quantity = models.IntegerField(verbose_name='数量')
    factory = models.ForeignKey(Factory, on_delete=models.CASCADE, verbose_name='工厂')
    
    def __str__(self):
        return f'{self.product}-{self.color}-{self.size}-{self.quantity}'
    
    class Meta:
        verbose_name = '仓库'
        verbose_name_plural = '仓库'
