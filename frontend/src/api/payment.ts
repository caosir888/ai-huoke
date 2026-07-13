import api from './client';

export const listPlans = () => api.get('/payment/plans');

export const createOrder = (planKey: string) =>
  api.post('/payment/order', { plan_key: planKey });
