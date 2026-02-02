import { useState, useMemo } from 'react';
import axios from 'axios';

export const useJobActions = (onJobAdded) => {
  const [submitStatus, setSubmitStatus] = useState(null);
  const [duplicateJobs, setDuplicateJobs] = useState([]);

  // --- טיפול בסטטוסים (DRY) ---
  const handleActionWrapper = async (actionFn) => {
    console.log('🟢 handleActionWrapper starting...');
    setSubmitStatus('sending');
    setDuplicateJobs([]); // נקה כפילויות קודמות
    try {
      await actionFn();
      console.log('✅ Action completed successfully');
      setSubmitStatus('success');
      setTimeout(() => setSubmitStatus(null), 3000);
      onJobAdded(); // רענן את הרשימה
      return true;
    } catch (e) {
      console.error('❌ Error in handleActionWrapper:', e);
      
      // תמיד רענן את הרשימה גם במקרה של שגיאה
      onJobAdded();
      
      // בדיקה אם זו שגיאת כפילות מותאמת (מכמה לינקים)
      if (e.isDuplicateError && e.duplicateData?.urls) {
        setDuplicateJobs(e.duplicateData.urls);
        setSubmitStatus(null);
      } 
      // שגיאת כפילות מהבקאנד (לינק בודד)
      else if (e.response?.status === 409) {
        const detail = e.response.data.detail;
        setDuplicateJobs([{
          url: detail.url,
          date: detail.date,
          company: detail.url
        }]);
        setSubmitStatus(null);
      } 
      else {
        setSubmitStatus('error');
        setTimeout(() => setSubmitStatus(null), 5000);
      }
      return false;
    }
  };

  const handleUrlSubmit = async (parsedLinks, callback) => {
    const result = await handleActionWrapper(async () => {
      const response = await axios.post('http://localhost:8000/api/jobs/url', { urls: parsedLinks });
      
      if (response.data.skipped_urls && response.data.skipped_urls.length > 0) {
        if (response.data.added === 0) {
          const error = new Error('All URLs were duplicates');
          error.isDuplicateError = true;
          error.duplicateData = { urls: response.data.skipped_urls };
          throw error;
        }
        setDuplicateJobs(response.data.skipped_urls);
      }
      if (callback) callback();
    });
    return result;
  };

  const handleTextSubmit = async (text, title, originalUrl = null, isFixModal = false, callback) => {
    return handleActionWrapper(async () => {
      await axios.post('http://localhost:8000/api/jobs/text', {
        text,
        title: title || 'משרה ידנית',
        url: originalUrl
      });
      if (callback) callback();
    });
  };

  const handleRescan = (url) => handleActionWrapper(async () => {
    await axios.delete(`http://localhost:8000/api/jobs`, { params: { url } });
    await axios.post('http://localhost:8000/api/jobs/url', { urls: [url] });
  });

  const handleCancel = async (url) => {
    try {
      await axios.delete(`http://localhost:8000/api/jobs`, { params: { url } });
      onJobAdded();
    } catch (err) { console.error(err); }
  };

  const handleRetry = async (url) => {
    try {
      await axios.post(`http://localhost:8000/api/jobs/retry`, null, { params: { url } });
      onJobAdded();
    } catch (err) { console.error(err); }
  };

  const handleDismissDuplicate = (url) => {
    setDuplicateJobs(prev => prev.filter(job => job.url !== url));
  };

  return {
    submitStatus,
    duplicateJobs,
    setDuplicateJobs,
    handleUrlSubmit,
    handleTextSubmit,
    handleRescan,
    handleCancel,
    handleRetry,
    handleDismissDuplicate
  };
};
