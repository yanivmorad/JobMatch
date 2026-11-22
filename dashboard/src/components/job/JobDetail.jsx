import React, { useState } from 'react';
import {
  AlertCircle, Ban, Check, ChevronDown, Copy, ExternalLink, Loader2, MoreHorizontal, RefreshCw, RotateCcw,
  Send, Sparkles, Trash2, TrendingUp,
} from 'lucide-react';
import Button from '../ui/Button';
import { HeroScore, VerdictBadge } from '../ui/Score';
import { Menu, MenuItem } from '../ui/Feedback';
import { useToast } from '../../hooks/useToast';
import { useConfirm } from '../../hooks/useConfirm';
import { PIPELINE_STEPS, stepStates } from '../../utils/pipeline';
import ApplicationStepper from './ApplicationStatus';
import {
  FAILED_STATUS_LABELS, isFailed, isProcessing, needsManualContent,
} from '../../constants/jobStatus';
import {
  blockersOf, gapsOf, isManualJob, jobHeading, jobHost, shortDate, verdictOf,
} from '../../utils/jobView';

// --- חלקים ---

const Header = ({ job }) => {
  const { title, sub, titleIsUrl } = jobHeading(job);
  const host = jobHost(job);
  const meta = [sub, job.created_at ? `נוסף ${shortDate(job.created_at)}` : null].filter(Boolean);
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-[13px] text-ink-2 flex flex-wrap items-center gap-x-1.5">
        {meta.map((m, i) => (
          <React.Fragment key={m}>{i > 0 && <span aria-hidden>·</span>}<span dir="auto">{m}</span></React.Fragment>
        ))}
        {host && job.url?.startsWith('http') && (
          <>
            <span aria-hidden>·</span>
            <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline inline-flex items-center gap-1" dir="ltr">
              {host}<ExternalLink size={12} aria-hidden />
            </a>
          </>
        )}
      </p>
      <h2 className={`font-bold leading-tight tracking-[-0.015em] ${titleIsUrl ? 'font-mono text-lg font-normal break-all' : 'text-[26px] max-sm:text-[22px]'}`} dir="auto">
        {title}
      </h2>
    </div>
  );
};

const VerdictBlock = ({ job }) => {
  const blockers = blockersOf(job).length;
  const gaps = gapsOf(job).length;
  const p = job.acceptance_probability;
  return (
    <div className="grid grid-cols-[1.3fr_1fr_1fr] max-md:grid-cols-2 rounded-lg shadow-[0_0_0_1px_var(--line)] overflow-hidden">
      <div className="p-5 max-sm:p-4 max-md:col-span-2 max-md:border-b border-line"><HeroScore score={job.suitability_score} /></div>
      <div className="p-5 max-sm:p-4 flex flex-col gap-2 md:border-s border-line">
        <span className="text-xs font-semibold text-ink-2">סיכוי קבלה</span>
        <span className="flex items-baseline gap-0.5">
          <span className="num text-[32px] max-sm:text-[28px] font-semibold leading-none">{p ?? '—'}</span>
          {p !== null && p !== undefined && <span className="text-ink-3">%</span>}
        </span>
        <span className="text-xs text-ink-2">הערכת ה-AI</span>
      </div>
      <div className="p-5 max-sm:p-4 flex flex-col gap-2 border-s border-line bg-sunken/70">
        <span className="text-xs font-semibold text-ink-2">המלצה</span>
        <VerdictBadge job={job} size="lg" />
        <span className="text-xs text-ink-2">
          {blockers ? `${blockers} ${blockers === 1 ? 'חוסם' : 'חוסמים'}` : 'אין חוסמים'}
          {gaps ? ` · ${gaps} ${gaps === 1 ? 'פער' : 'פערים'}` : ''}
        </span>
      </div>
    </div>
  );
};

