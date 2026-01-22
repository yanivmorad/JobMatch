import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Navbar from './Navbar';
import ActiveJobsTab from './ActiveJobsTab';
import AddJobsTab from './AddJobsTab';
import HistoryTab from './HistoryTab';
import AppliedJobsTab from './AppliedJobsTab';
import ProfileTab from './ProfileTab';

const JobDashboard = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  // --- 1. שליפת נתונים ---
  const fetchJobs = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/results');
      setJobs(response.data);
      setLoading(false);
    } catch (err) {
      console.error("Connection Error", err);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  // --- 2. Polling (רענון אוטומטי למשרות בתהליך) ---
  useEffect(() => {
    const hasPending = jobs.some(j => 
      ['NEW', 'WAITING_FOR_SCRAPE', 'SCRAPING', 'WAITING_FOR_AI', 'ANALYZING'].includes(j.status)
    );

    let interval = null;
    if (hasPending) {
      interval = setInterval(fetchJobs, 2000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
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
        await axios.post('http://localhost:8000/api/jobs/manual-update', {
          url: url,
          title: manualData.title,
          company: manualData.company,
          description: manualData.description
        });
      } else {
        await axios.post('http://localhost:8000/api/jobs/action', { url, action });
      }
      
      await fetchJobs(); // סנכרון סופי מול ה-DB
      return true;
    } catch (err) {
      console.error("Update Failed:", err);
      alert("העדכון נכשל. וודא שהשרת פועל.");
      return false;
    }
  };

  const handleDeleteJob = async (job) => {
    if (!window.confirm('למחוק את המשרה לצמיתות?')) return;
    try {
      await axios.delete('http://localhost:8000/api/jobs', { params: { url: job.url } });
      setJobs(prev => prev.filter(j => j.url !== job.url));
    } catch (err) {
      console.error("Delete Failed", err);
    }
  };

  // --- 4. פילטורים ---
  const pendingJobs = jobs.filter(j =>
    ['NEW', 'WAITING_FOR_SCRAPE', 'SCRAPING', 'WAITING_FOR_AI', 'ANALYZING', 'FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status)
  );

  const activeJobs = jobs
    .filter(j => 
      !j.is_archived && 
      (j.status === 'COMPLETED' || ['FAILED_SCRAPE', 'NO_DATA', 'WAITING_FOR_AI', 'ANALYZING'].includes(j.status))
    )
    .sort((a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at));

  const appliedJobs = jobs
    .filter(j => j.user_action === 'applied')
    .sort((a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at));

  const historyJobs = jobs
    .filter(j => j.is_archived && j.user_action !== 'applied')
    .sort((a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at));

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <div className="w-full bg-white shadow-sm sticky top-0 z-50">
        <Navbar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
          counts={{ active: activeJobs.length, pending: pendingJobs.length, applied: appliedJobs.length }}
        />
      </div>

      <main className="flex-1 w-full flex justify-center bg-slate-50/50">
        <div className="w-full max-w-[90%] mx-auto px-4 py-8 flex flex-col">          
          <div className="w-full transition-all duration-500 ease-in-out"> 
            {activeTab === 'dashboard' && (
              <ActiveJobsTab 
                jobs={activeJobs} 
                onAction={handleCardAction}
                onDelete={handleDeleteJob}
                onSwitchTab={setActiveTab} 
                onRefresh={fetchJobs} 
              />
            )}
            
            {activeTab === 'add' && (
              <AddJobsTab pendingJobs={pendingJobs} onJobAdded={fetchJobs} />
            )}

            {activeTab === 'applied' && (
              <AppliedJobsTab jobs={appliedJobs} onRemove={handleCardAction} onRefresh={fetchJobs} />
            )}

            {activeTab === 'history' && (
              <HistoryTab jobs={historyJobs} onRefresh={fetchJobs} onRestore={handleCardAction} />
            )}

            {activeTab === 'profile' && <ProfileTab />}
          </div>
        </div>
      </main>
    </div>
  );
};

export default JobDashboard;