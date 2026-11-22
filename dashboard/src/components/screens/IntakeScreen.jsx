import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Ban, Check, Loader2, Sparkles } from 'lucide-react';
import Button from '../ui/Button';
import Dialog from '../ui/Dialog';
import { useConfirm } from '../../hooks/useConfirm';
import { RunBar } from '../run/RunMini';
import { DuplicateLinkItem, FailedRunItem, RunRow } from '../run/RunRow';
import { useJobActions } from '../../hooks/useJobActions';
import { taskService } from '../../services/taskService';
import { isFailed } from '../../constants/jobStatus';
import { runSummary } from '../../utils/queueView';
import { jobKey, runCounts } from '../../utils/jobView';

const EMPTY_PREVIEW = { text: '', jobs: [], ignored: [], titles: {} };
const fieldCls = 'w-full rounded-md border border-line-strong bg-surface px-3.5 py-3 leading-relaxed resize-none focus:outline-2 focus:outline-accent focus:outline-offset-1';

// --- הדבקה חופשית: השרת מחלץ את קישורי המשרות (אותה לוגיקה שתשמש גם את הבוט) ---
const RawImport = ({ rawInput, setRawInput, duplicateJobs, setDuplicateJobs, submitStatus, onSubmit }) => {
  const [preview, setPreview] = useState(EMPTY_PREVIEW);
  const hasText = rawInput.trim().length > 0;

  useEffect(() => {
    if (!hasText) return undefined;
    const timer = setTimeout(() => {
      taskService.extractLinks(rawInput)
        .then((res) => setPreview({ text: rawInput, jobs: res.jobs, ignored: res.ignored, titles: res.titles || {} }))
        .catch(() => setPreview({ ...EMPTY_PREVIEW, text: rawInput, error: true }));
    }, 300);
    return () => clearTimeout(timer);
  }, [rawInput, hasText]);

  const links = hasText ? preview.jobs : [];
  const ignored = hasText ? preview.ignored : [];
  const titles = hasText ? preview.titles : {};
  const checking = hasText && preview.text !== rawInput;
  const previewError = hasText && preview.error;
  const sending = submitStatus === 'sending';

  const send = () => {
    const text = rawInput;
    setRawInput('');
    setDuplicateJobs([]);
    onSubmit(text);
  };

  let heading = 'הקישורים שיזוהו יופיעו כאן';
  if (checking) heading = 'מזהה קישורי משרות…';
  else if (previewError) heading = 'השרת לא זמין, אי אפשר לזהות קישורים';
  else if (hasText) heading = links.length ? `זוהו ${links.length} ${links.length === 1 ? 'משרה' : 'משרות'}` : 'לא נמצאו קישורי משרות';

  return (
    <div className="flex flex-col gap-3 flex-1 min-h-0">
      <label htmlFor="raw-input" className="text-xs font-semibold text-ink-2">הדבקה מוואטסאפ, לינקדאין או רשימת קישורים</label>
      <textarea
        id="raw-input"
        value={rawInput}
        onChange={(e) => {
          setRawInput(e.target.value);
          if (duplicateJobs.length > 0) setDuplicateJobs([]);
        }}
        rows={8}
        placeholder="הדבק כאן הודעות, פוסטים או רשימת קישורים. אפשר כמה הודעות יחד."
        className={`${fieldCls} min-h-44`}
        dir="auto"
      />
      <div className="flex items-center gap-2 pt-1" aria-live="polite">
        <h3 className={`text-[13px] font-bold flex-1 flex items-center gap-1.5 ${previewError ? 'text-danger' : ''}`}>
          {checking && <Loader2 size={14} className="animate-spin text-ink-3" aria-hidden />}
          {previewError && <AlertCircle size={14} aria-hidden />}
          {heading}
        </h3>
        {ignored.length > 0 && <span className="text-xs text-ink-3">{ignored.length} {ignored.length === 1 ? 'קישור יסונן' : 'קישורים יסוננו'}</span>}
      </div>
      {(links.length > 0 || ignored.length > 0) && (
        <ul className="flex flex-col gap-1.5 max-h-64 scroll-area">
          {links.map((link) => (
            <li key={link} className="flex items-center gap-2.5 px-3 py-2 rounded-md bg-page min-w-0" title={link}>
              <Check size={14} strokeWidth={2.8} className="text-go shrink-0" aria-hidden />
              {titles[link] && <span className="font-semibold truncate max-w-[50%] shrink-0" dir="auto">{titles[link]}</span>}
              <span className="flex-1 min-w-0 truncate font-mono text-xs text-ink-3" dir="ltr">{link.replace(/^https?:\/\/(www\.)?/, '')}</span>
            </li>
          ))}
          {ignored.map(({ url, reason }) => (
            <li key={url} className="flex items-center gap-2.5 px-3 py-2 rounded-md border border-dashed border-line-strong text-ink-2 min-w-0" title={url}>
              <Ban size={14} className="shrink-0" aria-hidden />
              <span className="shrink-0">יסונן: {reason}</span>
              <span className="flex-1 min-w-0 truncate font-mono text-xs text-ink-3" dir="ltr">{url.replace(/^https?:\/\/(www\.)?/, '')}</span>
            </li>
          ))}
        </ul>
      )}
      {submitStatus === 'error' && (
        <p role="alert" className="flex items-center gap-2 text-[13px] text-danger font-medium"><AlertCircle size={15} aria-hidden />השליחה נכשלה. בדוק שהשרת פועל ונסה שוב.</p>
      )}
      {submitStatus === 'success' && (
        <p role="status" className="flex items-center gap-2 text-[13px] text-go font-medium"><Check size={15} strokeWidth={2.6} aria-hidden />נשלח. כל קישור מופיע ב"איפה כל קישור עומד" עם השלב שלו.</p>
      )}
      <div className="mt-auto pt-3 border-t border-line flex flex-wrap items-center gap-3">
        <span className="flex-1 text-xs text-ink-3 min-w-40">פרמטרי מעקב (utm) יוסרו אוטומטית</span>
        <Button variant="primary" onClick={send} disabled={links.length === 0 || checking || sending}>
          {sending ? <><Loader2 size={16} className="animate-spin" aria-hidden />שולח…</> : `שליחת ${links.length || ''} ${links.length === 1 ? 'משרה' : 'משרות'} לעיבוד`.replace('  ', ' ')}
        </Button>
      </div>
    </div>
  );
};