const Blockers = ({ job }) => {
  const items = blockersOf(job);
  if (!items.length) {
    return (
      <p className="flex items-center gap-2 text-sm text-go font-medium">
        <Check size={16} strokeWidth={2.6} aria-hidden /> ה-AI לא מצא חוסמים במשרה הזו
      </p>
    );
  }
  return (
    <section aria-labelledby="blockers-h" className="flex flex-col gap-2.5">
      <h3 id="blockers-h" className="text-[15px] font-bold flex items-center gap-2"><Ban size={16} className="text-danger" aria-hidden />חוסמים</h3>
      <ol className="flex flex-col gap-1.5">
        {items.map((b, i) => (
          <li key={i} className="flex gap-3 px-3.5 py-3 rounded-[10px] bg-danger-soft leading-relaxed">
            <span className="num font-bold text-danger">{i + 1}</span>
            <span dir="auto">{b}</span>
          </li>
        ))}
      </ol>
    </section>
  );
};

const Gaps = ({ job }) => {
  const items = gapsOf(job);
  if (!items.length) return null;
  return (
    <section aria-labelledby="gaps-h" className="flex flex-col gap-2.5">
      <h3 id="gaps-h" className="text-[15px] font-bold flex items-center gap-2"><TrendingUp size={16} className="text-warn" aria-hidden />פערי ידע</h3>
      <ul className="flex flex-col gap-1.5 ps-5 list-disc marker:text-ink-3 text-ink leading-relaxed">
        {items.map((g, i) => <li key={i} dir="auto">{g}</li>)}
      </ul>
    </section>
  );
};

const Reading = ({ title, children, id }) => (
  <section aria-labelledby={id} className="flex flex-col gap-2">
    <h3 id={id} className="text-[15px] font-bold">{title}</h3>
    <div className="text-base leading-[1.75] text-ink max-w-[68ch] whitespace-pre-line" dir="auto">{children}</div>
  </section>
);

