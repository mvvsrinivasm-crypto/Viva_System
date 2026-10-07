import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://viva-system.onrender.com/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('kare_viva_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle unauthorized access
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token if expired or invalid
      localStorage.removeItem('kare_viva_token');
      localStorage.removeItem('kare_viva_user');
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register' && window.location.pathname !== '/') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth Service
export const authService = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
};

// Student Service
export const studentService = {
  getVivas: () => api.get('/student/vivas'),
  startViva: (vivaId) => api.post(`/student/vivas/${vivaId}/start`),
  getSession: (sessionId) => api.get(`/student/sessions/${sessionId}`),
  uploadAudio: (sqId, formData) =>
    api.post(`/student/session-questions/${sqId}/audio`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  updateTranscript: (sqId, transcript) =>
    api.post(`/student/session-questions/${sqId}/transcript`, { transcript }),
  submitAnswer: (sqId, transcript) =>
    api.post(`/student/session-questions/${sqId}/submit`, { transcript }),
  finalizeViva: (sessionId) => api.post(`/student/sessions/${sessionId}/finalize`),
  logViolation: (sessionId, type, metadata) =>
    api.post(`/student/sessions/${sessionId}/violations`, { type, metadata }),
  resolveViolation: (sessionId) =>
    api.post(`/student/sessions/${sessionId}/violations/resolve`),
  checkViolationExpiry: (sessionId) =>
    api.post(`/student/sessions/${sessionId}/violations/check-expiry`),
  getMyResults: () => api.get('/student/results'),
};

// Faculty Service
export const facultyService = {
  getVivas: () => api.get('/faculty/vivas'),
  createViva: (data) => api.post('/faculty/vivas', data),
  getViva: (id) => api.get(`/faculty/vivas/${id}`),
  uploadPDF: (vivaId, formData) =>
    api.post(`/faculty/vivas/${vivaId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getQuestions: (vivaId) => api.get(`/faculty/vivas/${vivaId}/questions`),
  publishViva: (vivaId) => api.post(`/faculty/vivas/${vivaId}/publish`),
  updateStatus: (vivaId, status) => api.patch(`/faculty/vivas/${vivaId}/status`, { status }),
  updateViva: (vivaId, data) => api.put(`/faculty/vivas/${vivaId}`, data),
  getStudents: (vivaId) => api.get(`/faculty/vivas/${vivaId}/students`),
  getStudentsDirectory: () => api.get('/faculty/students'),
  getResults: (vivaId) => api.get(`/faculty/vivas/${vivaId}/results`),
  getAllResults: (vivaId) => api.get('/faculty/results', { params: vivaId ? { viva_id: vivaId } : {} }),
  getExportUrl: (vivaId) => `${API_BASE_URL}/faculty/vivas/${vivaId}/results/export`,
};

// Admin Service
export const adminService = {
  getStats: () => api.get('/admin/stats'),
  getUsers: (role) => api.get('/admin/users', { params: { role } }),
  toggleUserStatus: (id, is_active) => api.patch(`/admin/users/${id}/status`, { is_active }),
  getVivas: () => api.get('/admin/vivas'),
  updateViva: (vivaId, data) => api.put(`/admin/vivas/${vivaId}`, data),
  getResults: () => api.get('/admin/results'),
  editMark: (resultId, new_score, reason) =>
    api.patch(`/admin/results/${resultId}`, { new_score, reason }),
  deleteResult: (resultId, reason) =>
    api.delete(`/admin/results/${resultId}`, { data: { reason } }),
  getAudits: () => api.get('/admin/audits'),
  getViolations: () => api.get('/admin/violations'),
};

export default api;