// --- טקסט של משרה (בלי קישור) ---
const ManualText = ({ textTitle, setTextTitle, textInput, setTextInput, submitStatus, onSubmit }) => (
  <div className="flex flex-col gap-3 flex-1 min-h-0">
    <label className="flex flex-col gap-1.5 text-xs font-semibold text-ink-2">כותרת או שם החברה (לא חובה)
      <input value={textTitle} onChange={(e) => setTextTitle(e.target.value)} className={`${fieldCls} py-2.5 text-sm font-normal text-ink`} dir="auto" />
    </label>
    <label className="flex flex-col gap-1.5 text-xs font-semibold text-ink-2 flex-1">תיאור המשרה
      <textarea
        value={textInput}
        onChange={(e) => setTextInput(e.target.value)}
        rows={10}
        placeholder="הדבק כאן את תיאור המשרה המלא."
        className={`${fieldCls} min-h-56 flex-1 text-sm font-normal text-ink`}
        dir="auto"
      />
    </label>
    {submitStatus === 'error' && <p role="alert" className="text-[13px] text-danger font-medium">השליחה נכשלה. בדוק שהשרת פועל ונסה שוב.</p>}
    {submitStatus === 'success' && <p role="status" className="text-[13px] text-go font-medium">נשלח לניתוח.</p>}
    <div className="pt-3 border-t border-line flex items-center gap-3">
      <span className="flex-1 text-xs text-ink-3 num">{textInput.length.toLocaleString('he-IL')} תווים</span>
      <Button variant="primary" onClick={() => onSubmit(textInput, textTitle)} disabled={!textInput.trim() || submitStatus === 'sending'}>
        {submitStatus === 'sending' ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <Sparkles size={16} aria-hidden />}
        ניתוח הטקסט
      </Button>
    </div>
  </div>
);

