from rest_framework import serializers

from .models import (
    DyeingOrder,
    DyeingReceipt,
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
    WeavingReceipt,
)


class FactorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Factory
        fields = '__all__'


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class WarehouseNodeSerializer(serializers.ModelSerializer):
    factory_name = serializers.CharField(source='factory.name', read_only=True)

    class Meta:
        model = WarehouseNode
        fields = '__all__'


class MaterialSerializer(serializers.ModelSerializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), required=False, allow_null=True)
    warehouse = serializers.PrimaryKeyRelatedField(queryset=WarehouseNode.objects.all(), required=False, allow_null=True)
    source_material = serializers.PrimaryKeyRelatedField(queryset=Material.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Material
        fields = '__all__'

    def validate(self, attrs):
        typ = attrs.get('type') or (self.instance and self.instance.type)
        attachment = attrs.get('attachment', serializers.empty)
        has_new_file = attachment not in (None, serializers.empty)
        existing_file = bool(self.instance and self.instance.attachment)
        # 新建辅料必须有附件；已存在记录允许补传或仅改其它字段
        if typ == 'accessory' and self.instance is None and not has_new_file:
            raise serializers.ValidationError({'attachment': '辅料入库需上传附件（PDF/Office/图片）'})
        return attrs


class MaterialDetailSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    warehouse = WarehouseNodeSerializer(read_only=True)
    source_material_name = serializers.CharField(source='source_material.name', read_only=True)

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


class WarehouseSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    warehouse = serializers.PrimaryKeyRelatedField(queryset=WarehouseNode.objects.all())

    class Meta:
        model = Warehouse
        fields = '__all__'


class WarehouseDetailSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    warehouse = WarehouseNodeSerializer(read_only=True)

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
        fields = [
            'id', 'date', 'plan_type', 'name', 'customer',
            'cloth_color', 'cloth_used', 'cloth_remaining',
            'factory', 'factory_id', 'template', 'models_data', 'sizes_data',
            'created_at', 'updated_at'
        ]


class DyeingReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DyeingReceipt
        fields = ['id', 'quantity', 'receipt_date', 'note', 'created_at']


class WeavingReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeavingReceipt
        fields = ['id', 'quantity', 'receipt_date', 'note', 'created_at']


class OutsourceReceiptWriteSerializer(serializers.Serializer):
    """登记一笔到货：数量、日期（默认可由视图填当天）、备注。"""
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)
    receipt_date = serializers.DateField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('数量须大于 0')
        return value


class DyeingOrderSerializer(serializers.ModelSerializer):
    raw_material = MaterialDetailSerializer(read_only=True)
    raw_material_id = serializers.PrimaryKeyRelatedField(
        queryset=Material.objects.filter(type='raw_fabric'),
        source='raw_material',
        write_only=True,
    )
    supplier = SupplierSerializer(read_only=True)
    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.filter(type='染厂'),
        source='supplier',
        write_only=True,
    )
    output_warehouse = WarehouseNodeSerializer(read_only=True)
    output_warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseNode.objects.all(),
        source='output_warehouse',
        write_only=True,
    )
    receipts = DyeingReceiptSerializer(many=True, read_only=True)
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = DyeingOrder
        fields = [
            'id', 'raw_material', 'raw_material_id', 'supplier', 'supplier_id', 'output_name', 'output_color',
            'quantity', 'received_quantity', 'remaining_quantity', 'receipts',
            'output_warehouse', 'output_warehouse_id', 'status', 'dyed_material', 'created_at',
        ]
        read_only_fields = ['status', 'received_quantity', 'dyed_material', 'created_at']

    def get_remaining_quantity(self, obj):
        return obj.quantity - obj.received_quantity


class WeavingOrderSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.filter(type='布厂'),
        source='supplier',
        write_only=True,
    )
    inbound_warehouse = WarehouseNodeSerializer(read_only=True)
    inbound_warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseNode.objects.all(),
        source='inbound_warehouse',
        write_only=True,
    )
    raw_material = MaterialDetailSerializer(read_only=True)
    receipts = WeavingReceiptSerializer(many=True, read_only=True)
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = WeavingOrder
        fields = [
            'id', 'supplier', 'supplier_id', 'fabric_name', 'fabric_color', 'quantity', 'received_quantity',
            'remaining_quantity', 'receipts', 'unit', 'inbound_warehouse', 'inbound_warehouse_id',
            'expected_delivery', 'status', 'raw_material', 'note', 'created_at',
        ]
        read_only_fields = ['status', 'received_quantity', 'raw_material', 'created_at']

    def get_remaining_quantity(self, obj):
        return obj.quantity - obj.received_quantity


class TransferOrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), source='product', write_only=True)

    class Meta:
        model = TransferOrderItem
        fields = ['id', 'product', 'product_id', 'color', 'size', 'quantity']


class TransferOrderSerializer(serializers.ModelSerializer):
    from_warehouse = WarehouseNodeSerializer(read_only=True)
    to_warehouse = WarehouseNodeSerializer(read_only=True)
    from_warehouse_id = serializers.PrimaryKeyRelatedField(queryset=WarehouseNode.objects.all(), source='from_warehouse', write_only=True)
    to_warehouse_id = serializers.PrimaryKeyRelatedField(queryset=WarehouseNode.objects.all(), source='to_warehouse', write_only=True)
    items = TransferOrderItemSerializer(many=True)

    class Meta:
        model = TransferOrder
        fields = [
            'id', 'from_warehouse', 'from_warehouse_id', 'to_warehouse', 'to_warehouse_id',
            'status', 'note', 'created_at', 'completed_at', 'items'
        ]
        read_only_fields = ['status', 'created_at', 'completed_at']