const FullDescription = ({ text }) => {
  const [open, setOpen] = useState(false);
  if (!text) return null;
  return (
    <section className="border-t border-line pt-5">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-2 hover:text-ink"
      >
        <ChevronDown size={16} className={`transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
        {open ? 'הסתרת תיאור המשרה המקורי' : 'תיאור המשרה המקורי'}
      </button>
      {open && (
        <div className="state-fade mt-3 p-4 rounded-md bg-sunken text-[13px] leading-relaxed text-ink-2 whitespace-pre-wrap max-h-[50vh] scroll-area" dir="auto">
          {text}
        </div>
      )}
    </section>
  );
};

// משרה שעוד בצינור: איפה היא עומדת, ומקום שמור לציון
const ProcessingState = ({ job }) => {
  const states = stepStates(job.status);
  return (
    <div className="flex flex-col gap-5">
      <ol className="flex flex-col">
        {PIPELINE_STEPS.map((step, i) => {
          const s = states[i];
          return (
            <li key={step.key} className={`flex items-center gap-3 h-10 ${s === 'working' || s === 'waiting' ? 'text-accent font-semibold' : s === 'off' ? 'text-ink-3' : ''}`}>
              <span className={`size-5 rounded-full inline-flex items-center justify-center shrink-0 ${s === 'done' ? 'bg-go-fill text-ink-inverse' : s === 'off' ? 'bg-sunken' : 'bg-accent-soft'}`}>
                {s === 'done' && <Check size={12} strokeWidth={3.2} aria-hidden />}
                {s === 'working' && <span className="size-2 rounded-full bg-accent pulse-dot" />}
                {s === 'waiting' && <span className="size-2 rounded-full border-2 border-accent box-border" />}
              </span>
              <span className="flex-1">{step.label}</span>
              <span className="text-xs">{s === 'done' ? 'הושלם' : s === 'working' ? 'עכשיו' : s === 'waiting' ? 'בתור' : ''}</span>
            </li>
          );
        })}
      </ol>
      <div className="rounded-lg bg-sunken h-24 flex items-center justify-center text-[13px] text-ink-3">
        הציון, ההמלצה והחוסמים יופיעו כאן כשהניתוח יסתיים
      </div>
    </div>
  );
};

// משרה שנכשלה: מה קרה, ותיקון במקום (הדבקת תוכן / ניסיון חוזר)
const FailedState = ({ job, onAction, onRetry }) => {
  const manual = needsManualContent(job.status);
  const [title, setTitle] = useState(job.job_title && job.job_title !== 'Unknown' ? job.job_title : '');
  const [company, setCompany] = useState(job.company && !/^https?:/.test(job.company) && job.company !== 'Unknown' ? job.company : '');
  const [desc, setDesc] = useState(job.full_description || '');
  const [busy, setBusy] = useState(null);
  const canSave = title.trim() && company.trim() && desc.trim();

  const save = async () => {
    setBusy('save');
    await onAction(job, 'manual_update', { title: title.trim(), company: company.trim(), description: desc });
    setBusy(null);
  };
  const retry = async () => {
    setBusy('retry');
    await onRetry(job.url);
    setBusy(null);
  };

  const fieldCls = 'w-full rounded-md border border-line-strong bg-surface px-3 py-2.5 focus:outline-2 focus:outline-accent focus:outline-offset-1';
  return (
    <div className="flex flex-col gap-4">
      <div role="alert" className="flex gap-2.5 px-4 py-3 rounded-[10px] bg-danger-soft">
        <AlertCircle size={18} className="text-danger shrink-0 mt-0.5" aria-hidden />
        <div className="flex flex-col gap-1 text-sm">
          <strong className="text-danger font-semibold">{FAILED_STATUS_LABELS[job.status] || 'העיבוד נכשל'}</strong>
          {job.error_log && <span className="text-ink-2 break-words" dir="auto">{job.error_log}</span>}
          {manual && <span className="text-ink">אם יש לך את טקסט המשרה, הדבק אותו כאן והניתוח ירוץ ישירות.</span>}
        </div>
      </div>
      {manual && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 max-sm:grid-cols-1 gap-3">
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-ink-2">כותרת המשרה
              <input value={title} onChange={(e) => setTitle(e.target.value)} className={`${fieldCls} text-sm font-normal text-ink`} dir="auto" />
            </label>
            <label className="flex flex-col gap-1.5 text-xs font-semibold text-ink-2">חברה
              <input value={company} onChange={(e) => setCompany(e.target.value)} className={`${fieldCls} text-sm font-normal text-ink`} dir="auto" />
            </label>
          </div>
          <label className="flex flex-col gap-1.5 text-xs font-semibold text-ink-2">תוכן המשרה
            <textarea
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              rows={10}
              placeholder="הדבקת תיאור המשרה…"
              className={`${fieldCls} text-sm font-normal text-ink leading-relaxed resize-y min-h-48`}
              dir="auto"
            />
          </label>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {manual && (
          <Button variant="primary" onClick={save} disabled={!canSave || busy}>
            {busy === 'save' ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <Sparkles size={16} aria-hidden />}
            שמירה וניתוח
          </Button>
        )}
        {!isManualJob(job) && (
          <Button variant={manual ? 'secondary' : 'primary'} onClick={retry} disabled={Boolean(busy)}>
            {busy === 'retry' ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <RefreshCw size={16} aria-hidden />}
            נסה שוב
          </Button>
        )}
      </div>
      {manual && !canSave && desc.trim() && <p className="text-xs text-ink-3">צריך כותרת, חברה ותוכן כדי לשלוח לניתוח.</p>}
    </div>
  );
};

// --- הפרט כולו ---
// context: review (החלטה) / applied (מעקב) / archive (החזרה)
const JobDetail = ({ job, context = 'review', onAction, onDelete, onUpdateStatus, onRetry, onDecided, layout = 'pane' }) => {
  const toast = useToast();
  const [confirm, confirmEl] = useConfirm();
  const [busy, setBusy] = useState(null);
  const processing = isProcessing(job.status);
  const failed = isFailed(job.status);
  const completed = !processing && !failed;
  const pending = !job.application_status || job.application_status === 'pending';
  const manual = isManualJob(job);
  const external = job.url?.startsWith('http');

  const decide = async (status) => {
    setBusy(status);
    const ok = await onUpdateStatus(job.url, status);
    setBusy(null);
    if (ok) {
      toast(status === 'applied' ? 'סומן כהוגש · עבר להגשות' : 'סומן כלא רלוונטי · עבר לארכיון');
      onDecided?.(job);
    }
  };

  const reanalyze = async () => {
    setBusy('retry');
    await onRetry(job.url);
    setBusy(null);
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(job.url);
      toast('הקישור הועתק');
    } catch {
      toast('לא הצלחתי להעתיק את הקישור', 'danger');
    }
  };

  const remove = async () => {
    const ok = await confirm({
      title: 'למחוק את המשרה?',
      body: 'המשרה והניתוח שלה יימחקו לצמיתות. אי אפשר לבטל.',
      confirmLabel: 'מחיקה',
      danger: true,
    });
    if (!ok) return;
    const done = await onDelete?.(job);
    if (done) onDecided?.(job);
  };

  const verdict = verdictOf(job);

  return (
    <div className={`flex flex-col min-h-0 ${layout === 'pane' ? 'h-full' : ''}`}>
      {confirmEl}
      <div className={`flex-1 min-h-0 flex flex-col gap-6 [&>*]:shrink-0 ${layout === 'pane' ? 'scroll-area px-9 max-xl:px-7 py-7' : 'px-5 max-sm:px-4 pb-6 pt-1'}`}>
        <Header job={job} />

        {processing && <ProcessingState job={job} />}
        {failed && <FailedState key={job.status} job={job} onAction={onAction} onRetry={onRetry} />}

        {completed && (
          <>
            {context !== 'review' && !pending && (
              <section aria-label="סטטוס ההגשה" className="flex flex-col gap-2">
                <span className="text-xs font-semibold text-ink-2">שלב ההגשה</span>
                <ApplicationStepper job={job} onUpdateStatus={onUpdateStatus} />
              </section>
            )}
            <VerdictBlock job={job} />
            <Blockers job={job} />
            <Gaps job={job} />
            {job.formatted_message && <Reading id="why-h" title="ההסבר של ה-AI">{job.formatted_message}</Reading>}
            {job.job_summary_hebrew && <Reading id="sum-h" title="על המשרה">{job.job_summary_hebrew}</Reading>}
            <FullDescription text={job.full_description} />
          </>
        )}
      </div>

      <footer className={`shrink-0 border-t border-line bg-surface flex flex-wrap items-center gap-2 ${layout === 'pane' ? 'px-9 max-xl:px-7 py-3.5' : 'px-5 max-sm:px-4 py-3 pb-[max(12px,env(safe-area-inset-bottom))] sticky bottom-0'}`}>
        {external && (
          <Button variant="accent" href={job.url}>
            לדף המשרה<ExternalLink size={15} aria-hidden />
          </Button>
        )}
        {completed && pending && (
          <>
            <Button variant="go" onClick={() => decide('applied')} disabled={Boolean(busy)}>
              {busy === 'applied' ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <Send size={16} aria-hidden />}
              הגשתי
            </Button>
            <Button variant="secondary" onClick={() => decide('not_relevant')} disabled={Boolean(busy)}>
              לא רלוונטי
            </Button>
          </>
        )}
        {context === 'archive' && (
          <Button variant="secondary" onClick={() => onAction(job, 'none')}>
            <RotateCcw size={16} aria-hidden />החזרה ללוח
          </Button>
        )}
        <span className="flex-1" />
        {completed && !manual && (
          <Button
            variant="secondary"
            size="icon"
            onClick={reanalyze}
            disabled={Boolean(busy)}
            aria-label="ניתוח מחדש"
            title="ניתוח מחדש"
          >
            {busy === 'retry' ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <RefreshCw size={16} aria-hidden />}
          </Button>
        )}
        <Menu
          label="עוד פעולות"
          align="end"
          placement="up"
          triggerClassName="h-10 w-10 max-sm:h-11 max-sm:w-11 inline-flex items-center justify-center rounded-md border border-line-strong bg-surface text-ink-2 hover:bg-hover"
          trigger={<MoreHorizontal size={18} aria-hidden />}
        >
          {(close) => (
            <>
              {job.url && <MenuItem close={close} icon={Copy} onSelect={copyLink}>העתקת הקישור</MenuItem>}
              {completed && !manual && <MenuItem close={close} icon={RefreshCw} hint="סריקה וניתוח מההתחלה" onSelect={reanalyze}>ניתוח מחדש</MenuItem>}
              {onDelete && <MenuItem close={close} icon={Trash2} tone="danger" onSelect={remove}>מחיקת המשרה</MenuItem>}
            </>
          )}
        </Menu>
        {verdict === 'yes' && completed && pending && <span className="sr-only">ה-AI ממליץ להגיש</span>}
      </footer>
    </div>
  );
};

export default JobDetail;
