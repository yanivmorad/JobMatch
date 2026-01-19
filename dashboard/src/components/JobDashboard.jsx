// src/components/JobDashboard.jsx
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

  // --- Fetching Logic ---
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

  // Smart Polling: אם יש משרות בתהליך, תרענן כל 2 שניות
  useEffect(() => {
    const hasPending = jobs.some(j => 
      ['pending', 'scraping', 'scraped', 'analyzing'].includes(j.status)
    );

    let interval = null;
    if (hasPending) {
      interval = setInterval(fetchJobs, 2000);
    }
    
    return () => {

      if (interval) clearInterval(interval);
    };
  }, [jobs]);

  // --- Actions ---
const handleCardAction = (job, action) => {
    const url = job.url;
    
    // עדכון אופטימי
    setJobs(prev => prev.map(j => j.url === url ? { 
      ...j, 
      user_action: action, 
      is_archived: action !== 'none',
      updated_at: new Date().toISOString()
    } : j));
    
    // קריאה לשרת
    axios.post('http://localhost:8000/api/jobs/action', { url, action })
      .catch(err => {
        console.error("Failed to update job action", err);
        // כאן אפשר להוסיף לוגיקה שמחזירה את המצב לקדמותו במקרה של שגיאה
      });
  };

  // 1. ממתינים ובתהליך
  const pendingJobs = jobs.filter(j =>
    ['pending', 'scraping', 'scraped', 'analyzing'].includes(j.status)
  );

  // 2. משרות פעילות (הצעות שעוד לא עשית איתן כלום)
  // הן Completed, לא בארכיון, ואין להן פעולת משתמש מוגדרת
  const activeJobs = jobs
    .filter(j => j.status === 'completed' && !j.is_archived)
    .sort((a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at));

  // 3. משרות שנשלחו
  // מציג רק משרות ששלחת אליהן קורות חיים והן עדיין בתהליך
  const appliedJobs = jobs
    .filter(j => j.user_action === 'applied')
    .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at));

  // 4. היסטוריה / ארכיון (משרות שנדחו או סומנו כלא רלוונטיות)
  const historyJobs = jobs
    .filter(j => j.is_archived && j.user_action !== 'applied')
    .sort((a, b) => new Date(b.analyzed_at || b.created_at) - new Date(a.analyzed_at || a.created_at));


return (
    <div className="min-h-screen bg-slate-50 flex flex-col" dir="rtl">
      
      {/* נאובר קבוע למעלה */}
      <div className="w-full bg-white shadow-sm sticky top-0 z-50">
        <Navbar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
          counts={{ 
            active: activeJobs.length, 
            pending: pendingJobs.length,
            applied: appliedJobs.length 
          }}
        />
      </div>

      {/* Main Content Area */}
      <main className="flex-1 w-full flex justify-center bg-slate-50/50">
        
        {/* קונטיינר מרכזי עם מרווחים משופרים מהצדדים */}
        <div className="w-full max-w-7xl mx-auto px-6 md:px-12 lg:px-16 py-8 flex flex-col">
          
          {/* תוכן הטאבים - ללא כותרת מעל, הכל נקי וממורכז */}
          <div className="w-full transition-all duration-500 ease-in-out"> 
            {activeTab === 'dashboard' && (
              <ActiveJobsTab 
                jobs={activeJobs} 
                onAction={handleCardAction}
                onSwitchTab={setActiveTab} 
                onRefresh={fetchJobs} 
              />
            )}
            
            {activeTab === 'add' && (
              <AddJobsTab 
                pendingJobs={pendingJobs} 
                onJobAdded={fetchJobs} 
              />
            )}

            {activeTab === 'applied' && (
              <AppliedJobsTab 
                jobs={appliedJobs} 
                onRemove={handleCardAction} 
                onRefresh={fetchJobs} 
              />
            )}

            {activeTab === 'history' && (
              <HistoryTab 
                jobs={historyJobs} 
                onRefresh={fetchJobs} 
                onRestore={handleCardAction} 
              />
            )}

            {activeTab === 'profile' && (
              <ProfileTab />
            )}
          </div>

        </div>
      </main>
    </div>
  );
};

export default JobDashboard;