"""与前端 productionTemplates.js 及排产模板 radio 取值一致（单一事实来源在后端用于校验与种子）。"""

# 顺序与前端 TEMPLATE_KEYS 一致
TEMPLATE_LABELS = {
    'f116': 'F116',
    'erDai': '二代',
    '728': '728',
    'danKu': '单裤',
    'g2WaKu': 'G2蛙裤',
    'BDU': 'BDU',
    'IX7danKu': 'IX7单裤',
}

TEMPLATE_KEYS = tuple(TEMPLATE_LABELS.keys())


def default_display_name_for_key(key: str) -> str:
    return TEMPLATE_LABELS.get(key, key or '')


def is_canonical_template_key(key: str) -> bool:
    return bool(key) and key in TEMPLATE_LABELS


def sync_template_product_rows():
    """为每个已知模板键确保存在一条 Product；仅新建缺失行，不覆盖已有名称。"""
    # 延后导入，避免 apps 未就绪时循环引用
    from .models import Product

    created_keys = []
    default_specs = 'XS,S,M,L,XL,XXL'
    for key, label in TEMPLATE_LABELS.items():
        _, was_created = Product.objects.get_or_create(
            production_template_key=key,
            defaults={
                'name': label,
                'colors': '',
                'specifications': default_specs,
            },
        )
        if was_created:
            created_keys.append(key)
    return created_keys
