import React, { useEffect, useRef, useState } from 'react';
import { RefreshCw, WifiOff } from 'lucide-react';
import { Rail, BottomNav } from './layout/Navigation';
import { TABS } from '../constants/navigation';
import TopBar from './layout/TopBar';
import OverviewScreen from './screens/OverviewScreen';
import ReviewScreen from './screens/ReviewScreen';
import IntakeScreen from './screens/IntakeScreen';
import ApplicationsScreen from './screens/ApplicationsScreen';
import ArchiveScreen from './screens/ArchiveScreen';
import ProfileScreen from './screens/ProfileScreen';
import RunMini from './run/RunMini';
import Button from './ui/Button';
import { Notice, ToastProvider } from './ui/Feedback';
import { useToast } from '../hooks/useToast';
import { taskService } from '../services/taskService';
import { isFailed, isInPipeline, isProcessing } from '../constants/jobStatus';
import { AUTO_ARCHIVE_STATUSES } from '../constants/statusConfig';
import { currentRun, pollDelay, shouldRefetch } from '../utils/queueView';
import { verdictOf, relativeTime } from '../utils/jobView';

// משרות שממתינות לניתוח בזמן שמכסת ה-AI נגמרה: בלי ההסבר הזה הן נראות "תקועות"
const AiQuotaNotice = ({ pausedUntil, waiting }) => {
  if (!pausedUntil || waiting === 0) return null;
  const until = new Date(pausedUntil).toLocaleString('he-IL', { weekday: 'short', hour: '2-digit', minute: '2-digit' });
  return (
    <Notice tone="warn">
      <strong className="font-semibold">הניתוח מושהה עד {until}.</strong>{' '}
      המכסה היומית של Gemini (תוכנית חינמית) נוצלה. {waiting} משרות ממתינות ויימשכו אוטומטית. שום משרה לא אבדה.
    </Notice>
  );
};

const byRecent = (a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at);

