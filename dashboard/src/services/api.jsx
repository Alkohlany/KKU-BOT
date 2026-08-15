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

  uploadWithProgress(endpoint, formData, onProgress, method = 'POST') {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open(method, `${API_URL}${endpoint}`);
      
      const token = localStorage.getItem('token');
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }
      
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percent = Math.round((event.loaded * 100) / event.total);
          onProgress(percent);
        }
      };
      
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else if (xhr.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          reject(new Error('Unauthorized'));
        } else {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      };
      
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },

  getStats: () => api.get('/stats'),
  getResponses: () => api.get('/responses'),
  addResponse: (data) => api.post('/responses', data),
  updateResponse: (id, data) => api.put(`/responses/${id}`, data),
  deleteResponse: (id) => api.delete(`/responses/${id}`),
  deleteAllResponses: () => api.delete('/responses'),
  getChannels: () => api.get('/channels'),
  getActiveChannels: () => api.get('/channels/active'),
  addChannel: (data) => api.post('/channels', data),
  updateChannel: (id, data) => api.put(`/channels/${id}`, data),
  toggleChannel: (id) => api.put(`/channels/${id}/toggle`),
  deleteChannel: (id) => api.delete(`/channels/${id}`),
  setOfficialChannel: async (id) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${API_URL}/channels/${id}/official`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (handle401(res)) return;
    if (!res.ok) {
      const err = new Error(`POST /channels/${id}/official failed`);
      err.status = res.status;
      throw err;
    }
    return res.json();
  },
  getBannedUsers: () => api.get('/users/banned'),
  banUser: (data) => api.post('/users/banned', data),
  unbanUser: (id) => api.delete(`/users/banned/${id}`),
  getActivityLog: () => api.get('/stats/activity'),
  getSettings: () => api.get('/stats/settings'),
  updateSettings: (data) => api.put('/stats/settings', data),
  login: (data) => api.post('/auth/login', data),
  verify: () => api.post('/auth/verify'),

  getNews: () => api.get('/news'),
  addNews: (data) => api.post('/news', data),
  publishNews: (id, payload = {}) => api.post(`/news/${id}/publish`, payload),
  deleteNews: (id) => api.delete(`/news/${id}`),
  analyzeNews: (data) => api.post('/news/analyze', data),
  editNews: (id, data) => api.put(`/news/${id}`, data),
  deleteNewsFromChannel: (id) => api.delete(`/news/${id}/channel`),
  deleteAllNews: () => api.delete('/news'),
  relinkNews: (id, data) => api.post(`/news/${id}/relink`, data),
  enhanceContent: (data) => api.post('/news/enhance', data),

  getQuestions: () => api.get('/questions'),
  addQuestion: (data) => api.post('/questions', data),
  updateQuestion: (id, data) => api.put(`/questions/${id}`, data),
  deleteQuestion: (id) => api.delete(`/questions/${id}`),

  getScheduledPosts: () => api.get('/scheduled-posts'),
  addScheduledPost: (data) => api.post('/scheduled-posts', data),
  updateScheduledPost: (id, data) => api.put(`/scheduled-posts/${id}`, data),
  deleteScheduledPost: (id) => api.delete(`/scheduled-posts/${id}`),
  deleteAllScheduledPosts: () => api.delete('/scheduled-posts'),
  addScheduledPostWithFile: (formData) => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_URL}/scheduled-posts/upload`);
      const token = localStorage.getItem('token');
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new Error(xhr.responseText));
        }
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },

  getStudyPlans: () => api.get('/study-plans'),
  addStudyPlan: (data) => api.post('/study-plans', data),
  uploadStudyPlan: (endpoint, formData, method = 'POST') => {
    const token = localStorage.getItem('token');
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open(method, `${API_URL}${endpoint}`);
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else if (xhr.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          reject(new Error('Unauthorized'));
        } else {
          reject(new Error(xhr.responseText));
        }
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },
  deleteStudyPlan: (id, mode = 'permanent') => api.delete(`/study-plans/${id}?mode=${mode}`),

  getStudyPlanGroups: () => api.get('/study-plans/groups'),
  getStudyPlanGroup: (id) => api.get(`/study-plans/groups/${id}`),
  addStudyPlanGroup: (data) => api.post('/study-plans/groups', data),
  deleteStudyPlanGroup: (id, mode = 'permanent') => api.delete(`/study-plans/groups/${id}?mode=${mode}`),
  publishPlan: (planId) => api.post(`/study-plans/publish-plan/${planId}`),
  publishAllPlans: () => api.post(`/study-plans/publish-all`),
  updateStudyPlan: (id, data) => {
    const formData = new FormData();
    if (data.title !== undefined) formData.append('title', data.title);
    if (data.group_id !== undefined) formData.append('group_id', data.group_id || '');
    if (data.file) formData.append('file', data.file);
    if (data.specialization !== undefined) formData.append('specialization', data.specialization || '');
    if (data.link !== undefined) formData.append('link', data.link || '');
    const token = localStorage.getItem('token');
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('PUT', `${API_URL}/study-plans/${id}`);
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else if (xhr.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          reject(new Error('Unauthorized'));
        } else {
          reject(new Error(xhr.responseText));
        }
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },
  updateStudyPlanGroup: (id, data) => api.put(`/study-plans/groups/${id}`, data),

  getBookGroups: () => api.get('/books/groups'),
  getBookGroup: (id) => api.get(`/books/groups/${id}`),
  addBookGroup: (data) => api.post('/books/groups', data),
  updateBookGroup: (id, data) => api.put(`/books/groups/${id}`, data),
  deleteBookGroup: (id, mode = 'permanent') => api.delete(`/books/groups/${id}?mode=${mode}`),
  getBooks: (params) => {
    const q = new URLSearchParams(params).toString();
    return api.get('/books' + (q ? '?' + q : ''));
  },
  addBook: (data) => api.post('/books', data),
  uploadBook: (endpoint, formData, method = 'POST') => {
    const token = localStorage.getItem('token');
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open(method, `${API_URL}${endpoint}`);
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else if (xhr.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          reject(new Error('Unauthorized'));
        } else {
          reject(new Error(xhr.responseText));
        }
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },
  updateBook: (id, data) => {
    const formData = new FormData();
    if (data.title !== undefined) formData.append('title', data.title);
    if (data.group_id !== undefined) formData.append('group_id', data.group_id || '');
    if (data.file) formData.append('file', data.file);
    if (data.author !== undefined) formData.append('author', data.author || '');
    if (data.link !== undefined) formData.append('link', data.link || '');
    const token = localStorage.getItem('token');
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('PUT', `${API_URL}/books/${id}`);
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else if (xhr.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          reject(new Error('Unauthorized'));
        } else {
          reject(new Error(xhr.responseText));
        }
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },
  deleteBook: (id, mode = 'permanent') => api.delete(`/books/${id}?mode=${mode}`),
  publishBook: (bookId) => api.post(`/books/publish-book/${bookId}`),
  publishAllBooks: () => api.post(`/books/publish-all`),

  getSpamPatterns: (params) => {
    const q = new URLSearchParams(params).toString();
    return api.get('/spam' + (q ? '?' + q : ''));
  },
  addSpamPattern: (data) => api.post('/spam', data),
  deleteSpamPattern: (id) => api.delete(`/spam/${id}`),

  // Cloud Files
  getCloudFiles: (folder) => api.get('/files' + (folder ? '?folder=' + encodeURIComponent(folder) : '')),
  deleteCloudFile: (key) => api.delete('/files?key=' + encodeURIComponent(key)),
  renameCloudFile: (oldKey, newName) => {
    var fd = new FormData();
    fd.append('old_key', oldKey);
    fd.append('new_name', newName);
    return api.put('/files/rename', fd);
  },
  moveCloudFile: (key, newFolder) => {
    var fd = new FormData();
    fd.append('key', key);
    fd.append('new_folder', newFolder);
    return api.put('/files/move', fd);
  },
  createCloudFolder: (path) => {
    var fd = new FormData();
    fd.append('path', path);
    return api.post('/files/folder', fd);
  },
  deleteCloudFolder: (path) => api.delete('/files/folder?path=' + encodeURIComponent(path)),
  uploadCloudFile: (file, folder) => {
    var fd = new FormData();
    fd.append('file', file);
    fd.append('folder', folder || 'kku-bot');
    return api.post('/files', fd);
  },
};

export default api;
