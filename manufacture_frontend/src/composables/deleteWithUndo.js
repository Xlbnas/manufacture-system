import { h } from 'vue'
import { ElMessageBox, ElMessage, ElNotification, ElButton } from 'element-plus'
import api from '../utils/axios'

/**
 * 二次确认后执行删除，成功提示，并在 10 秒内提供撤回。
 * 撤回方式二选一：undo.post + undo.payload（POST 重建），或 undo.handler()（本地/自定义）。
 * @param {object} opts
 * @param {string} [opts.confirmTitle]
 * @param {string} opts.confirmMessage
 * @param {() => Promise<void>} opts.deleteFn
 * @param {{ post: string, payload: object } | { handler: () => Promise<void> } | null} [opts.undo]
 * @param {() => void|Promise<void>} [opts.onSuccess] — 删除成功后刷新列表
 * @param {string} [opts.successMessage]
 */
export async function deleteWithUndo(opts) {
  const {
    confirmTitle = '确认删除',
    confirmMessage,
    deleteFn,
    undo = null,
    onSuccess,
    successMessage = '已删除',
  } = opts

  try {
    await ElMessageBox.confirm(confirmMessage, confirmTitle, {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await deleteFn()
  } catch (e) {
    const msg =
      e?.response?.data?.detail ||
      (typeof e?.response?.data === 'object' && JSON.stringify(e.response.data)) ||
      e?.message ||
      '删除失败'
    ElMessage.error(String(msg).slice(0, 200))
    return
  }
  await onSuccess?.()
  ElMessage.success(successMessage)

  const canUndoApi = undo?.post && undo.payload != null
  const canUndoHandler = typeof undo?.handler === 'function'
  if (!canUndoApi && !canUndoHandler) return

  const runUndo = async (not) => {
    try {
      if (canUndoApi) {
        const postPath = undo.post.startsWith('/') ? undo.post : `/${undo.post}`
        await api.post(postPath, undo.payload)
      } else {
        await undo.handler()
      }
      not.close()
      ElMessage.success('已撤回')
      await onSuccess?.()
    } catch (e) {
      const msg =
        e?.response?.data?.detail ||
        (typeof e?.response?.data === 'object' && JSON.stringify(e.response.data)) ||
        e?.message ||
        '撤回失败'
      ElMessage.error(String(msg).slice(0, 200))
    }
  }

  const not = ElNotification({
    title: '已删除',
    duration: 10000,
    message: h('div', { class: 'delete-undo-notification' }, [
      h(
        'p',
        { style: 'margin:0 0 10px 0;font-size:13px;line-height:1.5' },
        canUndoApi
          ? '10 秒内可撤回，将重新创建记录（新 id 可能与原不同）。'
          : '10 秒内可撤回本次操作。'
      ),
      h(ElButton, {
        type: 'primary',
        size: 'small',
        onClick: () => runUndo(not),
      }, { default: () => '撤回' }),
    ]),
  })
}