const Dashboard = () => {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  // loading -> ready, או error אם הטעינה הראשונה נכשלה (קודם: "אין משרות" בזמן טעינה)
  const [loadState, setLoadState] = useState('loading');
  // הבדיקה האחרונה מול השרת נכשלה: מציגים את הנתונים האחרונים עם הודעה
  const [offline, setOffline] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [reviewSelection, setReviewSelection] = useState(null);
  // כל מודלי ה-AI בהפסקה (המכסה היומית החינמית של Gemini נוצלה) - עד מתי
  const [aiPausedUntil, setAiPausedUntil] = useState(null);
  // "עכשיו" של הניטור החי. מתעדכן בכל טעינה / בדיקת תור, לא בזמן render
  const [now, setNow] = useState(() => Date.now());
  const [syncedAt, setSyncedAt] = useState(null);

  // --- 1. שליפת נתונים ---
  const fetchJobs = async () => {
    try {
      const data = await taskService.getJobs();
      setJobs(data);
      const t = Date.now();
      setNow(t);
      setSyncedAt(t);
      setOffline(false);
      setLoadState('ready');
    } catch (err) {
      console.error('Connection Error', err);
      setOffline(true);
    }
  };

  useEffect(() => {
    let cancelled = false;
    taskService.getJobs()
      .then((data) => {
        if (cancelled) return;
        const t = Date.now();
        setJobs(data);
        setNow(t);
        setSyncedAt(t);
        setLoadState('ready');
      })
      .catch((err) => {
        console.error('Connection Error', err);
        if (!cancelled) setLoadState('error');
      });
    return () => { cancelled = true; };
  }, []);

  const retryInitialLoad = () => {
    setLoadState('loading');
    fetchJobs().then(() => setLoadState((s) => (s === 'loading' ? 'error' : s)));
  };

  // --- 2. Polling (רענון אוטומטי) ---
  // בקשה קטנה למצב התור (ספירה לפי סטטוס + version), ואת הרשימה המלאה מושכים רק כשמשהו השתנה.
  // רץ תמיד: כל 5 שניות כשיש עיבוד, כל 15 כשאין. כשהטאב מוסתר לא בודקים, וכשחוזרים - מיד.
  const queueVersion = useRef(null);
  const jobsRef = useRef(jobs);
  useEffect(() => { jobsRef.current = jobs; }, [jobs]);
  const fetchJobsRef = useRef(fetchJobs);
  useEffect(() => { fetchJobsRef.current = fetchJobs; });
  const hasProcessing = jobs.some((j) => isProcessing(j.status));

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
          setOffline(false);
          if (shouldRefetch(queueVersion.current, snapshot, jobsRef.current)) fetchJobsRef.current();
          else setSyncedAt(Date.now());
          queueVersion.current = snapshot.version;
        } catch (err) {
          console.error('Queue poll failed', err);
          if (!stopped) setOffline(true);
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

  // --- 3. Actions ---
  const handleCardAction = async (job, action, manualData = null) => {
    const url = job.url;
    setJobs((prev) => prev.map((j) => (j.url === url ? {
      ...j,
      user_action: action === 'manual_update' ? j.user_action : action,
      is_archived: action === 'applied' || action === 'ignored',
      application_status: action === 'none' ? 'pending' : j.application_status,
      job_title: manualData?.title || j.job_title,
      company: manualData?.company || j.company,
    } : j)));

    try {
      if (action === 'manual_update') {
        await taskService.updateManualJob({
          url,
          title: manualData.title,
          company: manualData.company,
          description: manualData.description,
        });
      } else {
        await taskService.updateJobAction(url, action);
      }
      await fetchJobs();
      if (action === 'none') toast('המשרה חזרה ללבדיקה');
      if (action === 'manual_update') toast('נשמר. המשרה נשלחה לניתוח');
      return true;
    } catch (err) {
      console.error('Update Failed:', err);
      toast('העדכון נכשל. בדוק שהשרת פועל ונסה שוב.', 'danger');
      await fetchJobs();
      return false;
    }
  };

  const handleUpdateApplicationStatus = async (url, newStatus, isArchived = null) => {
    setJobs((prev) => prev.map((j) => {
      if (j.url !== url) return j;
      const autoArchived = AUTO_ARCHIVE_STATUSES.includes(newStatus);
      const nextArchived = isArchived !== null ? isArchived : autoArchived;
      return { ...j, application_status: newStatus, is_archived: nextArchived };
    }));

    try {
      await taskService.updateApplicationStatus(url, newStatus, isArchived);
      await fetchJobs();
      return true;
    } catch (err) {
      console.error('Status Update Failed:', err);
      toast('עדכון הסטטוס נכשל. בדוק שהשרת פועל ונסה שוב.', 'danger');
      await fetchJobs();
      return false;
    }
  };

  // האישור נעשה בממשק (דיאלוג) לפני הקריאה הזו
  const handleDeleteJob = async (job) => {
    try {
      await taskService.deleteJob(job.url);
      setJobs((prev) => prev.filter((j) => j.url !== job.url));
      toast('המשרה נמחקה');
      return true;
    } catch (err) {
      console.error('Delete Failed', err);
      toast('המחיקה נכשלה', 'danger');
      return false;
    }
  };

  const handleRetryJob = async (url) => {
    try {
      await taskService.retryJob(url);
      await fetchJobs();
      toast('המשרה חזרה לתור');
      return true;
    } catch (err) {
      console.error('Retry Failed', err);
      toast('לא הצלחתי להחזיר את המשרה לתור', 'danger');
      return false;
    }
  };

  const handleClearHistory = async () => {
    try {
      await taskService.clearHistory();
      await fetchJobs();
      toast('הארכיון נוקה');
    } catch (err) {
      console.error('Clear history failed', err);
      toast('ניקוי הארכיון נכשל', 'danger');
    }
  };

  // --- 4. פילטורים ---
  const s = searchQuery.trim().toLowerCase();
  const filteredJobs = !s ? jobs : jobs.filter((j) => (
    (j.job_title || '').toLowerCase().includes(s) ||
    (j.company || '').toLowerCase().includes(s) ||
    (j.url || '').toLowerCase().includes(s)
  ));

  // בעיבוד + נכשלו
  const pendingJobs = filteredJobs.filter((j) => isInPipeline(j.status));
  // הניטור החי: כל משרה בעיבוד + מה שסיים בשעה האחרונה
  const runJobs = currentRun(filteredJobs, now);
  const allRunJobs = currentRun(jobs, now);

  const activeJobs = filteredJobs
    .filter((j) => !j.is_archived && (j.application_status === 'pending' || !j.application_status) && j.status === 'COMPLETED')
    .sort(byRecent);

  const appliedJobs = filteredJobs
    .filter((j) => !j.is_archived && j.application_status && !['pending', 'not_relevant'].includes(j.application_status))
    .sort(byRecent);

  const historyJobs = filteredJobs.filter((j) => j.is_archived).sort(byRecent);

  const failedCount = jobs.filter((j) => isFailed(j.status)).length;
  const processingCount = jobs.filter((j) => isProcessing(j.status)).length;
  const allActive = jobs.filter((j) => !j.is_archived && (j.application_status === 'pending' || !j.application_status) && j.status === 'COMPLETED');
  const recommendedCount = allActive.filter((j) => verdictOf(j) === 'yes').length;

  const badges = {
    active: allActive.length ? { text: allActive.length, tone: 'strong' } : null,
    applied: { text: jobs.filter((j) => !j.is_archived && j.application_status && !['pending', 'not_relevant'].includes(j.application_status)).length },
    add: failedCount ? { text: `${failedCount} נכשל${failedCount > 1 ? 'ו' : ''}`, tone: 'danger' } : processingCount ? { text: `${processingCount} בעיבוד` } : null,
    history: { text: jobs.filter((j) => j.is_archived).length },
  };

  const mainRef = useRef(null);
  const navigate = (tab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0 });
    if (mainRef.current) mainRef.current.scrollTop = 0;
  };
  const openInReview = (job) => {
    setReviewSelection(job.id ?? job.url);
    navigate('active');
  };

  const syncedLabel = syncedAt ? `עודכן ${relativeTime(syncedAt, now)}` : '';
  const filtered = s ? ` · מסונן לפי "${searchQuery.trim()}"` : '';
  const subtitles = {
    dashboard: `${syncedLabel}${hasProcessing ? ' · מתעדכן כל 5 שניות' : ''}`,
    active: `${activeJobs.length} משרות מחכות להחלטה${recommendedCount ? ` · ${recommendedCount} מומלצות להגשה` : ''}${filtered}`,
    applied: `${appliedJobs.length} תהליכים פתוחים${filtered}`,
    add: 'מדביקים הודעות או קישורים. המערכת מוצאת את המשרות ומנתחת כל אחת מהן.',
    history: `משרות שסגרת. אפשר להחזיר כל אחת ללוח.${filtered}`,
    profile: 'על זה הניתוח נשען. שינוי משפיע רק על משרות שינותחו מעכשיו.',
  };
  const tab = TABS.find((t) => t.id === activeTab);

  const screenProps = { now, loading: loadState === 'loading' };

  return (
    <div className="min-h-dvh lg:h-dvh lg:overflow-hidden flex bg-page text-ink" dir="rtl">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:start-2 focus:z-[200] focus:bg-surface focus:px-3 focus:py-2 focus:rounded-md">דילוג לתוכן</a>
      <Rail
        activeTab={activeTab}
        onNavigate={navigate}
        badges={badges}
        footer={<RunMini runJobs={allRunJobs} onOpen={() => navigate('add')} />}
      />
      <div className="flex-1 min-w-0 flex flex-col pb-[calc(60px+env(safe-area-inset-bottom))] lg:pb-0 lg:h-dvh">
        <TopBar
          title={tab.label}
          subtitle={subtitles[activeTab]}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          showSearch={!['add', 'profile', 'dashboard'].includes(activeTab)}
          onAdd={activeTab !== 'add' ? () => navigate('add') : null}
        />
        {offline && loadState === 'ready' && (
          <Notice
            tone="danger"
            role="alert"
            action={<Button size="sm" variant="secondary" onClick={fetchJobs}>נסה עכשיו</Button>}
          >
            אין חיבור לשרת. מוצגים הנתונים האחרונים{syncedAt ? ` (${relativeTime(syncedAt, now)})` : ''}, והבדיקה חוזרת אוטומטית.
          </Notice>
        )}
        <AiQuotaNotice pausedUntil={aiPausedUntil} waiting={jobs.filter((j) => j.status === 'WAITING_FOR_AI').length} />

        <main id="main" ref={mainRef} className="flex-1 min-h-0 flex flex-col lg:overflow-y-auto">
          {loadState === 'error' ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center gap-3 px-6 py-16">
              <span className="size-12 rounded-full bg-danger-soft text-danger inline-flex items-center justify-center"><WifiOff size={22} aria-hidden /></span>
              <h2 className="text-[17px] font-bold">אין חיבור לשרת</h2>
              <p className="text-ink-2 max-w-[44ch]">הדשבורד לא הצליח לטעון משרות. ודא שהשרת רץ (<span dir="ltr" className="font-mono text-[13px]">python src/server.py</span>) ונסה שוב.</p>
              <Button variant="primary" onClick={retryInitialLoad}><RefreshCw size={16} aria-hidden />נסה שוב</Button>
            </div>
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <OverviewScreen
                  {...screenProps}
                  jobs={jobs}
                  activeJobs={allActive}
                  runJobs={allRunJobs}
                  failedCount={failedCount}
                  onNavigate={navigate}
                  onOpenJob={openInReview}
                />
              )}
              {activeTab === 'active' && (
                <ReviewScreen
                  {...screenProps}
                  jobs={activeJobs}
                  selection={reviewSelection}
                  onSelect={setReviewSelection}
                  onAction={handleCardAction}
                  onDelete={handleDeleteJob}
                  onUpdateStatus={handleUpdateApplicationStatus}
                  onRetry={handleRetryJob}
                  onNavigate={navigate}
                  searching={Boolean(s)}
                />
              )}
              {activeTab === 'add' && (
                <IntakeScreen
                  {...screenProps}
                  pendingJobs={pendingJobs}
                  runJobs={runJobs}
                  onJobAdded={fetchJobs}
                  onOpenJob={openInReview}
                />
              )}
              {activeTab === 'applied' && (
                <ApplicationsScreen
                  {...screenProps}
                  jobs={appliedJobs}
                  onAction={handleCardAction}
                  onDelete={handleDeleteJob}
                  onUpdateStatus={handleUpdateApplicationStatus}
                  onRetry={handleRetryJob}
                  onNavigate={navigate}
                  searching={Boolean(s)}
                />
              )}
              {activeTab === 'history' && (
                <ArchiveScreen
                  {...screenProps}
                  jobs={historyJobs}
                  onRestore={handleCardAction}
                  onDelete={handleDeleteJob}
                  onUpdateStatus={handleUpdateApplicationStatus}
                  onRetry={handleRetryJob}
                  onClearHistory={handleClearHistory}
                  searching={Boolean(s)}
                />
              )}
              {activeTab === 'profile' && <ProfileScreen />}
            </>
          )}
        </main>
      </div>
      <BottomNav activeTab={activeTab} onNavigate={navigate} badges={badges} />
    </div>
  );
};

const JobDashboard = () => (
  <ToastProvider>
    <Dashboard />
  </ToastProvider>
);

export default JobDashboard;
