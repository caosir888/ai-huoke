import api from './client';

export const sendCode = (phone: string) => api.post('/auth/send-code', { phone });
export const login = (phone: string, code: string) => api.post('/auth/login', { phone, code });
export const getMe = () => api.get('/auth/me');
export const updateProfile = (data: { industry?: string; company_name?: string }) =>
  api.put('/auth/profile', data);
