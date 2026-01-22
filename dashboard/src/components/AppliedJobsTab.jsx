import React, { useState } from 'react';
import { 
  Calendar, Trash2, ExternalLink, CheckCircle, Target, XCircle, 
  TrendingDown, Archive, AlertCircle, Briefcase, Building2 
} from 'lucide-react';
import JobModal from './JobCard/JobModal';

const AppliedJobsTab = ({ jobs, onRemove }) => {
  const [selectedJob, setSelectedJob] = useState(null);
  
  const formatTime = (dateString) => {
    if (!dateString) return 'לא ידוע';
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('he-IL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  // נתונים סטטיסטיים לראש העמוד
  const stats = {
    total: jobs.length,
    applied: jobs.filter(j => j.user_action === 'applied').length,
    rejected: jobs.filter(j => j.user_action === 'rejected').length,
  };

  if (jobs.length === 0) {
    return (
      <div className="text-center py-24 bg-white rounded-3xl border-2 border-dashed border-slate-200 animate-in fade-in duration-500">
        <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <Briefcase className="w-10 h-10 text-slate-200" />
        </div>
        <h3 className="text-2xl font-black text-slate-800 mb-2">עדיין לא נשלחו משרות</h3>
        <p className="text-slate-500 max-w-md mx-auto">ברגע שתסמן משרות כ"נשלחו", הן יופיעו כאן עם כל הפרטים והניתוח</p>
      </div>
    );
  }

  return (
<div className="bg-gradient-to-br from-amber-50/50 via-orange-50/30 to-rose-50/20 rounded-[2.5rem] border border-amber-200/50 p-8 shadow-[0_12px_40px_-15px_rgba(251,146,60,0.15)]">
  <div className="flex justify-between items-start mb-6">
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 bg-gradient-to-br from-amber-400 to-orange-500 rounded-3xl flex items-center justify-center shadow-lg shadow-amber-100">
          <Briefcase size={24} className="text-white" />
        </div>
        <div>
          <h2 className="text-3xl font-black text-slate-800 tracking-tight">
            משרות בתהליך
          </h2>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-orange-600 font-black text-xl">{stats.total}</span>
            <span className="text-slate-500 text-sm">משרות פעילות</span>
          </div>
        </div>
      </div>
      
      <div className="bg-white/60 rounded-2xl p-4 border border-amber-100 backdrop-blur-sm">
        <p className="text-slate-700 font-medium leading-relaxed">
          <span className="text-orange-500">💡</span> טיפ: עקוב אחרי ההתקדמות שלך ועדכן את הסטטוס של כל משרה
        </p>
      </div>
    </div>
    
    {/* אלמנט דקורטיבי */}
    <div className="hidden lg:flex items-center gap-3">
      <div className="w-3 h-3 bg-amber-400 rounded-full animate-pulse"></div>
      <div className="w-2 h-2 bg-orange-400 rounded-full animate-pulse delay-75"></div>
      <div className="w-3 h-3 bg-rose-400 rounded-full animate-pulse delay-150"></div>
    </div>
  
        
      
         {/* <div className="grid grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4 border border-blue-200">
            <div className="flex items-center gap-2 text-blue-700 font-bold text-sm mb-1">
              <Target size={16} />
              <span>סך הכל משרות</span>
            </div>
            <div className="text-3xl font-black text-blue-800">{stats.total}</div>
          </div>
          <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-xl p-4 border border-emerald-200">
            <div className="flex items-center gap-2 text-emerald-700 font-bold text-sm mb-1">
              <CheckCircle size={16} />
              <span>נשלחו בהצלחה</span>
            </div>
            <div className="text-3xl font-black text-emerald-800">{stats.applied}</div>
          </div>
          <div className="bg-gradient-to-br from-rose-50 to-rose-100 rounded-xl p-4 border border-rose-200">
            <div className="flex items-center gap-2 text-rose-700 font-bold text-sm mb-1">
              <TrendingDown size={16} />
              <span>נדחו</span>
            </div>
            <div className="text-3xl font-black text-rose-800">{stats.rejected}</div>
          </div>
        </div> */}
      </div>

      {/* הטבלה המעוצבת */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-right border-collapse">
            <thead>
              <tr className="bg-slate-50/70 text-slate-500 font-black text-xs uppercase tracking-wider border-b border-slate-200">
                <th className="px-8 py-6 text-right">פרטי המשרה</th>
                <th className="px-8 py-6 text-center">תאריך הגשה</th>
                <th className="px-8 py-6 text-center">ציון התאמה</th>
                <th className="px-8 py-6 text-center">סטטוס נוכחי</th>
                <th className="px-8 py-6 text-left">ניהול פעולות</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((job) => (
                <tr 
                  key={job.url} 
                  className="hover:bg-slate-50 transition-all duration-200 group cursor-pointer"
                  onClick={() => setSelectedJob(job)}
                >
                  <td className="px-8 py-7">
                    <div className="flex flex-col gap-2">
                      <span className="font-black text-slate-900 text-lg group-hover:text-blue-600 transition-colors">
                        {job.job_title}
                      </span>
                      <span className="text-slate-500 text-sm font-medium flex items-center gap-2">
                        <Building2 size={14} className="text-slate-400" />
                        {job.company}
                      </span>
                      <a 
                        href={job.url} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="flex items-center gap-1.5 text-blue-600 text-xs font-black mt-1 hover:underline w-fit"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink size={12}/>
                        צפייה במקור
                      </a>
                    </div>
                  </td>
                  <td className="px-8 py-7 text-center">
                    <div className="inline-flex items-center gap-2 text-slate-600 text-sm font-medium bg-slate-50 px-3 py-1.5 rounded-full">
                      <Calendar size={14} className="text-slate-400"/>
                      {formatTime(job.updated_at || job.analyzed_at)}
                    </div>
                  </td>
                  <td className="px-8 py-7 text-center">
                    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-black border ${
                      job.suitability_score >= 85 
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                      : job.suitability_score >= 50
                      ? 'bg-amber-50 text-amber-700 border-amber-200'
                      : 'bg-rose-50 text-rose-700 border-rose-200'
                    }`}>
                      <Target size={14} />
                      {job.suitability_score}%
                    </div>
                  </td>
                  <td className="px-8 py-7 text-center">
                    {job.user_action === 'applied' ? (
                      <span className="inline-flex items-center gap-2 px-3 py-2 rounded-full text-xs font-black bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle size={14} />
                        נשלח בהצלחה
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-2 px-3 py-2 rounded-full text-xs font-black bg-rose-50 text-rose-700 border border-rose-200">
                        <TrendingDown size={14} />
                        נדחה על ידי המעסיק
                      </span>
                    )}
                  </td>
                  <td className="px-8 py-7 text-left">
                    <div className="flex items-center justify-end gap-3">
                      {job.user_action !== 'rejected' && (
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm('לסמן משרה זו כנדחה? פעולה זו תעדכן את הסטטוס.')) {
                              onRemove(job, 'rejected');
                            }
                          }}
                          className="flex items-center gap-2 px-4 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-600 hover:text-rose-700 rounded-xl transition-all font-bold text-sm border border-rose-200"
                          title="סמן כדחייה"
                        >
                          <TrendingDown size={16} />
                          <span>דחייה</span>
                        </button>
                      )}
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm('להעביר משרה לארכיון? היא תוסר מהרשימה אבל תשמר בהיסטוריה.')) {
                            onRemove(job, 'ignored');
                          }
                        }}
                        className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-slate-700 rounded-xl transition-all font-bold text-sm border border-slate-200"
                        title="העבר לארכיון"
                      >
                        <Archive size={16} />
                        <span>ארכיון</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedJob && (
        <JobModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onAction={onRemove}
        />
      )}
    </div>
  );
};

export default AppliedJobsTab;