
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- Axios Logging Interceptors ---
apiClient.interceptors.request.use(request => {
  console.groupCollapsed(`🚀 Request: ${request.method.toUpperCase()} ${request.url}`);
  console.log('Payload:', request.data);
  console.log('Params:', request.params);
  console.groupEnd();
  return request;
});

apiClient.interceptors.response.use(
  response => {
    console.groupCollapsed(`✅ Response: ${response.config.method.toUpperCase()} ${response.config.url}`);
    console.log('Status:', response.status);
    console.log('Data:', response.data);
    console.groupEnd();
    return response;
  },
  error => {
    console.groupCollapsed(`❌ Error: ${error.config?.method.toUpperCase()} ${error.config?.url}`);
    console.error('Message:', error.message);
    console.error('Response:', error.response?.data);
    console.groupEnd();
    return Promise.reject(error);
  }
);

export const taskService = {
  // --- Jobs Methods ---
  
  // שליפת כל המשרות
  getJobs: async () => {
    const response = await apiClient.get('/results');
    return response.data;
  },

  // הוספת משרות חדשות (URLs)
  addJobUrls: async (urls) => {
    const response = await apiClient.post('/jobs/url', { urls });
    return response.data;
  },

  // הוספת משרה ידנית (טקסט חופשי)
  addManualJob: async (text, title, originalUrl = null) => {
    const response = await apiClient.post('/jobs/text', {
      text,
      title: title || 'משרה ידנית',
      url: originalUrl
    });
    return response.data;
  },

  // עדכון פרטי משרה באופן ידני
  updateManualJob: async (data) => {
    const response = await apiClient.post('/jobs/manual-update', data);
    return response.data;
  },

  // הזרקת תוכן ידני למשרה קיימת (למשל אחרי כישלון סריקה)
  updateJobContent: async (jobId, content) => {
    const response = await apiClient.post(`/jobs/${jobId}/manual-content`, { content });
    return response.data;
  },

  // מחיקת משרה
  deleteJob: async (url) => {
    const response = await apiClient.delete('/jobs', { params: { url } });
    return response.data;
  },

  // סריקה מחדש
  retryJob: async (url) => {
    const response = await apiClient.post('/jobs/retry', null, { params: { url } });
    return response.data;
  },

  // עדכון פעולה (User Action) - לוגיקה ישנה
  updateJobAction: async (url, action) => {
    const response = await apiClient.post('/jobs/action', { url, action });
    return response.data;
  },

  // עדכון סטטוס מועמדות (לוגיקה חדשה)
  updateApplicationStatus: async (url, status, isArchived = null) => {
    const payload = { url, status };
    if (isArchived !== null) {
      payload.is_archived = isArchived;
    }
    const response = await apiClient.post('/jobs/application-status', payload);
    return response.data;
  },

  // ניקוי היסטוריה
  clearHistory: async () => {
    const response = await apiClient.delete('/history');
    return response.data;
  },


  // --- Profile Methods ---

  getResume: async () => {
    const response = await apiClient.get('/profile/resume');
    return response.data;
  },

  getContext: async () => {
    const response = await apiClient.get('/profile/context');
    return response.data;
  },

  saveResume: async (content) => {
    const response = await apiClient.post('/profile/resume', { content });
    return response.data;
  },

  saveContext: async (content) => {
    const response = await apiClient.post('/profile/context', { content });
    return response.data;
  }
};
