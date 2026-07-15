import api from './client';

export const bindAccount = (platform: string, authToken: string) =>
  api.post('/platform/accounts/bind', { platform, auth_token: authToken });

export const listAccounts = () => api.get('/platform/accounts');

export const unbindAccount = (id: string) => api.delete(`/platform/accounts/${id}`);

export const getDouyinAuthUrl = () => api.get('/platform/oauth/douyin/authorize');