// --- תיקון ידני של משרה שנכשלה: הדבקת התוכן, והניתוח ממשיך ישר ל-AI ---
const ManualFixDialog = ({ job, onClose, onSubmit, isSubmitting }) => {
  const [content, setContent] = useState('');
  return (
    <Dialog
      open
      onClose={onClose}
      title="הדבקת טקסט המשרה"
      size="lg"
      footer={(
        <>
          <Button variant="primary" onClick={() => onSubmit(job.id, content)} disabled={!content.trim() || isSubmitting}>
            {isSubmitting ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <Sparkles size={16} aria-hidden />}
            שמירה וניתוח
          </Button>
          <Button variant="ghost" onClick={onClose}>ביטול</Button>
        </>
      )}
    >
      <div className="px-5 max-sm:px-4 pb-5 flex flex-col gap-3">
        <p className="text-[13px] text-ink-2">
          הסריקה האוטומטית נכשלה. פתח את{' '}
          {job.url?.startsWith('http')
            ? <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline" dir="ltr">{job.url.replace(/^https?:\/\/(www\.)?/, '').slice(0, 60)}</a>
            : 'המשרה'}
          , העתק את התיאור והדבק אותו כאן.
        </p>
        <textarea
          data-autofocus
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={12}
          aria-label="תוכן המשרה"
          placeholder="תיאור המשרה…"
          className={`${fieldCls} text-sm min-h-64`}
          dir="auto"
        />
      </div>
    </Dialog>
  );
};

