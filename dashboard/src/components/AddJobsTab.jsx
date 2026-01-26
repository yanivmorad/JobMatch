import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { 
  Link as LinkIcon, Send, Loader2, FileText, 
  CheckCircle, Sparkles, AlertCircle, 
  RefreshCw, Trash2, Edit3, ExternalLink, X, Brain, Search, Clock
} from 'lucide-react';
import { ActiveQueueList } from './ActiveQueueList';


// --- קומפוננטת Modal לתיקון ידני ---
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
        
        {/* Header */}
        <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div>
            <h3 className="text-xl font-bold text-slate-800">תיקון משרה ידני</h3>
            <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-slate-400 font-mono bg-white px-2 py-1 rounded border border-slate-200 truncate max-w-[300px]">
                  {job.url}
                </span>
                <a 
                  href={job.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-500 hover:text-blue-700 hover:underline text-xs flex items-center gap-1"
                >
                  פתח קישור <ExternalLink size={10} />
                </a>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors text-slate-500">
            <X size={24} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 flex flex-col gap-4">
          <div className="bg-blue-50 text-blue-800 text-sm p-4 rounded-xl flex items-start gap-3">
             <Sparkles className="shrink-0 mt-0.5" size={16} />
             <p>הסורק האוטומטי נכשל. העתק את הטקסט מהאתר והדבק אותו כאן - המערכת תדלג על הסריקה ותעבור ישירות לניתוח AI, אך תשמור את הקישור המקורי.</p>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">כותרת / שם חברה</label>
            <input 
              type="text" 
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all"
              placeholder="לדוגמה: מפתח Full Stack בחברת X"
            />
          </div>

          <div className="flex-1">
            <label className="block text-sm font-bold text-slate-700 mb-2">תוכן המשרה (הדבק כאן)</label>
            <textarea 
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-48 bg-slate-50 border border-slate-200 rounded-xl p-4 resize-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all text-sm leading-relaxed"
              placeholder="תיאור המשרה, דרישות, וכל מידע רלוונטי..."
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-6 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-200 transition-colors"
          >
            ביטול
          </button>
          <button 
            onClick={() => onSubmit(job.url, title, content)}
            disabled={!content.trim() || isSubmitting}
            className="px-8 py-3 rounded-xl font-bold bg-blue-600 text-white shadow-lg shadow-blue-200 hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50 flex items-center gap-2"
          >
            {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : <CheckCircle size={20} />}
            שמור ונתח מחדש
          </button>
        </div>
      </div>
    </div>
  );
};


