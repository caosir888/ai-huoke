import api from './client';

export const createPublishTask = (data: {
  video_url: string;
  platform_account_id: string;
  title: string;
  schedule_type?: string;
  schedule_time?: string;
}) => api.post('/publish/tasks', data);

export const listPublishTasks = (status?: string) =>
  api.get('/publish/tasks', { params: { status } });

export const reschedule = (taskId: string, scheduleTime: string) =>
  api.post(`/publish/reschedule/${taskId}`, null, { params: { schedule_time: scheduleTime } });

export const cancelPublishTask = (taskId: string) =>
  api.post(`/publish/cancel/${taskId}`);
