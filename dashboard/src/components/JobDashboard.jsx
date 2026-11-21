import React, { useEffect, useRef, useState } from 'react';
import Navbar from './Navbar';
import ActiveJobsTab from './ActiveJobsTab';
import AddJobsTab from './AddJobsTab/AddJobsTab';
import HistoryTab from './HistoryTab';
import AppliedJobsTab from './AppliedJobsTab/AppliedJobsTab';
import ProfileTab from './ProfileTab';
import OverviewTab from './OverviewTab';
import { taskService } from '../services/taskService';
import { isInPipeline, isProcessing } from '../constants/jobStatus';

const QUEUE_POLL_MS = 5000;

const JobDashboard = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  // --- 1. שליפת נתונים ---
  const fetchJobs = async () => {
    try {
      const data = await taskService.getJobs();
      setJobs(data);
    } catch (err) {
      console.error("Connection Error", err);
    }
  };

  // טעינה ראשונית: setState רק ב-callback של ה-Promise (לא סינכרונית בתוך ה-effect),
  // ולא אחרי שהקומפוננטה ירדה מהמסך
  useEffect(() => {
    let cancelled = false;
    taskService.getJobs()
      .then(data => { if (!cancelled) setJobs(data); })
      .catch(err => console.error("Connection Error", err));
    return () => { cancelled = true; };
  }, []);

  // --- 2. Polling (רענון אוטומטי למשרות בתהליך) ---
  // קודם: כל 2 שניות כל המשרות, כולל תיאורים מלאים (עשרות KB למשרה) - עומס מיותר על
  // השרת וה-DB בענן. עכשיו: כל 5 שניות בקשה קטנה למצב התור, ואת הרשימה המלאה מושכים
  // רק כשמשהו השתנה (version).
  const queueVersion = useRef(null);
  useEffect(() => {
    if (!jobs.some(j => isProcessing(j.status))) return;

    const interval = setInterval(async () => {
      try {
        const { version } = await taskService.getQueueSnapshot();
        const changed = queueVersion.current !== null && version !== queueVersion.current;
        queueVersion.current = version;
        if (changed) fetchJobs();
      } catch (err) {
        console.error("Queue poll failed", err);
      }
    }, QUEUE_POLL_MS);

    return () => clearInterval(interval);
  }, [jobs]);

  // --- 3. Actions (פונקציות עבודה) ---

  const handleCardAction = async (job, action, manualData = null) => {
    const url = job.url;
    
    // עדכון אופטימי לשיפור חווית המשתמש
    setJobs(prev => prev.map(j => j.url === url ? { 
      ...j, 
      user_action: action === 'manual_update' ? j.user_action : action, 
      is_archived: action === 'applied' || action === 'ignored',
      job_title: manualData?.title || j.job_title,
      company: manualData?.company || j.company
    } : j));
    
    try {
      if (action === 'manual_update') {
        await taskService.updateManualJob({
          url: url,
          title: manualData.title,
          company: manualData.company,
          description: manualData.description
        });
      } else {
        await taskService.updateJobAction(url, action);
      }
      
      await fetchJobs(); // סנכרון סופי מול ה-DB
      return true;
    } catch (err) {
      console.error("Update Failed:", err);
      alert("העדכון נכשל. וודא שהשרת פועל.");
      return false;
    }
  };

  const handleUpdateApplicationStatus = async (url, newStatus, isArchived = null) => {
    // עדכון אופטימי
    setJobs(prev => prev.map(j => {
      if (j.url === url) {
        // אם לא הועבר במפורש, נשתמש בלוגיקה האוטומטית
        const autoArchived = ['not_relevant', 'rejected', 'ghosted'].includes(newStatus);
        const nextArchived = isArchived !== null ? isArchived : (autoArchived || j.is_archived);
        
        return { 
          ...j, 
          application_status: newStatus, 
          is_archived: nextArchived 
        };
      }
      return j;
    }));

    try {
      await taskService.updateApplicationStatus(url, newStatus, isArchived);
      await fetchJobs();
      return true;
    } catch (err) {
      console.error("Status Update Failed:", err);
      alert("עדכון הסטטוס נכשל.");
      return false;
    }
  };

  const handleDeleteJob = async (job) => {
    if (!window.confirm('למחוק את המשרה לצמיתות?')) return;
    try {
      await taskService.deleteJob(job.url);
      setJobs(prev => prev.filter(j => j.url !== job.url));
    } catch (err) {
      console.error("Delete Failed", err);
    }
  };

  const handleRetryJob = async (url) => {
    try {
      await taskService.retryJob(url);
      await fetchJobs();
      return true;
    } catch (err) {
      console.error("Retry Failed", err);
      return false;
    }
  };

  // --- 4. פילטורים ---
  const filteredJobs = jobs.filter(j => {
    const s = searchQuery.toLowerCase();
    return (
      (j.job_title || '').toLowerCase().includes(s) ||
      (j.company || '').toLowerCase().includes(s) ||
      (j.url || '').toLowerCase().includes(s)
    );
  });

  // בעיבוד + נכשלו (FAILED_RESOLVE היה חסר כאן, ולכן משרות שנכשלו בפענוח נעלמו מהממשק)
  const pendingJobs = filteredJobs.filter(j => isInPipeline(j.status));

  const activeJobs = filteredJobs
    .filter(j => 
      !j.is_archived && 
      (j.application_status === 'pending' || !j.application_status) &&
      j.status === 'COMPLETED'
    )
    .sort((a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at));

  const appliedJobs = filteredJobs
    .filter(j => !j.is_archived && j.application_status && !['pending', 'not_relevant'].includes(j.application_status))
    .sort((a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at));

  const historyJobs = filteredJobs
    .filter(j => j.is_archived)
    .sort((a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at));

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <div className="w-full bg-white shadow-sm sticky top-0 z-50">
        <Navbar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
          counts={{ active: activeJobs.length, pending: pendingJobs.length, applied: appliedJobs.length }}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
        />
      </div>

      <main className="flex-1 w-full flex justify-center bg-slate-50/50">
        <div className="w-full max-w-[90%] mx-auto px-4 py-8 flex flex-col">          
          <div className="w-full transition-all duration-500 ease-in-out"> 
            {activeTab === 'dashboard' && (
              <OverviewTab
                activeJobs={activeJobs}
                appliedJobs={appliedJobs}
                pendingJobs={pendingJobs}
                onAction={handleCardAction}
                onDelete={handleDeleteJob}
                onUpdateStatus={handleUpdateApplicationStatus}
                onRetry={handleRetryJob}
                onSwitchTab={setActiveTab} 
              />
            )}
            
            {activeTab === 'active' && (
              <ActiveJobsTab 
                jobs={activeJobs} 
                onAction={handleCardAction}
                onDelete={handleDeleteJob}
                onUpdateStatus={handleUpdateApplicationStatus}
                onRetry={handleRetryJob}
                onSwitchTab={setActiveTab} 
                onRefresh={fetchJobs} 
              />
            )}
            
            {activeTab === 'add' && (
              <AddJobsTab pendingJobs={pendingJobs} onJobAdded={fetchJobs} />
            )}

            {activeTab === 'applied' && (
              <AppliedJobsTab 
                jobs={appliedJobs} 
                onRemove={handleCardAction} 
                onUpdateStatus={handleUpdateApplicationStatus} 
                onRetry={handleRetryJob}
                onRefresh={fetchJobs} 
              />
            )}

            {activeTab === 'history' && (
              <HistoryTab 
                jobs={historyJobs} 
                onUpdateStatus={handleUpdateApplicationStatus} 
                onRefresh={fetchJobs} 
                onRestore={handleCardAction} 
                onRetry={handleRetryJob}
              />
            )}

            {activeTab === 'profile' && <ProfileTab />}
          </div>
        </div>
      </main>
    </div>
  );
};

export default JobDashboard;