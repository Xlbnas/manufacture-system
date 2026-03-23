import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'manufacture_project.settings')
django.setup()

from production.models import Warehouse

# 清除Warehouse表中的所有数据
Warehouse.objects.all().delete()
print("Warehouse table cleared successfully!")
