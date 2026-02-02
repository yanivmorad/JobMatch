import React, { useState, useEffect } from 'react';
import { Sparkles, ExternalLink, X, Loader2, CheckCircle } from 'lucide-react';

const ManualFixModal = ({ isOpen, onClose, job, onSubmit, isSubmitting }) => {
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('');

  useEffect(() => {
    if (isOpen && job) {
      setTitle(job.company !== 'Unknown' ? job.company : '');
      setContent('');
    }
  }, [isOpen, job]);

  if (!isOpen || !job) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-[2rem] w-full max-w-2xl shadow-2xl border border-slate-100 flex flex-col max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div>
            <h3 className="text-xl font-bold text-slate-800">תיקון משרה ידני</h3>
            <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-slate-400 font-mono bg-white px-2 py-1 rounded border border-slate-200 truncate max-w-[300px]">
                  {job.url}
                </span>
                <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 text-xs flex items-center gap-1">
                  פתח קישור <ExternalLink size={10} />
                </a>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors text-slate-500">
            <X size={24} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 flex flex-col gap-4">
          <div className="bg-blue-50 text-blue-800 text-sm p-4 rounded-xl flex items-start gap-3">
             <Sparkles className="shrink-0 mt-0.5" size={16} />
             <p>הסורק האוטומטי נכשל. הדבק את טקסט המשרה כאן לניתוח AI ישיר.</p>
          </div>
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">כותרת / שם חברה</label>
            <input 
              type="text" 
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all"
              placeholder="לדוגמה: מפתח Full Stack בחברת X"
            />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-bold text-slate-700 mb-2">תוכן המשרה (הדבק כאן)</label>
            <textarea 
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-48 bg-slate-50 border border-slate-200 rounded-xl p-4 resize-none focus:ring-2 focus:ring-blue-500/20 outline-none transition-all text-sm leading-relaxed"
              placeholder="תיאור המשרה..."
            />
          </div>
        </div>

        <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex justify-end gap-3">
          <button onClick={onClose} className="px-6 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-200 transition-colors">ביטול</button>
          <button 
            onClick={() => onSubmit(job.url, title, content)}
            disabled={!content.trim() || isSubmitting}
            className="px-8 py-3 rounded-xl font-bold bg-blue-600 text-white shadow-lg hover:bg-blue-700 transition-all disabled:opacity-50 flex items-center gap-2"
          >
            {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : <CheckCircle size={20} />}
            שמור ונתח מחדש
          </button>
        </div>
      </div>
    </div>
  );
};

export default ManualFixModal;