const IntakeScreen = ({ pendingJobs, runJobs, onJobAdded, onOpenJob }) => {
  const [mode, setMode] = useState('raw');
  const [rawInput, setRawInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [textTitle, setTextTitle] = useState('');
  const [jobToFix, setJobToFix] = useState(null);
  const [busyUrl, setBusyUrl] = useState(null);
  const [confirm, confirmEl] = useConfirm();

  const {
    submitStatus, duplicateJobs, setDuplicateJobs, handleRawSubmit, handleTextSubmit, handleManualUpdate,
    handleRescan, handleCancel, handleRetry, handleDismissDuplicate,
  } = useJobActions(onJobAdded);

  const failedJobs = useMemo(() => pendingJobs.filter((j) => isFailed(j.status)), [pendingJobs]);
  const runList = runJobs.filter((j) => !isFailed(j.status));
  const summary = runSummary(runJobs);
  const counts = runCounts(summary);

  const retry = async (url) => {
    setBusyUrl(url);
    await handleRetry(url);
    setBusyUrl(null);
  };
  const remove = async (job) => {
    const ok = await confirm({ title: 'למחוק את המשרה?', body: 'הקישור יוסר מהמערכת. אפשר להוסיף אותו שוב בכל זמן.', confirmLabel: 'מחיקה', danger: true });
    if (ok) handleCancel(job.url);
  };

  const tabs = [
    { id: 'raw', label: 'קישורים מתוך טקסט' },
    { id: 'manual', label: 'טקסט של משרה' },
  ];

  return (
    <div className="px-7 max-sm:px-4 py-6 max-sm:py-4 grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(0,520px)] gap-5 items-start">
      {confirmEl}
      {jobToFix && (
        <ManualFixDialog
          key={jobKey(jobToFix)}
          job={jobToFix}
          onClose={() => setJobToFix(null)}
          isSubmitting={submitStatus === 'sending'}
          onSubmit={async (jobId, content) => {
            const ok = await handleManualUpdate(jobId, content);
            if (ok) setJobToFix(null);
          }}
        />
      )}

      <section aria-label="הוספת משרות" className="bg-surface rounded-lg shadow-[0_0_0_1px_var(--line)] flex flex-col xl:min-h-[560px]">
        <div role="tablist" aria-label="סוג הזנה" className="flex gap-1 p-3 pb-0">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={mode === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setMode(t.id)}
              className={`h-9 px-3.5 rounded-md ${mode === t.id ? 'bg-page font-semibold text-ink' : 'text-ink-2 hover:text-ink hover:bg-hover'}`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div role="tabpanel" id={`panel-${mode}`} aria-labelledby={`tab-${mode}`} className="p-5 max-sm:p-4 pt-3 flex flex-col flex-1">
          {mode === 'raw' ? (
            <RawImport
              rawInput={rawInput}
              setRawInput={setRawInput}
              duplicateJobs={duplicateJobs}
              setDuplicateJobs={setDuplicateJobs}
              submitStatus={submitStatus}
              onSubmit={(text) => handleRawSubmit(text, () => setRawInput(''))}
            />
          ) : (
            <ManualText
              textTitle={textTitle}
              setTextTitle={setTextTitle}
              textInput={textInput}
              setTextInput={setTextInput}
              submitStatus={submitStatus}
              onSubmit={(text, title) => handleTextSubmit(text, title, null, () => { setTextInput(''); setTextTitle(''); })}
            />
          )}
        </div>
      </section>

      <section aria-labelledby="run-h" className="bg-surface rounded-lg shadow-[0_0_0_1px_var(--line)] flex flex-col">
        <div className="px-5 max-sm:px-4 pt-4 pb-3 flex flex-col gap-2.5 border-b border-line">
          <div className="flex items-center gap-2">
            <h2 id="run-h" className="text-[15px] font-bold flex-1">איפה כל קישור עומד</h2>
            <span className="text-xs text-ink-3">{counts.processing ? 'מתעדכן כל 5 שניות' : 'מתעדכן אוטומטית'}</span>
          </div>
          {summary.total > 0 && <RunBar summary={summary} height="h-2" />}
          <p aria-live="polite" className="text-[13px] text-ink-2" data-testid="run-summary">
            {summary.total ? (
              <>
                <strong className="text-ink font-semibold">{summary.total} קישורים בשעה האחרונה:</strong>{' '}
                {counts.done} הושלמו
                {counts.failed > 0 && <> · <span className="text-danger font-semibold">{counts.failed} נכשלו</span></>}
                {counts.processing > 0 && <> · {counts.processing} בעיבוד</>}
              </>
            ) : 'שום קישור לא נכנס בשעה האחרונה.'}
          </p>
        </div>
        <div className="p-3 flex flex-col gap-1.5">
          {duplicateJobs.map((dup) => (
            <DuplicateLinkItem key={dup.url} dup={dup} onRescan={handleRescan} onDismiss={handleDismissDuplicate} />
          ))}
          {failedJobs.map((job) => (
            <FailedRunItem
              key={jobKey(job)}
              job={job}
              busy={busyUrl === job.url}
              onFix={setJobToFix}
              onRetry={retry}
              onRescan={handleRescan}
              onDelete={remove}
            />
          ))}
          {runList.map((job) => <RunRow key={jobKey(job)} job={job} onOpen={onOpenJob} />)}
          {!runList.length && !failedJobs.length && !duplicateJobs.length && (
            <p className="px-3 py-8 text-center text-ink-3 text-[13px]">אין כרגע קישורים בעיבוד. משהו שתדביק כאן יופיע מיד, עם השלב שבו הוא נמצא.</p>
          )}
        </div>
      </section>
    </div>
  );
};

export default IntakeScreen;
