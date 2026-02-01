import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { 
  Link as LinkIcon, Send, Loader2, FileText, 
  CheckCircle, Sparkles, AlertCircle, 
  RefreshCw, Trash2, Edit3, ExternalLink, X, List
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

const AddJobsTab = ({ pendingJobs, onJobAdded }) => {
  const [rawInput, setRawInput] = useState('');
  const [submitStatus, setSubmitStatus] = useState(null); 
  const [duplicateJobs, setDuplicateJobs] = useState([]); // מערך של לינקים כפולים
  
  const [textInput, setTextInput] = useState('');
  const [textTitle, setTextTitle] = useState('');
  const [isFixModalOpen, setIsFixModalOpen] = useState(false);
  const [jobToFix, setJobToFix] = useState(null);

  // --- חילוץ לינקים אוטומטי ---
  const parsedLinks = useMemo(() => {
    if (!rawInput) return [];
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const matches = rawInput.match(urlRegex) || [];
    return [...new Set(matches.map(link => link.replace(/[.,;]$/, "")))];
  }, [rawInput]);

  // --- טיפול בסטטוסים (DRY) ---
  const handleActionWrapper = async (actionFn) => {
    console.log('🟢 handleActionWrapper starting...');
    setSubmitStatus('sending');
    setDuplicateJobs([]); // נקה כפילויות קודמות
    try {
      await actionFn();
      console.log('✅ Action completed successfully');
      setSubmitStatus('success');
      setTimeout(() => setSubmitStatus(null), 3000);
      onJobAdded(); // רענן את הרשימה
      return true;
    } catch (e) {
      console.error('❌ Error in handleActionWrapper:', e);
      console.error('❌ Error response:', e.response);
      console.error('❌ Error status:', e.response?.status);
      console.error('❌ Error data:', e.response?.data);
      
      // תמיד רענן את הרשימה גם במקרה של שגיאה
      onJobAdded();
      
      // בדיקה אם זו שגיאת כפילות מותאמת (מכמה לינקים)
      if (e.isDuplicateError && e.duplicateData?.urls) {
        console.log('🟡 Custom duplicate error detected:', e.duplicateData);
        setDuplicateJobs(e.duplicateData.urls); // שמור כמערך
        setSubmitStatus(null);
      } 
      // שגיאת כפילות מהבקאנד (לינק בודד)
      else if (e.response?.status === 409) {
        console.log('🟡 Backend duplicate error detected:', e.response.data.detail);
        // המר לפורמט אחיד
        const detail = e.response.data.detail;
        setDuplicateJobs([{
          url: detail.url,
          date: detail.date,
          company: detail.url // אין לנו את שם החברה כאן
        }]);
        setSubmitStatus(null);
      } 
      // שגיאה כללית
      else {
        console.log('🔴 General error detected');
        setSubmitStatus('error');
        setTimeout(() => setSubmitStatus(null), 5000);
      }
      return false;
    }
  };

  const handleUrlSubmit = async () => {
    console.log('🔵 handleUrlSubmit called with links:', parsedLinks);
    const result = await handleActionWrapper(async () => {
      console.log('🔵 Sending POST request to backend...');
      const response = await axios.post('http://localhost:8000/api/jobs/url', { urls: parsedLinks });
      console.log('✅ Backend response:', response.data);
      
      // בדיקה אם יש לינקים שדולגו
      if (response.data.skipped_urls && response.data.skipped_urls.length > 0) {
        console.log('⚠️ Some URLs were skipped:', response.data.skipped_urls);
        
        // אם כל הלינקים דולגו - נזרוק שגיאה עם המידע
        if (response.data.added === 0) {
          const error = new Error('All URLs were duplicates');
          error.isDuplicateError = true;
          error.duplicateData = {
            urls: response.data.skipped_urls
          };
          throw error;
        }
        
        // אם חלק מהלינקים דולגו - נוסיף אותם לרשימת הכפילויות
        setDuplicateJobs(response.data.skipped_urls);
      }
      
      setRawInput('');
    });
    console.log('🔵 handleActionWrapper result:', result);
  };

  const handleTextSubmit = (text, title, originalUrl = null) => handleActionWrapper(async () => {
    await axios.post('http://localhost:8000/api/jobs/text', {
      text,
      title: title || 'משרה ידנית',
      url: originalUrl
    });
    if (!isFixModalOpen) {
      setTextInput('');
      setTextTitle('');
    }
  });

  const handleRescan = (url) => handleActionWrapper(async () => {
    await axios.delete(`http://localhost:8000/api/jobs`, { params: { url } });
    await axios.post('http://localhost:8000/api/jobs/url', { urls: [url] });
  });

  const handleCancel = async (url) => {
    try {
      await axios.delete(`http://localhost:8000/api/jobs`, { params: { url } });
      onJobAdded();
    } catch (err) { console.error(err); }
  };

  const handleRetry = async (url) => {
    try {
      await axios.post(`http://localhost:8000/api/jobs/retry`, null, { params: { url } });
      onJobAdded();
    } catch (err) { console.error(err); }
  };

  const handleDismissDuplicate = (url) => {
    // הסרת לינק כפול מהרשימה (המשתמש החליט להתעלם ממנו)
    setDuplicateJobs(prev => prev.filter(job => job.url !== url));
  };

  const { activeQueue, failedJobs } = useMemo(() => {
    return {
      activeQueue: pendingJobs.filter(j => !['FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status)),
      failedJobs: pendingJobs.filter(j => ['FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status))
    };
  }, [pendingJobs]);

  return (
    <div className="w-full min-h-screen bg-slate-50/50" dir="rtl">
      <ManualFixModal 
        isOpen={isFixModalOpen}
        onClose={() => setIsFixModalOpen(false)}
        job={jobToFix}
        onSubmit={async (url, title, content) => {
          const success = await handleTextSubmit(content, title, url);
          if (success) {
            await handleCancel(url);
            setIsFixModalOpen(false);
          }
        }}
        isSubmitting={submitStatus === 'sending'}
      />

      <div className="max-w-[1600px] mx-auto w-full px-6 py-10 flex flex-col gap-10">
        <section className="flex flex-col gap-2 border-b border-slate-200 pb-6">
          <h2 className="text-4xl font-black text-slate-900 tracking-tight">הוספת משרות</h2>
          <p className="text-slate-500 text-lg">ניהול מקורות מידע ועיבוד AI</p>
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-10 items-start">
          <div className="xl:col-span-8 flex flex-col gap-10">
            
            {/* כרטיס הזנה מפוצל - חדש */}
            <div className="bg-white rounded-[2rem] border border-slate-100 shadow-xl p-8 relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-1.5 h-full bg-blue-500"></div>
              
              <div className="flex items-center gap-4 mb-8">
                 <div className="bg-blue-50 p-3 rounded-2xl text-blue-600"><LinkIcon size={24} /></div>
                 <div>
                    <h3 className="text-xl font-bold text-slate-900">ייבוא לינקים חכם</h3>
                    <p className="text-slate-400 text-sm">הדבק טקסט הכולל לינקים - המערכת תחלץ אותם אוטומטית</p>
                 </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                {/* צד ימין - קלט */}
                <div className="flex flex-col gap-3">
                  <label className="text-xs font-bold text-slate-400 uppercase mr-1">הדבקת תוכן / לינקים</label>
                  <textarea 
                    value={rawInput}
                    onChange={(e) => {
                      setRawInput(e.target.value);
                      if (duplicateJobs.length > 0) setDuplicateJobs([]);
                    }}
                    className={`w-full h-64 bg-slate-50 border rounded-2xl p-5 text-sm focus:bg-white focus:ring-4 transition-all resize-none outline-none
                      ${duplicateJobs.length > 0 ? 'border-amber-300 focus:ring-amber-500/10' : 'border-slate-100 focus:ring-blue-500/10'}`}
                    placeholder="הדבק כאן הודעות, רשימות או לינקים ישירים..."
                  />
                </div>

                {/* צד שמאל - תצוגת לינקים שחולצו */}
                <div className="flex flex-col gap-3">
                  <label className="text-xs font-bold text-slate-400 uppercase mr-1">לינקים שזוהו ({parsedLinks.length})</label>
                  <div className="w-full h-64 bg-slate-50/50 border border-dashed border-slate-200 rounded-2xl p-4 overflow-y-auto">
                    {parsedLinks.length > 0 ? (
                      <div className="flex flex-col gap-2">
                        {parsedLinks.map((link, i) => (
                          <div key={i} className="flex items-center gap-2 bg-white p-2 rounded-lg border border-slate-100 text-[11px] text-slate-500 font-mono truncate">
                            <span className="text-blue-500 shrink-0">#{i+1}</span>
                            <span className="truncate shrink">{link}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="h-full flex flex-col items-center justify-center text-slate-300 gap-2 text-center">
                        <List size={32} strokeWidth={1} />
                        <p className="text-xs">טרם זוהו לינקים בטקסט</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {submitStatus === 'error' && (
                <div className="mb-6 p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-center gap-3 animate-in slide-in-from-top-2">
                  <AlertCircle size={20} className="text-rose-600" />
                  <p className="text-rose-900 font-bold text-sm">אירעה שגיאה בעיבוד הבקשה. אנא בדוק את הקונסול לפרטים נוספים.</p>
                </div>
              )}

              <div className="flex justify-end pt-4 border-t border-slate-50">
                <button 
                  onClick={handleUrlSubmit}
                  disabled={parsedLinks.length === 0 || submitStatus === 'sending'}
                  className={`flex items-center gap-3 py-3.5 px-10 rounded-xl font-bold transition-all
                    ${parsedLinks.length > 0 ? 'bg-blue-600 text-white shadow-lg hover:bg-blue-700' : 'bg-slate-100 text-slate-400'}`}
                >
                  {submitStatus === 'sending' ? <Loader2 className="animate-spin" /> : <Send size={18} />}
                  שלח {parsedLinks.length} לינקים לעיבוד
                </button>
              </div>
            </div>

            {/* כרטיס הזנה ידנית */}
            <div className="bg-white rounded-[2rem] border border-slate-100 shadow-lg p-8 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-1.5 h-full bg-purple-500"></div>
              <div className="flex items-center gap-4 mb-6">
                <div className="bg-purple-50 p-3 rounded-2xl text-purple-600"><FileText size={24} /></div>
                <div>
                   <h3 className="text-xl font-bold text-slate-900">ניתוח טקסט חופשי</h3>
                   <p className="text-slate-400 text-sm">העתק-הדבק לתיאור משרה מלא</p>
                </div>
              </div>
              <input 
                type="text" value={textTitle} onChange={e => setTextTitle(e.target.value)}
                placeholder="שם החברה / כותרת (אופציונלי)"
                className="w-full bg-slate-50 border border-slate-100 rounded-xl px-5 py-3 mb-4 outline-none focus:ring-4 focus:ring-purple-500/10 transition-all"
              />
              <textarea 
                value={textInput} onChange={e => setTextInput(e.target.value)}
                className="w-full h-32 bg-slate-50 border border-slate-100 rounded-xl p-5 text-sm mb-4 resize-none outline-none focus:ring-4 focus:ring-purple-500/10 transition-all"
                placeholder="הדבק את תוכן המשרה כאן..."
              />
              <div className="flex justify-end">
                <button 
                  onClick={() => handleTextSubmit(textInput, textTitle)}
                  disabled={!textInput.trim() || submitStatus === 'sending'}
                  className="bg-purple-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-purple-700 shadow-lg transition-all disabled:opacity-50"
                >
                  {submitStatus === 'sending' ? <Loader2 className="animate-spin" /> : 'נתח טקסט עכשיו'}
                </button>
              </div>
            </div>
          </div>

          {/* עמודת צד - סטטוסים */}
          <aside className="xl:col-span-4 flex flex-col gap-8 sticky top-8">
            <div className="flex flex-col gap-4">
               <h3 className="text-lg font-bold text-slate-700 flex items-center gap-2 px-1">
                 <AlertCircle size={20} className="text-rose-500" /> נדרשת תשומת לב
                 {(failedJobs.length + duplicateJobs.length) > 0 && (
                   <span className="bg-rose-100 text-rose-700 text-xs font-bold px-2 py-1 rounded-full">
                     {failedJobs.length + duplicateJobs.length}
                   </span>
                 )}
               </h3>
               
               {failedJobs.length === 0 && duplicateJobs.length === 0 ? (
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
                          <button onClick={() => { setJobToFix(job); setIsFixModalOpen(true); }} className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-rose-50 text-rose-700 text-xs font-bold hover:bg-rose-100 transition-colors">
                            <Edit3 size={14} /> תיקון ידני
                          </button>
                          <button onClick={() => handleRetry(job.url)} className="p-2 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"><RefreshCw size={14} /></button>
                          <button onClick={() => handleCancel(job.url)} className="p-2 rounded-lg bg-slate-50 text-slate-400 hover:text-rose-600 transition-colors"><Trash2 size={14} /></button>
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
        </div>
      </div>
    </div>
  );
};

export default AddJobsTab;