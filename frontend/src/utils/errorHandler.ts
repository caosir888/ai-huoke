import { message } from 'antd';

export function handleApiError(err: any, fallback?: string): void {
  const msg = err?.friendlyMessage || fallback || '操作失败，请稍后重试';
  message.error(msg);
}

export function showSuccess(msg: string): void {
  message.success(msg);
}
