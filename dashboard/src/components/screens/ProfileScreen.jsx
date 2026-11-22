import React, { useEffect, useState } from 'react';
import { AlertCircle, Check, Loader2, RefreshCw } from 'lucide-react';
import Button from '../ui/Button';
import { taskService } from '../../services/taskService';

const Editor = ({ id, label, hint, value, onChange, dirty, placeholder, loading }) => (
  <section className="bg-surface rounded-lg shadow-[0_0_0_1px_var(--line)] flex flex-col min-h-0">
    <div className="px-5 max-sm:px-4 pt-4 pb-2.5 flex flex-col gap-0.5">
      <div className="flex items-center gap-2">
        <label htmlFor={id} className="text-[15px] font-bold flex-1">{label}</label>
        {dirty && <span className="text-xs font-semibold text-warn inline-flex items-center gap-1.5"><span className="size-2 rounded-full bg-warn-fill" aria-hidden />נערך</span>}
      </div>
      <span className="text-[13px] text-ink-3">{hint}</span>
    </div>
    {loading ? (
      <div className="mx-5 max-sm:mx-4 h-[52vh] rounded-md bg-sunken" aria-hidden />
    ) : (
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        dir="ltr"
        spellCheck={false}
        className="mx-5 max-sm:mx-4 h-[52vh] max-sm:h-[44vh] resize-y rounded-md border border-line-strong bg-surface p-3.5 font-mono text-[13px] leading-[1.7] focus:outline-2 focus:outline-accent focus:outline-offset-1"
      />
    )}
    <div className="px-5 max-sm:px-4 py-2.5 text-xs text-ink-3 num">{value.length.toLocaleString('he-IL')} תווים</div>
  </section>
);

const ProfileScreen = () => {
  const [resume, setResume] = useState('');
  const [context, setContext] = useState('');
  const [saved, setSaved] = useState({ resume: '', context: '' });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const load = () => {
    setLoading(true);
    setLoadError(false);
    return Promise.all([taskService.getResume(), taskService.getContext()])
      .then(([r, c]) => {
        setResume(r.content || '');
        setContext(c.content || '');
        setSaved({ resume: r.content || '', context: c.content || '' });
      })
      .catch((error) => {
        console.error('Error loading profile:', error);
        setLoadError(true);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let cancelled = false;
    Promise.all([taskService.getResume(), taskService.getContext()])
      .then(([r, c]) => {
        if (cancelled) return;
        setResume(r.content || '');
        setContext(c.content || '');
        setSaved({ resume: r.content || '', context: c.content || '' });
      })
      .catch((error) => {
        console.error('Error loading profile:', error);
        if (!cancelled) setLoadError(true);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const dirtyResume = resume !== saved.resume;
  const dirtyContext = context !== saved.context;
  const dirty = dirtyResume || dirtyContext;

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await Promise.all([taskService.saveResume(resume), taskService.saveContext(context)]);
      setSaved({ resume, context });
      setMessage({ type: 'success', text: 'נשמר. הניתוחים הבאים ישתמשו בגרסה הזו.' });
      setTimeout(() => setMessage(null), 4000);
    } catch (error) {
      console.error('Error saving profile:', error);
      setMessage({ type: 'error', text: 'השמירה נכשלה. השינויים עדיין כאן. בדוק שהשרת פועל ונסה שוב.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="px-7 max-sm:px-4 py-5 max-sm:py-4 flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3 min-h-10">
        <p className="flex-1 min-w-60 text-[13px] text-ink-2">
          קורות החיים הם מה שה-AI משווה מול כל משרה. ההנחיות אומרות לו איך לשפוט: מטרות, סינונים קשיחים ומה לא מתאים לך. משרות שכבר נותחו לא מתעדכנות. אפשר להריץ עליהן "ניתוח מחדש".
        </p>
        <span aria-live="polite" className="text-[13px]">
          {message?.type === 'success' && <span className="text-go font-medium inline-flex items-center gap-1.5"><Check size={15} strokeWidth={2.6} aria-hidden />{message.text}</span>}
          {message?.type === 'error' && <span className="text-danger font-medium inline-flex items-center gap-1.5"><AlertCircle size={15} aria-hidden />{message.text}</span>}
          {!message && dirty && <span className="text-warn font-semibold inline-flex items-center gap-1.5"><span className="size-2 rounded-full bg-warn-fill" aria-hidden />יש שינויים שלא נשמרו</span>}
        </span>
        <Button variant="primary" onClick={handleSave} disabled={saving || loading || loadError || !dirty}>
          {saving ? <><Loader2 size={16} className="animate-spin" aria-hidden />שומר…</> : 'שמירה'}
        </Button>
      </div>

      {loadError ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 px-4 py-3 rounded-[10px] bg-danger-soft text-[13px]">
          <AlertCircle size={16} className="text-danger" aria-hidden />
          <span className="flex-1">לא הצלחתי לטעון את הפרופיל מהשרת.</span>
          <Button size="sm" variant="secondary" onClick={load}><RefreshCw size={14} aria-hidden />נסה שוב</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <Editor
            id="resume"
            label="קורות חיים"
            hint="כישורים, ניסיון, פרויקטים והשכלה."
            value={resume}
            onChange={setResume}
            dirty={dirtyResume}
            loading={loading}
            placeholder="הדבק כאן את קורות החיים…"
          />
          <Editor
            id="context"
            label="הנחיות לניתוח"
            hint="איך לשפוט משרות: מטרות, העדפות, סינונים קשיחים."
            value={context}
            onChange={setContext}
            dirty={dirtyContext}
            loading={loading}
            placeholder="מטרות קריירה, העדפות, אסטרטגיה…"
          />
        </div>
      )}
    </div>
  );
};

export default ProfileScreen;
