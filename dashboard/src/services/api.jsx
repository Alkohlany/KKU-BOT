const API_URL = import.meta.env.VITE_API_URL || '/api';

function handle401(res) {
  if (res.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
    return true;
  }
  return false;
}

const api = {
  async get(endpoint) {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}${endpoint}`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (handle401(res)) return;
    if (!res.ok) throw new Error(`GET ${endpoint} failed`);
    return res.json();
  },

  async post(endpoint, data) {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify(data),
    });
    if (handle401(res)) return;
    if (!res.ok) throw new Error(`POST ${endpoint} failed`);
    return res.json();
  },

  async put(endpoint, data) {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify(data),
    });
    if (handle401(res)) return;
    if (!res.ok) throw new Error(`PUT ${endpoint} failed`);
    return res.json();
  },

  async delete(endpoint) {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'DELETE',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (handle401(res)) return;
    if (!res.ok) throw new Error(`DELETE ${endpoint} failed`);
    return res.json();
  },

  getStats: () => api.get('/stats'),
  getResponses: () => api.get('/responses'),
  addResponse: (data) => api.post('/responses', data),
  updateResponse: (id, data) => api.put(`/responses/${id}`, data),
  deleteResponse: (id) => api.delete(`/responses/${id}`),
  deleteAllResponses: () => api.delete('/responses'),
  addResponseWithFile: (formData) => api.postFormData('/responses/upload', formData),
  updateResponseWithFile: (id, formData) => api.putFormData(`/responses/upload/${id}`, formData),
  addResponseWithFileProgress: (formData, onProgress) => api.uploadWithProgress('/responses/upload', formData, onProgress, 'POST'),
  updateResponseWithFileProgress: (id, formData, onProgress) => api.uploadWithProgress(`/responses/upload/${id}`, formData, onProgress, 'PUT'),
  getGroups: () => api.get('/groups'),
  addGroup: (data) => api.post('/groups', data),
  toggleGroup: (id, enabled) => api.put(`/groups/${id}/toggle`, { enabled }),
  getBannedUsers: () => api.get('/users/banned'),
  banUser: (data) => api.post('/users/banned', data),
  unbanUser: (id) => api.delete(`/users/banned/${id}`),
  getActivityLog: () => api.get('/stats/activity'),
  getSettings: () => api.get('/stats/settings'),
  updateSettings: (data) => api.put('/stats/settings', data),
  login: (data) => api.post('/auth/login', data),
  verify: () => api.post('/auth/verify'),

  async postFormData(endpoint, formData) {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: formData,
    });
    if (handle401(res)) return;
    if (!res.ok) throw new Error(`POST ${endpoint} failed`);
    return res.json();
  },

  async putFormData(endpoint, formData) {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}${endpoint}`, {
      method: 'PUT',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: formData,
    });
    if (handle401(res)) return;
    if (!res.ok) throw new Error(`PUT ${endpoint} failed`);
    return res.json();
  },

  uploadWithProgress(endpoint, formData, onProgress, method = 'POST') {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const token = localStorage.getItem('token');

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else if (xhr.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          reject(new Error('Unauthorized'));
        } else {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Network error')));
      xhr.addEventListener('abort', () => reject(new Error('Aborted')));

      xhr.open(method, `${API_URL}${endpoint}`);
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);
    });
  },

  getNews: () => api.get('/news'),
  addNews: (data) => api.post('/news', data),
  addNewsWithFile: (formData) => api.postFormData('/news/upload', formData),
  publishNews: (id, payload = {}) => api.post(`/news/${id}/publish`, payload),
  deleteNews: (id) => api.delete(`/news/${id}`),

  getQuestions: () => api.get('/questions'),
  addQuestion: (data) => api.post('/questions', data),
  updateQuestion: (id, data) => api.put(`/questions/${id}`, data),
  deleteQuestion: (id) => api.delete(`/questions/${id}`),
  addQuestionWithFile: (formData) => api.postFormData('/questions/upload', formData),
  updateQuestionWithFile: (id, formData) => api.putFormData(`/questions/upload/${id}`, formData),
  addQuestionWithFileProgress: (formData, onProgress) => api.uploadWithProgress('/questions/upload', formData, onProgress, 'POST'),
  updateQuestionWithFileProgress: (id, formData, onProgress) => api.uploadWithProgress(`/questions/upload/${id}`, formData, onProgress, 'PUT'),

  getScheduledPosts: () => api.get('/scheduled-posts'),
  addScheduledPost: (data) => api.post('/scheduled-posts', data),
  addScheduledPostWithFile: (formData) => api.postFormData('/scheduled-posts/upload', formData),
  deleteScheduledPost: (id) => api.delete(`/scheduled-posts/${id}`),

  getStudyPlans: () => api.get('/study-plans'),
  addStudyPlan: (data) => api.post('/study-plans', data),
  addStudyPlanWithFile: (formData) => api.postFormData('/study-plans/upload', formData),
  deleteStudyPlan: (id, mode = 'permanent') => api.delete(`/study-plans/${id}?mode=${mode}`),

  getStudyPlanGroups: () => api.get('/study-plans/groups'),
  getStudyPlanGroup: (id) => api.get(`/study-plans/groups/${id}`),
  addStudyPlanGroup: (data) => api.post('/study-plans/groups', data),
  deleteStudyPlanGroup: (id, mode = 'permanent') => api.delete(`/study-plans/groups/${id}?mode=${mode}`),
  publishGroupPlans: (groupId) => api.post(`/study-plans/publish-group/${groupId}`),
  publishPlan: (planId) => api.post(`/study-plans/publish-plan/${planId}`),
  updateStudyPlan: (id, data) => api.put(`/study-plans/${id}`, data),
  updateStudyPlanWithFile: (id, formData) => api.putFormData(`/study-plans/${id}`, formData),
  updateStudyPlanGroup: (id, data) => api.put(`/study-plans/groups/${id}`, data),
};

export default api;
