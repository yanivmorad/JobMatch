import React from 'react';
import { 
  PlusCircle, 
  Search, 
  Bell, 
  LayoutDashboard, 
  Send, 
  CheckCircle, 
  Calendar, 
  Sparkles, 
  ArrowRight, 
  Building2, 
  ExternalLink,
  Clock,
  Briefcase,
  Target,
  BarChart3,
  TrendingUp,
  Brain,
  History,
  MoreVertical,
  ChevronLeft,
  AlertCircle
} from 'lucide-react';
import JobCard from './JobCard';
import { AppliedJobsTable } from './AppliedJobsTab';
import { ActiveQueueList } from './ActiveQueueList';

const OverviewTab = ({ 
  jobs, 
  activeJobs, 
  appliedJobs, 
  pendingJobs, 
  onSwitchTab, 
  onAction, 
  onDelete 
}) => {
  // Statistics
  const analysisCount = pendingJobs.length;
  const submissionsThisWeek = appliedJobs.filter(j => {
    const appliedDate = new Date(j.updated_at || j.analyzed_at);
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    return appliedDate > oneWeekAgo;
  }).length;
  
  const highMatchCount = activeJobs.filter(j => j.suitability_score >= 85).length;

  // Separation of pending jobs
  const failedJobs = pendingJobs.filter(j => 
    ['FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status)
  );
  
  const processingJobs = pendingJobs.filter(j => 
    !['FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status)
  );

  // Recent data subsets
  const recommendedJobs = activeJobs.slice(0, 3);
  const recentApplied = appliedJobs.slice(0, 5);
  const activeQueue = processingJobs.slice(0, 4);

  return (
    <div className="flex flex-col gap-8 animate-in fade-in duration-500 pb-20">
      
      {/* 1. Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto px-4 w-full">
        {/* כרטיס 1: משרות בניתוח */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4 group hover:border-blue-200 transition-all">
          <div className="size-12 shrink-0 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600 group-hover:scale-110 transition-transform">
            <BarChart3 size={22} />
          </div>
          <div>
            <p className="text-slate-500 text-[11px] font-bold uppercase tracking-wider">משרות בניתוח</p>
            <p className="text-2xl font-black text-slate-900 mt-0.5">{analysisCount}</p>
          </div>
        </div>

        {/* כרטיס 2: הגשות השבוע */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4 group hover:border-emerald-200 transition-all">
          <div className="size-12 shrink-0 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600 group-hover:scale-110 transition-transform">
            <CheckCircle size={22} />
          </div>
          <div>
            <p className="text-slate-500 text-[11px] font-bold uppercase tracking-wider">הגשות השבוע</p>
            <p className="text-2xl font-black text-slate-900 mt-0.5">{submissionsThisWeek}</p>
          </div>
        </div>

        {/* כרטיס 3: התאמות גבוהות */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4 group hover:border-amber-200 transition-all">
          <div className="size-12 shrink-0 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600 group-hover:scale-110 transition-transform">
            <TrendingUp size={22} />
          </div>
          <div>
            <p className="text-slate-500 text-[11px] font-bold uppercase tracking-wider">התאמות גבוהות</p>
            <p className="text-2xl font-black text-slate-900 mt-0.5">{highMatchCount}</p>
          </div>
        </div>
      </div>

      <div className="flex flex-col xl:flex-row gap-8">
        
        {/* 2. Main content area (Left in LTR, Right in RTL) */}
        <div className="flex-1 flex flex-col gap-10 min-w-0">
          
          {/* Recommended Section */}
          <section>
            <div className="flex items-center justify-between mb-6 px-1">
              <h2 className="text-xl font-black text-slate-800 flex items-center gap-3">
                <div className="p-2 bg-blue-600 rounded-lg">
                  <Sparkles size={18} className="text-white" />
                </div>
                מומלץ עבורך (דורש סקירה)
              </h2>
              <button 
                onClick={() => onSwitchTab('active')}
                className="text-sm font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1 group"
              >
                צפה בהכל
                <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
              </button>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-6">
              {recommendedJobs.length > 0 ? (
                recommendedJobs.map(job => (
                  <JobCard 
                    key={job.url} 
                    job={job} 
                    onAction={onAction} 
                    onDelete={onDelete} 
                  />
                ))
              ) : (
                <div className="col-span-full py-16 text-center bg-white rounded-3xl border-2 border-dashed border-slate-100 text-slate-400">
                  אין משרות להצגה כרגע
                </div>
              )}
            </div>
          </section>

          {/* Recent Applications Section */}
          <section>
            <div className="flex items-center justify-between mb-6 px-1">
              <h2 className="text-xl font-black text-slate-800 flex items-center gap-3">
                <div className="p-2 bg-slate-800 rounded-lg">
                  <History size={18} className="text-white" />
                </div>
                הגשות אחרונות
              </h2>
              <button 
                onClick={() => onSwitchTab('applied')}
                className="text-sm font-bold text-blue-600 hover:text-blue-700"
              >
                צפה בכל ההיסטוריה
              </button>
            </div>

            <AppliedJobsTable 
              jobs={recentApplied} 
              onAction={onAction} 
              onRowClick={() => onSwitchTab('applied')}
            />
          </section>
        </div>

        {/* 3. Side panel - Monitoring (Righthand in LTR, Lefthand in RTL) */}
        <aside className="w-full xl:w-80 flex flex-col gap-6">
          
         

          {/* Process Monitoring */}
          <div className="bg-white border border-slate-200 rounded-2xl flex flex-col overflow-hidden shadow-sm">
            <div className="p-5 border-b border-slate-100">
              <h3 className="text-sm font-black text-slate-800 flex items-center gap-2">
                <Brain size={16} className="text-blue-600" />
                ניטור תהליכים חי
              </h3>
              <p className="text-[10px] text-slate-400 mt-1 uppercase font-bold tracking-tight">Real-time Analysis Queue</p>
            </div>
            
            <div className="p-5 space-y-6">
              {/* Failed Jobs Alert */}
              {failedJobs.length > 0 && (
                <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl flex flex-col gap-2 animate-pulse">
                  <div className="flex items-center gap-2 text-rose-700 font-bold text-sm">
                    <AlertCircle size={16} />
                    עיבוד נכשל ({failedJobs.length} משרות)
                  </div>
                  <button 
                    onClick={() => onSwitchTab('add')}
                    className="text-[11px] text-rose-600 font-black hover:underline underline-offset-4 flex items-center gap-1"
                  >
                    לחץ כאן לתיקון ידני
                    <ChevronLeft size={12} />
                  </button>
                </div>
              )}

              <ActiveQueueList 
                activeQueue={activeQueue} 
              />
            </div>

            <div className="p-4 bg-slate-50/50 border-t border-slate-100">
              <button 
                onClick={() => onSwitchTab('add')}
                className="w-full py-2 bg-white border border-slate-200 rounded-lg text-[11px] font-bold text-slate-600 hover:bg-slate-50 transition-colors shadow-sm"
              >
                ניהול תור ההזנות
              </button>
            </div>
          </div>

    

        </aside>
      </div>
    </div>
  );
};

export default OverviewTab;
