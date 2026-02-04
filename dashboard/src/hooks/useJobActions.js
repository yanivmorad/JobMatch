import { useState, useMemo } from 'react';
import { taskService } from '../services/taskService';

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
      const data = await taskService.addJobUrls(parsedLinks);
      
      if (data.skipped_urls && data.skipped_urls.length > 0) {
        if (data.added === 0) {
          const error = new Error('All URLs were duplicates');
          error.isDuplicateError = true;
          error.duplicateData = { urls: data.skipped_urls };
          throw error;
        }
        setDuplicateJobs(data.skipped_urls);
      }
      if (callback) callback();
    });
    return result;
  };

  const handleTextSubmit = async (text, title, originalUrl = null, isFixModal = false, callback) => {
    return handleActionWrapper(async () => {
      await taskService.addManualJob(text, title, originalUrl);
      if (callback) callback();
    });
  };

  const handleRescan = (url) => handleActionWrapper(async () => {
    await taskService.deleteJob(url);
    await taskService.addJobUrls([url]);
  });

  const handleCancel = async (url) => {
    try {
      await taskService.deleteJob(url);
      onJobAdded();
    } catch (err) { console.error(err); }
  };

  const handleRetry = async (url) => {
    try {
      await taskService.retryJob(url);
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
