import React from 'react';
import { Send, XCircle, Loader2, RefreshCw, Trash2, Copy } from 'lucide-react';

const JobActionPanel = ({ job, isManual, onUpdateStatus, onRetry, onDelete, onClose, isRescanLoading, setIsRescanLoading }) => {
  return (
    <div className="bg-slate-900 rounded-3xl p-6 md:p-8">
      <h3 className="text-center font-black text-[10px] uppercase tracking-widest mb-6 text-slate-500">פעולות לביצוע</h3>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <button 
          onClick={() => { onUpdateStatus(job.url, 'applied'); onClose(); }} 
          className="py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-bold text-sm flex flex-col items-center justify-center gap-1.5 transition-all active:scale-95"
        >
          <Send size={18} />
          <span>הוגש</span>
        </button>

        <button 
          onClick={() => { onUpdateStatus(job.url, 'not_relevant'); onClose(); }} 
          className="py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-bold text-sm flex flex-col items-center justify-center gap-1.5 transition-all active:scale-95"
        >
          <XCircle size={18} />
          <span>לא רלוונטי</span>
        </button>

        {!isManual && (
          <button 
            onClick={async () => { 
              setIsRescanLoading(true); 
              await onRetry(job.url); 
              setIsRescanLoading(false); 
              onClose(); 
            }} 
            disabled={isRescanLoading}
            className="py-2.5 bg-amber-600 hover:bg-amber-500 text-white rounded-xl font-bold text-sm flex flex-col items-center justify-center gap-1.5 transition-all active:scale-95 disabled:opacity-50"
          >
            {isRescanLoading ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
            <span>ניתוח מחדש</span>
          </button>
        )}

        <button 
          onClick={() => { onDelete(job); onClose(); }} 
          className="py-2.5 bg-rose-600 hover:bg-rose-500 text-white rounded-xl font-bold text-sm flex flex-col items-center justify-center gap-1.5 transition-all active:scale-95"
        >
          <Trash2 size={18} />
          <span>מחיקה</span>
        </button>
      </div>

      {job.url && (
        <button 
          onClick={() => {
            navigator.clipboard.writeText(job.url);
            alert('הלינק הועתק ללוח');
          }} 
          className="w-full mt-6 py-2 text-slate-500 hover:text-white text-[10px] font-bold flex items-center justify-center gap-2 transition-colors uppercase tracking-widest"
        >
          <Copy size={12} />
          <span>העתק קישור למשרה</span>
        </button>
      )}
    </div>
  );
};

export default JobActionPanel;