const AddJobsTab = ({ pendingJobs, onJobAdded }) => {
  const [rawInput, setRawInput] = useState('');
  const [parsedLinks, setParsedLinks] = useState([]);
  const [submitStatus, setSubmitStatus] = useState(null); 
  const [localJobs, setLocalJobs] = useState([]);
  
  // States for general manual text input
  const [textInput, setTextInput] = useState('');
  const [textTitle, setTextTitle] = useState('');

  // States for the Modal
  const [isFixModalOpen, setIsFixModalOpen] = useState(false);
  const [jobToFix, setJobToFix] = useState(null);

  // --- לוגיקה ---
  useEffect(() => {
    if (!rawInput) {
      setParsedLinks([]);
      return;
    }
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const matches = rawInput.match(urlRegex) || [];
    const uniqueLinks = [...new Set(matches.map(link => link.replace(/[.,;]$/, "")) )];
    setParsedLinks(uniqueLinks);
  }, [rawInput]);

  useEffect(() => {
    if (pendingJobs.length > 0) {
      const serverUrls = new Set(pendingJobs.map(j => j.url));
      setLocalJobs(prev => prev.filter(local => !serverUrls.has(local.url)));
    }
  }, [pendingJobs]);

  const handleUrlSubmit = async () => {
    if (parsedLinks.length === 0) return;
    setSubmitStatus('sending');
    try {
      await axios.post('http://localhost:8000/api/jobs/url', { urls: parsedLinks });
      setRawInput('');
      setParsedLinks([]); 
      setSubmitStatus('success');
      setTimeout(() => setSubmitStatus(null), 3000);
      onJobAdded(); 
    } catch (e) {
      setSubmitStatus('error');
    }
  };

  // עדכנתי את הפונקציה לקבל גם originalUrl
  const handleTextSubmit = async (text, title, originalUrl = null) => {
    if (!text.trim()) return;
    setSubmitStatus('sending');
    try {
      await axios.post('http://localhost:8000/api/jobs/text', {
        text: text,
        title: title || 'משרה ידנית',
        url: originalUrl // שולחים את ה-URL המקורי אם קיים
      });

      if (!isFixModalOpen) {
        setTextInput('');
        setTextTitle('');
      }
      setSubmitStatus('success');
      setTimeout(() => setSubmitStatus(null), 3000);
      onJobAdded();
      return true;
    } catch (e) {
      setSubmitStatus('error');
      return false;
    }
  };

  const handleFixSubmit = async (originalUrl, title, content) => {
    // כאן הקסם קורה: שולחים לניתוח טקסט (מדלג על סריקה) אבל עם ה-URL המקורי
    const success = await handleTextSubmit(content, title, originalUrl);
    
    if (success) {
      // מוחקים את הג'וב המקורי שנכשל
      await handleCancel(originalUrl);
      setIsFixModalOpen(false);
      setJobToFix(null);
    }
  };

  const handleCancel = async (url) => {
    try {
      await axios.delete(`http://localhost:8000/api/jobs`, { params: { url } });
      onJobAdded(); 
    } catch (err) {
      console.error("Failed to cancel job", err);
    }
  };

  const handleRetry = async (url) => {
    try {
      await axios.post(`http://localhost:8000/api/jobs/retry`, null, { params: { url } });
      onJobAdded();
    } catch (err) {
      console.error("Failed to retry job", err);
    }
  };


  const { activeQueue, failedJobs } = useMemo(() => {
    const serverUrlSet = new Set(pendingJobs.map(j => j.url));
    const uniqueLocalJobs = localJobs.filter(j => !serverUrlSet.has(j.url));
    const all = [...pendingJobs, ...uniqueLocalJobs];
    
    return {
      activeQueue: all.filter(j => !['FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status)),
      failedJobs: all.filter(j => ['FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status))
    };
  }, [pendingJobs, localJobs]);

  return (
    <div className="w-full min-h-screen bg-slate-50/50" dir="rtl">
      
      {/* Modal Integration */}
      <ManualFixModal 
        isOpen={isFixModalOpen}
        onClose={() => setIsFixModalOpen(false)}
        job={jobToFix}
        onSubmit={handleFixSubmit}
        isSubmitting={submitStatus === 'sending'}
      />

      <div className="max-w-[1600px] mx-auto w-full px-6 sm:px-10 py-10 flex flex-col gap-10 text-slate-800">
        
        {/* כותרת הדף */}
        <section className="flex flex-col gap-2 border-b border-slate-200 pb-6">
          <h2 className="text-4xl font-black text-slate-900 tracking-tight">הוספת משרות</h2>
          <p className="text-slate-500 text-lg">ניהול מקורות מידע, לינקים וטקסטים חופשיים לעיבוד AI</p>
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-10 items-start">
          
          {/* עמודה מרכזית - אזורי הזנה */}
          <div className="xl:col-span-8 flex flex-col gap-10">
            
            {/* כרטיס הזנה ראשי */}
            <div className="bg-white rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/50 p-8 relative overflow-hidden group transition-all hover:shadow-2xl hover:shadow-blue-500/5">
              <div className="absolute top-0 right-0 w-1.5 h-full bg-gradient-to-b from-blue-500 to-indigo-600"></div>
              
              <div className="flex items-center gap-4 mb-6">
                 <div className="bg-blue-50 p-3 rounded-2xl text-blue-600">
                    <LinkIcon size={24} strokeWidth={2.5} />
                 </div>
                 <div>
                    <h3 className="text-xl font-bold text-slate-900">ייבוא לינקים מהיר</h3>
                    <p className="text-slate-400 text-sm">הדבק כאן רשימת לינקים (LinkedIn, Glassdoor וכד')</p>
                 </div>
              </div>

              <textarea 
                value={rawInput}
                onChange={(e) => setRawInput(e.target.value)}
                className="w-full h-40 bg-slate-50 border border-slate-100 rounded-2xl p-6 text-lg placeholder:text-slate-400 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500/50 transition-all resize-none mb-6 outline-none"
                placeholder="https://www.linkedin.com/jobs/..."
              />

              <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
                <div className="flex gap-4 text-slate-400 text-sm font-medium bg-slate-50 px-4 py-2 rounded-xl">
                  <span className="flex items-center gap-2"><Sparkles size={14} className="text-blue-500"/> {parsedLinks.length} לינקים זוהו</span>
                </div>
                
                <button 
                  onClick={handleUrlSubmit}
                  disabled={parsedLinks.length === 0 || submitStatus === 'sending'}
                  className={`flex items-center gap-3 py-3.5 px-8 rounded-xl font-bold transition-all active:scale-95
                    ${parsedLinks.length > 0 
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-200 hover:bg-blue-700 hover:-translate-y-0.5' 
                      : 'bg-slate-100 text-slate-400 cursor-not-allowed'}`}
                >
                  {submitStatus === 'sending' ? <Loader2 className="animate-spin" /> : <Send size={18} />}
                  הוסף לתור העיבוד
                </button>
              </div>
            </div>

            {/* כרטיס הזנה ידנית כללית */}
            <div className="bg-white rounded-[2rem] border border-slate-100 shadow-lg shadow-slate-200/50 p-8 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-1.5 h-full bg-gradient-to-b from-purple-500 to-fuchsia-600"></div>
              
              <div className="flex items-center gap-4 mb-6">
                <div className="bg-purple-50 p-3 rounded-2xl text-purple-600">
                  <FileText size={24} strokeWidth={2.5} />
                </div>
                <div>
                   <h3 className="text-xl font-bold text-slate-900">ניתוח טקסט חופשי</h3>
                   <p className="text-slate-400 text-sm">העתק-הדבק לתיאור משרה מלא מוואטסאפ או מייל</p>
                </div>
              </div>

              <div className="flex gap-4 mb-4">
                <input 
                  type="text"
                  value={textTitle}
                  onChange={e => setTextTitle(e.target.value)}
                  placeholder="שם החברה / כותרת (אופציונלי)"
                  className="w-full bg-slate-50 border border-slate-100 rounded-xl px-5 py-3 focus:bg-white focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500/50 outline-none transition-all"
                />
              </div>
              
              <textarea 
                value={textInput}
                onChange={e => setTextInput(e.target.value)}
                className="w-full h-32 bg-slate-50 border border-slate-100 rounded-xl p-5 text-sm focus:bg-white focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500/50 transition-all resize-none outline-none mb-4"
                placeholder="הדבק את תוכן המשרה כאן..."
              />

              <div className="flex justify-end">
                <button 
                  onClick={() => handleTextSubmit(textInput, textTitle)}
                  disabled={!textInput.trim() || submitStatus === 'sending'}
                  className="bg-purple-600 text-white px-8 py-3 rounded-xl font-bold text-sm hover:bg-purple-700 hover:-translate-y-0.5 shadow-lg shadow-purple-200 transition-all disabled:opacity-50 disabled:hover:translate-y-0"
                >
                   {submitStatus === 'sending' ? <Loader2 className="animate-spin" /> : 'נתח טקסט'}
                </button>
              </div>
            </div>
          </div>

          {/* עמודת צד - סטטוסים */}
          <aside className="xl:col-span-4 flex flex-col gap-8 sticky top-8">
            
            {/* שגיאות / נדרשת פעולה */}
            <div className="flex flex-col gap-4">
               <div className="flex items-center justify-between px-1">
                 <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2">
                   <AlertCircle size={20} className="text-rose-500" />
                   נדרשת תשומת לב
                 </h3>
                 {failedJobs.length > 0 && 
                   <span className="bg-rose-100 text-rose-600 text-xs font-black px-2.5 py-1 rounded-full">
                     {failedJobs.length}
                   </span>
                 }
               </div>

               {failedJobs.length === 0 ? (
                 <div className="bg-emerald-50/50 border border-emerald-100/50 rounded-3xl p-6 text-center py-10">
                   <div className="size-14 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
                     <CheckCircle size={28} />
                   </div>
                   <p className="text-emerald-900 font-bold">הכל תקין!</p>
                   <p className="text-emerald-700/60 text-xs mt-1">אין משימות שנכשלו</p>
                 </div>
               ) : (
                 <div className="flex flex-col gap-3">
                   {failedJobs.map((job, idx) => (
                     <div key={idx} className="bg-white border border-rose-100 shadow-sm rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden group hover:shadow-md transition-all">
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-rose-400"></div>
                        
                        <div className="flex justify-between items-start gap-3">
                           <div>
                              <div className="flex items-center gap-2 text-rose-600 text-xs font-bold uppercase tracking-wider mb-1">
                                <AlertCircle size={12} /> נכשל בסריקה
                              </div>
                              <a 
                                href={job.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-slate-800 font-bold text-sm leading-tight hover:text-blue-600 hover:underline decoration-2 flex items-center gap-1 group-link"
                              >
                                {job.company !== 'Unknown' ? job.company : 'קישור לא מזוהה'}
                                <ExternalLink size={12} className="opacity-0 group-hover/link:opacity-100 transition-opacity" />
                              </a>
                              <p className="text-slate-400 text-xs mt-1 truncate max-w-[200px]" dir="ltr">{job.url}</p>
                           </div>
                        </div>
                        
                        <div className="flex gap-2 mt-1">
                          <button 
                            onClick={() => {
                              setJobToFix(job);
                              setIsFixModalOpen(true);
                            }}
                            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-rose-50 text-rose-700 text-xs font-bold hover:bg-rose-100 transition-colors"
                          >
                            <Edit3 size={14} /> תיקון ידני
                          </button>
                          <button 
                            onClick={() => handleRetry(job.url)}
                            className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                            title="נסה שוב"
                          >
                            <RefreshCw size={14} />
                          </button>
                          <button 
                            onClick={() => handleCancel(job.url)}
                            className="px-3 py-2.5 rounded-lg bg-slate-50 text-slate-400 hover:bg-rose-100 hover:text-rose-600 transition-colors"
                            title="מחק מהרשימה"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                     </div>
                   ))}
                 </div>
               )}
            </div>

            {/* תור פעיל - מעוצב מחדש לפי בקשתך */}
            <div className="flex flex-col gap-4 pt-6 border-t border-slate-200">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2">
                  <RefreshCw size={20} className="text-blue-500" />
                  מעובד כעת
                </h3>
                <span className="bg-slate-100 text-slate-600 text-xs font-black px-2.5 py-1 rounded-full">
                  {activeQueue.length}
                </span>
              </div>

              <ActiveQueueList activeQueue={activeQueue} onRetry={handleRetry} />
            </div>

          </aside>
        </div>
      </div>
    </div>
  );
};

export default AddJobsTab;