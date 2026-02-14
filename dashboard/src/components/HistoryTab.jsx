import React, { useState } from 'react';
import { 
  Trash2, CheckCircle, XCircle, ArchiveRestore, Clock, RotateCcw, History, FolderOpen, Building2, AlertCircle, ChevronDown
} from 'lucide-react';
import { taskService } from '../services/taskService';
import JobModal from './JobModal/JobModal';
import { STATUS_CONFIG } from '../constants/statusConfig';

const HistoryTab = ({ jobs, onRefresh, onRestore, onUpdateStatus, onRetry }) => {
  const [selectedJob, setSelectedJob] = useState(null);
  
  const clearHistory = async () => {
    if (!window.confirm("האם למחוק את כל המשרות שסומנו כ'לא רלוונטי' מההיסטוריה?")) return;
    await taskService.clearHistory();
    onRefresh(); 
  };

  // נתונים סטטיסטיים
  const stats = {
    total: jobs.length,
    rejected: jobs.filter(j => j.application_status === 'rejected').length,
    not_relevant: jobs.filter(j => j.application_status === 'not_relevant').length,
  };

  if (jobs.length === 0) {
    return (
      <div className="text-center py-24 bg-gradient-to-br from-slate-50 to-slate-100 rounded-3xl border-2 border-dashed border-slate-200 animate-in fade-in duration-500">
        <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mx-auto mb-6 shadow-md">
          <FolderOpen className="w-10 h-10 text-slate-300" />
        </div>
        <h3 className="text-2xl font-black text-slate-800 mb-2">היסטוריה ריקה</h3>
        <p className="text-slate-500 max-w-md mx-auto">כאן תופיענה משרות שהסרת מהלוח הראשי כדי שתוכל לנהל אותן בהמשך</p>
      </div>
    );
  }

  return (
    <div className="space-y-7 animate-in fade-in duration-500">
      {/* כותרת משופרת */}
      <div className="bg-gradient-to-br from-slate-50 to-slate-100/50 rounded-3xl border border-slate-200/80 p-7 shadow-[0_8px_32px_-12px_rgba(0,0,0,0.08)] backdrop-blur-sm">
        <div className="flex justify-between items-start">
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-purple-100">
                <History size={24} className="text-white" />
              </div>
              <div>
                <h2 className="text-3xl font-black text-slate-800 tracking-tight">
                  היסטוריית משרות
                </h2>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-indigo-600 font-black text-lg">{stats.total}</span>
                  <span className="text-slate-500 text-sm">פריטים בארכיון</span>
                </div>
              </div>
            </div>
            
            {/* סטטיסטיקות קטנות */}
            <div className="flex gap-3 pt-2">
              <div className="bg-white rounded-xl px-3 py-2 border border-slate-200 flex items-center gap-2">
                <XCircle size={14} className="text-rose-500" />
                <span className="text-rose-600 font-bold text-sm">{stats.rejected} דחויות</span>
              </div>
              <div className="bg-white rounded-xl px-3 py-2 border border-slate-200 flex items-center gap-2">
                <AlertCircle size={14} className="text-slate-500" />
                <span className="text-slate-600 font-bold text-sm">{stats.not_relevant} לא רלוונטיות</span>
              </div>
            </div>
          </div>
          
          <button
            onClick={clearHistory}
            className="text-rose-600 hover:bg-rose-50 px-5 py-3 rounded-2xl text-sm flex items-center gap-2 transition border border-rose-200 hover:shadow-md font-black"
          >
            <Trash2 size={18} /> נקה היסטוריה
          </button>
        </div>
      </div>

      {/* רשמת היסטוריה משופרת */}
      <div className="space-y-5">
        {jobs.map((job) => (
          <div
            key={job.url}
            onClick={() => setSelectedJob(job)}
            className={`
              relative overflow-hidden group
              rounded-2xl border transition-all duration-300 cursor-pointer
              hover:shadow-xl hover:border-slate-300 hover:-translate-y-1
              ${job.user_action === 'rejected' 
                ? 'bg-gradient-to-r from-rose-50/60 to-white border-rose-200/50' 
                : 'bg-gradient-to-r from-slate-50/60 to-white border-slate-200/60'}
            `}
          >
            {/* רצועת צבע דקורטיבית בצד */}
            <div className={`
              absolute left-0 top-0 h-full w-1 transition-all duration-300
              group-hover:w-2
              ${job.application_status === 'rejected' ? 'bg-gradient-to-b from-rose-400 to-rose-500' : 'bg-gradient-to-b from-slate-400 to-slate-500'}
            `}></div>

            <div className="p-6 pl-8">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
                {/* פרטי המשרה */}
                <div className="flex items-center gap-5 flex-1">
                  <div className={`
                    p-3 rounded-2xl transition-transform duration-300 group-hover:scale-110
                    ${job.application_status === 'rejected' 
                      ? 'bg-rose-100 text-rose-700 shadow-rose-100 shadow-md' 
                      : 'bg-slate-100 text-slate-600 shadow-slate-100 shadow-md'}
                  `}>
                    {job.application_status === 'rejected' 
                      ? <XCircle className="w-6 h-6" /> 
                      : <ArchiveRestore className="w-6 h-6" />
                    }
                  </div>
                  
                  <div className="space-y-2 min-w-0 flex-1">
                    <h3 className="text-xl font-black text-slate-800 group-hover:text-blue-600 transition-colors truncate">
                      {job.job_title}
                    </h3>
                    <div className="flex items-center gap-3 flex-wrap">
                      <p className="text-sm text-slate-600 font-medium flex items-center gap-2">
                        <Building2 size={14} className="text-slate-400" />
                        {job.company}
                      </p>
                      
                      {/* Status Management Dropdown */}
                      <div 
                        className="relative group/status"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {(() => {
                          const status = job.application_status || 'pending';
                          const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
                          return (
                            <div 
                              className="px-3 py-1 rounded-full text-[11px] font-black uppercase tracking-wider flex items-center gap-1.5 transition-all border"
                              style={{ 
                                backgroundColor: config.bg, 
                                color: config.color,
                                borderColor: config.border
                              }}
                            >
                              <config.icon size={12} />
                              {config.label}
                              <ChevronDown size={14} />
                            </div>
                          );
                        })()}
                        <select
                          value={job.application_status || 'pending'}
                          onChange={(e) => onUpdateStatus(job.url, e.target.value)}
                          className="absolute inset-0 opacity-0 cursor-pointer w-full"
                        >
                          {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                            <option key={key} value={key}>{config.label}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                {/* פעולות וציון */}
                <div className="flex items-center gap-6 lg:ml-6">
                  {/* ציון התאמה */}
                  <div className="text-center space-y-1">
                    <div className={`
                      font-black text-2xl transition-transform duration-300 group-hover:scale-110
                      ${job.suitability_score > 80 ? 'text-emerald-600' : 
                        job.suitability_score < 50 ? 'text-rose-500' : 
                        'text-slate-500'}
                    `}>
                      {job.suitability_score}%
                    </div>
                    <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                      התאמה
                    </div>
                  </div>

                  {/* כפתור החזרה */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRestore(job, 'none');
                    }}
                    className="
                      flex items-center gap-2 px-5 py-3 
                      bg-gradient-to-r from-blue-50 to-indigo-50 
                      hover:from-blue-100 hover:to-indigo-100
                      text-blue-600 hover:text-blue-700 
                      rounded-2xl font-black text-sm 
                      transition-all duration-300 
                      border border-blue-200/50 hover:shadow-md
                      group-hover:translate-x-1
                    "
                  >
                    <RotateCcw size={16} />
                    <span>החזרה ללוח</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedJob && (
        <JobModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onAction={onRestore}
          onUpdateStatus={onUpdateStatus}
          onRetry={onRetry}
        />
      )}
    </div>
  );
};

export default HistoryTab;