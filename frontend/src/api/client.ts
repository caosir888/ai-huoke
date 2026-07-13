import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 60000,
});

// Request interceptor — attach Bearer token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — unified error handling
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
      return Promise.reject(err);
    }

    // Network error
    if (!err.response) {
      err.friendlyMessage = '网络连接失败，请检查网络后重试';
      return Promise.reject(err);
    }

    // Server error with detail message
    const detail = err.response.data?.detail;
    if (detail) {
      err.friendlyMessage = typeof detail === 'string' ? detail : JSON.stringify(detail);
    }

    // Fallback messages by status code
    if (!err.friendlyMessage) {
      const statusMessages: Record<number, string> = {
        400: '请求参数有误，请检查输入',
        403: '权限不足，请升级套餐',
        404: '请求的资源不存在',
        409: '操作冲突，请刷新后重试',
        413: '上传文件过大',
        429: '操作太频繁，请稍后重试',
        500: '服务器繁忙，请稍后重试',
        502: '服务暂不可用，请稍后重试',
        503: '服务维护中，请稍后重试',
      };
      err.friendlyMessage = statusMessages[err.response?.status] || `请求失败 (${err.response?.status})`;
    }

    return Promise.reject(err);
  },
);

export default api;
