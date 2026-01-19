import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import axios from 'axios';

// --- Axios Logging Interceptors ---
axios.interceptors.request.use(request => {
  console.groupCollapsed(`🚀 Request: ${request.method.toUpperCase()} ${request.url}`);
  console.log('Payload:', request.data);
  console.log('Params:', request.params);
  console.groupEnd();
  return request;
});

axios.interceptors.response.use(
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


createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
