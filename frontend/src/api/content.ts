import api from './client';

export const generateCopywriting = (keywords: string, style: string, count = 5, industry = '通用', referenceStructure?: any) =>
  api.post('/content/copywriting/generate', { keywords, style, count, industry, reference_structure: referenceStructure });

export const parseLink = (url: string) => api.post('/content/copywriting/parse-link', { url });

export const listCopywriting = (style?: string) =>
  api.get('/content/copywriting/list', { params: { style } });

export const uploadMaterial = (formData: FormData) =>
  api.post('/content/materials/upload', formData);

export const listMaterials = (params?: { folder_id?: string; type?: string }) =>
  api.get('/content/materials', { params });

export const deleteMaterial = (id: string) => api.delete(`/content/materials/${id}`);

export const createFolder = (name: string, parentId?: string) =>
  api.post('/content/folders', { name, parent_id: parentId });

export const listFolders = () => api.get('/content/folders');

export const createEditTask = (data: {
  material_ids: string[];
  copywriting_id?: string;
  template_id?: string;
  count?: number;
  duration?: number;
  ratio?: string;
  voice?: string;
  subtitle_style?: string;
}) => api.post('/content/edit-tasks', data);

export const listEditTasks = () => api.get('/content/edit-tasks');

export const getEditTask = (id: string) => api.get(`/content/edit-tasks/${id}`);
