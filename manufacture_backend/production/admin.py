from django.contrib import admin
from .models import Factory, Material, Product, ProductionPlan, ProductionProgress, OutboundRecord

@admin.register(Factory)
class FactoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'workshop')
    search_fields = ('name', 'location', 'workshop')

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('type', 'name', 'quantity', 'unit', 'stock_date')
    search_fields = ('name',)
    list_filter = ('type', 'stock_date')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'colors', 'specifications')
    search_fields = ('name', 'colors', 'specifications')
    list_filter = ()

@admin.register(ProductionPlan)
class ProductionPlanAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'start_date', 'expected_end_date')
    search_fields = ('product__name',)
    list_filter = ('start_date', 'expected_end_date')

@admin.register(ProductionProgress)
class ProductionProgressAdmin(admin.ModelAdmin):
    list_display = ('plan', 'current_quantity', 'status', 'update_time')
    search_fields = ('plan__product__name',)
    list_filter = ('status', 'update_time')

@admin.register(OutboundRecord)
class OutboundRecordAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'outbound_date', 'warehouse')
    search_fields = ('product__name', 'warehouse')
    list_filter = ('outbound_date', 'warehouse')
