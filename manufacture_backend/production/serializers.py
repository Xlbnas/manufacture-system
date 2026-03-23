from rest_framework import serializers
from .models import Factory, Material, Product, ProductionPlan, ProductionPlanDetail, ProductionProgress, OutboundRecord, Warehouse, Supplier

class FactorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Factory
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class MaterialSerializer(serializers.ModelSerializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), required=False, allow_null=True)
    factory = serializers.PrimaryKeyRelatedField(queryset=Factory.objects.all(), required=False, allow_null=True)
    
    class Meta:
        model = Material
        fields = '__all__'

class MaterialDetailSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer()
    factory = FactorySerializer()
    
    class Meta:
        model = Material
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class ProductionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionPlan
        fields = '__all__'

class ProductionProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionProgress
        fields = '__all__'

class OutboundRecordSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )
    
    class Meta:
        model = OutboundRecord
        fields = ['id', 'product', 'product_id', 'color', 'size', 'quantity', 'outbound_date', 'warehouse']

class WarehouseSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    factory = serializers.PrimaryKeyRelatedField(queryset=Factory.objects.all())
    
    class Meta:
        model = Warehouse
        fields = '__all__'

# 用于列表展示的序列化器，包含产品和工厂的详细信息
class WarehouseDetailSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    factory = FactorySerializer()
    
    class Meta:
        model = Warehouse
        fields = '__all__'

class ProductionPlanDetailSerializer(serializers.ModelSerializer):
    factory = FactorySerializer(read_only=True)
    factory_id = serializers.PrimaryKeyRelatedField(
        queryset=Factory.objects.all(), 
        source='factory', 
        required=False, 
        allow_null=True,
        write_only=True
    )
    
    class Meta:
        model = ProductionPlanDetail
        fields = ['id', 'date', 'plan_type', 'name', 'factory', 'factory_id', 'template', 'models_data', 'sizes_data', 'created_at', 'updated_at']
