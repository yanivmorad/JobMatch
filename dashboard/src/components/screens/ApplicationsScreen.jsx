import React, { useState } from 'react';
import { ArrowLeft, Columns3, Inbox, SearchX } from 'lucide-react';
import Dialog from '../ui/Dialog';
import Button from '../ui/Button';
import { EmptyState } from '../ui/Feedback';
import JobDetail from '../job/JobDetail';
import { CloseMenu } from '../job/ApplicationStatus';
import { PIPELINE_STAGES, STATUS_CONFIG } from '../../constants/statusConfig';
import { daysSince, jobHeading, jobKey } from '../../utils/jobView';

const sinceLabel = (job, now) => {
  const stage = job.application_status;
  const ref = stage === 'applied' ? (job.applied_at || job.updated_at) : job.updated_at;
  const d = daysSince(ref, now);
  if (d === null) return '';
  const when = d === 0 ? 'היום' : d === 1 ? 'אתמול' : `לפני ${d} ימים`;
  if (stage === 'applied') return `הוגש ${when}`;
  return d === 0 ? 'עבר לשלב הזה היום' : `בשלב הזה ${d === 1 ? 'מאתמול' : `${d} ימים`}`;
};

const AppCard = ({ job, now, onOpen, onUpdateStatus }) => {
  const { title, sub } = jobHeading(job);
  const status = job.application_status;
  const i = PIPELINE_STAGES.indexOf(status);
  const next = i >= 0 ? PIPELINE_STAGES[i + 1] : null;
  return (
    <article className="bg-surface rounded-xl shadow-[0_0_0_1px_var(--line)] p-3.5 flex flex-col gap-2.5">
      <button type="button" onClick={() => onOpen(job)} className="text-start flex gap-3 items-start rounded-md -m-1 p-1 hover:bg-hover">
        <span className="flex-1 min-w-0">
          <span className="block truncate font-semibold" dir="auto">{title}</span>
          <span className="block truncate text-[13px] text-ink-2" dir="auto">{sub || 'חברה לא ידועה'}</span>
        </span>
        {job.suitability_score !== null && job.suitability_score !== undefined && (
          <span className="num text-lg font-semibold leading-tight" aria-label={`ציון ${job.suitability_score}`}>{job.suitability_score}</span>
        )}
      </button>
      <span className="text-xs text-ink-3">{sinceLabel(job, now)}</span>
      <div className="flex gap-1.5">
        {next ? (
          <Button size="sm" variant="secondary" className="flex-1 justify-center !bg-accent-soft !text-accent !border-transparent font-semibold" onClick={() => onUpdateStatus(job.url, next)}>
            {STATUS_CONFIG[next].label}<ArrowLeft size={14} aria-hidden />
          </Button>
        ) : (
          <span className="flex-1 text-xs text-ink-2 self-center">{STATUS_CONFIG[status]?.closed ? `נסגר: ${STATUS_CONFIG[status].label}` : 'השלב האחרון'}</span>
        )}
        <CloseMenu job={job} onUpdateStatus={onUpdateStatus} compact />
      </div>
    </article>
  );
};

// הגשות כ-pipeline: עמודה לכל שלב. לחיצה על שלב הבא מקדמת; "סגירה" מסיימת.
const ApplicationsScreen = ({ jobs, now, loading, onAction, onDelete, onUpdateStatus, onRetry, onNavigate, searching }) => {
  const [openKey, setOpenKey] = useState(null);
  const openJob = jobs.find((j) => jobKey(j) === openKey);

  const columns = PIPELINE_STAGES.map((k) => ({ key: k, label: STATUS_CONFIG[k].label, items: jobs.filter((j) => j.application_status === k) }));
  const closed = jobs.filter((j) => !PIPELINE_STAGES.includes(j.application_status));
  if (closed.length) columns.push({ key: 'closed', label: 'נסגרו (לא בארכיון)', items: closed });

  if (!loading && jobs.length === 0) {
    return searching ? (
      <EmptyState icon={SearchX} title="אין הגשות שמתאימות לחיפוש" className="flex-1" />
    ) : (
      <EmptyState
        icon={Columns3}
        title="אין הגשות פתוחות"
        className="flex-1"
        action={<Button variant="primary" onClick={() => onNavigate('active')}><Inbox size={16} aria-hidden />למשרות לבדיקה</Button>}
      >
        כשמסמנים "הגשתי" על משרה, היא עוברת לכאן. כאן מקדמים אותה לשיחה טלפונית ולראיון, או סוגרים.
      </EmptyState>
    );
  }

  return (
    <div className="px-7 max-sm:px-4 py-5 max-sm:py-4">
      <div className="grid gap-4 grid-cols-1 md:[grid-template-columns:repeat(var(--cols),minmax(0,1fr))]" style={{ '--cols': columns.length }}>
        {columns.map((c, ci) => (
          <section key={c.key} aria-labelledby={`col-${c.key}`} className="flex flex-col gap-2.5 min-w-0">
            <div className="flex items-center gap-2 h-7 px-1">
              <h2 id={`col-${c.key}`} className="text-sm font-bold">{c.label}</h2>
              <span className="num text-xs font-semibold bg-surface shadow-[0_0_0_1px_var(--line)] rounded-full px-2 leading-5">{c.items.length}</span>
              <span className="flex-1 h-px bg-line" />
              {ci < PIPELINE_STAGES.length - 1 && <ArrowLeft size={14} className="text-ink-3 max-md:hidden" aria-hidden />}
            </div>
            {loading && <div className="skeleton h-28 rounded-xl" aria-hidden />}
            {!loading && c.items.length === 0 && (
              <div className="rounded-xl border border-dashed border-line-strong/60 text-ink-3 text-[13px] px-4 py-6 text-center">ריק</div>
            )}
            {c.items.map((j) => (
              <AppCard key={jobKey(j)} job={j} now={now} onOpen={(job) => setOpenKey(jobKey(job))} onUpdateStatus={onUpdateStatus} />
            ))}
          </section>
        ))}
      </div>

      <Dialog open={Boolean(openJob)} onClose={() => setOpenKey(null)} title={openJob ? jobHeading(openJob).title : ''} hideTitle variant="sheet">
        {openJob && (
          <JobDetail
            job={openJob}
            context="applied"
            layout="sheet"
            onAction={onAction}
            onDelete={async (job) => { const ok = await onDelete(job); if (ok) setOpenKey(null); return ok; }}
            onUpdateStatus={onUpdateStatus}
            onRetry={onRetry}
          />
        )}
      </Dialog>
    </div>
  );
};

export default ApplicationsScreen;
