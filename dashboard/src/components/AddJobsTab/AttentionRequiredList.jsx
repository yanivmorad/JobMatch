import React from 'react';
import { AlertCircle, CheckCircle, ExternalLink, RefreshCw, X, Edit3, Trash2 } from 'lucide-react';
import { ActiveQueueList } from '../ActiveQueueList';

const AttentionRequiredList = ({ 
  failedJobs, 
  duplicateJobs, 
  handleRescan, 
  handleDismissDuplicate, 
  handleRetry, 
  handleCancel, 
  setJobToFix, 
  setIsFixModalOpen,
  activeQueue
}) => {
  const totalAttention = failedJobs.length + duplicateJobs.length;

  return (
    <aside className="xl:col-span-4 flex flex-col gap-8 sticky top-8">
      <div className="flex flex-col gap-4">
        <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2 px-1">
          <AlertCircle size={20} className="text-rose-500" /> נדרשת תשומת לב
          {totalAttention > 0 && (
            <span className="bg-rose-100 text-rose-700 text-xs font-bold px-2 py-1 rounded-full">
              {totalAttention}
            </span>
          )}
        </h3>
        
        {totalAttention === 0 ? (
          <div className="bg-emerald-50/50 border border-emerald-100/50 rounded-3xl p-6 text-center">
            <CheckCircle size={28} className="text-emerald-600 mx-auto mb-2" />
            <p className="text-emerald-900 font-bold text-sm">הכל תקין!</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {/* לינקים כפולים */}
            {duplicateJobs.map((dupJob, idx) => (
              <div key={`dup-${idx}`} className="bg-white border border-amber-100 shadow-sm rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden group hover:shadow-md transition-all">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-400"></div>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-amber-600 text-[10px] font-black uppercase tracking-widest">נסרק בעבר</span>
                    <a href={dupJob.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 text-xs flex items-center gap-1">
                      קישור <ExternalLink size={10} />
                    </a>
                  </div>
                  <div className="text-slate-800 font-bold text-sm">
                    {dupJob.company !== 'Unknown' ? dupJob.company : 'משרה'}
                  </div>
                  <div className="bg-amber-50/50 border border-amber-200/50 rounded-lg p-2">
                    <p className="text-amber-800 text-xs font-medium">
                      <span className="font-bold">נסרק לאחרונה: </span>
                      {dupJob.date}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => { 
                      handleRescan(dupJob.url);
                      handleDismissDuplicate(dupJob.url);
                    }} 
                    className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-blue-50 text-blue-700 text-xs font-bold hover:bg-blue-100 transition-colors"
                  >
                    <RefreshCw size={14} /> סרוק מחדש
                  </button>
                  <button 
                    onClick={() => handleDismissDuplicate(dupJob.url)} 
                    className="p-2 rounded-lg bg-slate-50 text-slate-400 hover:text-slate-600 transition-colors"
                    title="התעלם"
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>
            ))}
            
            {/* משרות שנכשלו */}
            {failedJobs.map((job, idx) => (
              <div key={idx} className="bg-white border border-rose-100 shadow-sm rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden group hover:shadow-md transition-all">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-rose-400"></div>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-rose-600 text-[10px] font-black uppercase tracking-widest">
                      {job.status === 'FAILED_SCRAPE' ? 'נכשל בסריקה' : 
                       job.status === 'FAILED_ANALYSIS' ? 'נכשל בניתוח AI' : 
                       'אין מידע'}
                    </span>
                    <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 text-xs flex items-center gap-1">
                      קישור <ExternalLink size={10} />
                    </a>
                  </div>
                  <div className="text-slate-800 font-bold text-sm">
                    {job.company !== 'Unknown' ? job.company : job.job_title !== 'Unknown' ? job.job_title : 'משרה לא מזוהה'}
                  </div>
                  
                  {/* הצגת הודעת השגיאה */}
                  {job.error_log && (
                    <div className="bg-rose-50/50 border border-rose-200/50 rounded-lg p-3 mt-1">
                      <p className="text-rose-800 text-xs font-medium leading-relaxed break-words">
                        <span className="font-bold">שגיאה: </span>
                        {job.error_log}
                      </p>
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => { setJobToFix(job); setIsFixModalOpen(true); }} 
                    className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-rose-50 text-rose-700 text-xs font-bold hover:bg-rose-100 transition-colors"
                  >
                    <Edit3 size={14} /> תיקון ידני
                  </button>
                  <button onClick={() => handleRetry(job.url)} className="p-2 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors">
                    <RefreshCw size={14} />
                  </button>
                  <button onClick={() => handleCancel(job.url)} className="p-2 rounded-lg bg-slate-50 text-slate-400 hover:text-rose-600 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-4 pt-6 border-t border-slate-200">
        <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2 px-1">
          <RefreshCw size={20} className="text-blue-500" /> מעובד כעת
        </h3>
        <ActiveQueueList activeQueue={activeQueue} onRetry={handleRetry} />
      </div>
    </aside>
  );
};

export default AttentionRequiredList;
