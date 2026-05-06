/**
 * 与生产页模板 radio 的 value 及后端 Product.production_template_key 一致。
 * 新增模板时：在此增加一项，并运行后端 sync_template_products（或迁移）补 Product 行。
 */
export const TEMPLATE_TYPE_LABELS = Object.freeze({
  f116: 'F116',
  erDai: '二代',
  728: '728',
  danKu: '单裤',
  g2WaKu: 'G2蛙裤',
  BDU: 'BDU',
  IX7danKu: 'IX7单裤',
})

/** 稳定顺序，供 radio / 列表遍历 */
export const TEMPLATE_KEYS = Object.freeze(Object.keys(TEMPLATE_TYPE_LABELS))

export function templateLabelForKey(key) {
  return TEMPLATE_TYPE_LABELS[key] ?? key ?? ''
}

export function isKnownTemplateKey(key) {
  return key != null && key !== '' && Object.prototype.hasOwnProperty.call(TEMPLATE_TYPE_LABELS, key)
}
