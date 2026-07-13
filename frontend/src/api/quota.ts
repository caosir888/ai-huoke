import api from './client';

export function getQuotaUsage() {
  return api.get('/quota/usage').then(r => r.data);
}
