import api from './client';

export function submitFeedback(rating: number, content: string) {
  return api.post('/feedback', { rating, content });
}
