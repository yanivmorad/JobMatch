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
import { currentRun, pollDelay, shouldRefetch } from '../utils/queueView';

// משרות שממתינות לניתוח בזמן שמכסת ה-AI נגמרה: בלי ההסבר הזה הן נראות "תקועות"
const AiQuotaBanner = ({ pausedUntil, waiting }) => {
  if (!pausedUntil || waiting === 0) return null;
  const until = new Date(pausedUntil).toLocaleString('he-IL', {
    weekday: 'short', hour: '2-digit', minute: '2-digit',
  });
  return (
    <div className="w-full bg-amber-50 border-b border-amber-200 text-amber-900 text-sm font-medium px-6 py-3 text-center" dir="rtl">
      ⏸️ המכסה היומית של ה-AI (Gemini, תוכנית חינמית) נוצלה. {waiting} משרות ממתינות לניתוח
      והניתוח ימשיך אוטומטית ב-{until}. שום משרה לא אבדה.
    </div>
  );
};

const JobDashboard = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  // כל מודלי ה-AI בהפסקה (המכסה היומית החינמית של Gemini נוצלה) - עד מתי
  const [aiPausedUntil, setAiPausedUntil] = useState(null);
  // "עכשיו" של הניטור החי (איזו משרה סיימה בשעה האחרונה). מתעדכן בכל טעינה / בדיקת תור,
  // לא בזמן render (Date.now() ב-render הוא לא טהור)
  const [now, setNow] = useState(() => Date.now());

  // --- 1. שליפת נתונים ---
  const fetchJobs = async () => {
    try {
      const data = await taskService.getJobs();
      setJobs(data);
      setNow(Date.now());
    } catch (err) {
      console.error("Connection Error", err);
    }
  };

  // טעינה ראשונית: setState רק ב-callback של ה-Promise (לא סינכרונית בתוך ה-effect),
  // ולא אחרי שהקומפוננטה ירדה מהמסך
  useEffect(() => {
    let cancelled = false;
    taskService.getJobs()
      .then(data => { if (!cancelled) { setJobs(data); setNow(Date.now()); } })
      .catch(err => console.error("Connection Error", err));
    return () => { cancelled = true; };
  }, []);

  // --- 2. Polling (רענון אוטומטי) ---
  // בקשה קטנה למצב התור (ספירה לפי סטטוס + version), ואת הרשימה המלאה מושכים רק כשמשהו השתנה.
  // באג: ה-polling רץ רק אם ברשימה שנטענה כבר הייתה משרה בעיבוד - משרות שנוספו מחוץ לדשבורד
  // (תוסף / API / טאב או טלפון אחר) לא הופיעו עד רענון ידני. עכשיו הוא רץ תמיד: כל 5 שניות
  // כשיש עיבוד, כל 15 כשאין. כשהטאב מוסתר לא בודקים (DB בענן כמו Neon נרדם רק כשאין שאילתות),
  // וכשחוזרים אליו - בודקים מיד.
  const queueVersion = useRef(null);
  const jobsRef = useRef(jobs);
  useEffect(() => { jobsRef.current = jobs; }, [jobs]);
  const fetchJobsRef = useRef(fetchJobs);
  useEffect(() => { fetchJobsRef.current = fetchJobs; });
  const hasProcessing = jobs.some(j => isProcessing(j.status));

  useEffect(() => {
    let timer = null;
    let stopped = false;

    const tick = async () => {
      clearTimeout(timer);
      if (stopped) return;
      if (!document.hidden) {
        try {
          const snapshot = await taskService.getQueueSnapshot();
          if (stopped) return;
          setAiPausedUntil(snapshot.ai?.paused_until || null);
          setNow(Date.now());
          if (shouldRefetch(queueVersion.current, snapshot, jobsRef.current)) fetchJobsRef.current();
          queueVersion.current = snapshot.version;
        } catch (err) {
          console.error("Queue poll failed", err);
        }
      }
      if (!stopped) timer = setTimeout(tick, pollDelay(hasProcessing));
    };

    const onVisibilityChange = () => { if (!document.hidden) tick(); };
    document.addEventListener('visibilitychange', onVisibilityChange);
    timer = setTimeout(tick, pollDelay(hasProcessing));
    return () => {
      stopped = true;
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [hasProcessing]);

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

  // הניטור החי: כל משרה בעיבוד + מה שסיים בשעה האחרונה, עם המצב של כל קישור
  const runJobs = currentRun(filteredJobs, now);

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

      <AiQuotaBanner pausedUntil={aiPausedUntil} waiting={jobs.filter(j => j.status === 'WAITING_FOR_AI').length} />

      <main className="flex-1 w-full flex justify-center bg-slate-50/50">
        <div className="w-full max-w-[90%] mx-auto px-4 py-8 flex flex-col">          
          <div className="w-full transition-all duration-500 ease-in-out"> 
            {activeTab === 'dashboard' && (
              <OverviewTab
                activeJobs={activeJobs}
                appliedJobs={appliedJobs}
                pendingJobs={pendingJobs}
                runJobs={runJobs}
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