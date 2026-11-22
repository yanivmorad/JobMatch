import React from 'react';
import { Archive, Check, ChevronDown, Inbox } from 'lucide-react';
import { Menu, MenuItem } from '../ui/Feedback';
import { AUTO_ARCHIVE_STATUSES, PIPELINE_STAGES, STATUS_CONFIG } from '../../constants/statusConfig';

const closingHint = (key) => (AUTO_ARCHIVE_STATUSES.includes(key) ? 'יועבר לארכיון' : '');

// תפריט סגירה / העברה: דחייה, ללא מענה, לא רלוונטי, ארכיון, חזרה לבדיקה
export const CloseMenu = ({ job, onUpdateStatus, label = 'סגירה', compact = false }) => {
  const status = job.application_status || 'pending';
  return (
    <Menu
      label={`סגירה או העברה של ${job.job_title || 'המשרה'}`}
      triggerClassName={`inline-flex items-center gap-1.5 rounded-md border border-line-strong bg-surface hover:bg-hover text-ink ${compact ? 'h-8 px-2.5 text-[13px]' : 'h-10 px-3 text-sm'}`}
      trigger={<>{label}<ChevronDown size={14} aria-hidden /></>}
    >
      {(close) => (
        <>
          {['rejected', 'ghosted', 'not_relevant'].map((k) => (
            <MenuItem
              key={k}
              close={close}
              current={status === k}
              tone={k === 'rejected' ? 'danger' : undefined}
              hint={closingHint(k)}
              onSelect={() => onUpdateStatus(job.url, k)}
            >
              {STATUS_CONFIG[k].label}
            </MenuItem>
          ))}
          <div className="my-1 h-px bg-line" />
          {!job.is_archived && (
            <MenuItem close={close} icon={Archive} hint="שומר את השלב הנוכחי" onSelect={() => onUpdateStatus(job.url, status, true)}>
              העברה לארכיון
            </MenuItem>
          )}
          <MenuItem close={close} icon={Inbox} hint="ממתין לבדיקה" onSelect={() => onUpdateStatus(job.url, 'pending')}>
            חזרה ללבדיקה
          </MenuItem>
        </>
      )}
    </Menu>
  );
};

// שלב ההגשה כ-pipeline: הוגש ← שיחה טלפונית ← ראיון. כל שלב הוא כפתור שמעביר אליו.
const ApplicationStepper = ({ job, onUpdateStatus, size = 'md' }) => {
  const status = job.application_status || 'pending';
  const currentIndex = PIPELINE_STAGES.indexOf(status);
  const closed = STATUS_CONFIG[status]?.closed;
  const h = size === 'sm' ? 'h-8 text-[13px] px-2.5' : 'h-9 text-sm px-3';
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div role="group" aria-label="שלב ההגשה" className="inline-flex items-center gap-1 p-1 rounded-md bg-surface shadow-[0_0_0_1px_var(--line)] max-w-full overflow-x-auto">
        {PIPELINE_STAGES.map((k, i) => {
          const past = currentIndex > i;
          const current = currentIndex === i;
          return (
            <React.Fragment key={k}>
              {i > 0 && <span className="text-ink-3 text-xs" aria-hidden>←</span>}
              <button
                type="button"
                aria-current={current ? 'step' : undefined}
                aria-label={current ? `${STATUS_CONFIG[k].label} (השלב הנוכחי)` : `העברה ל${STATUS_CONFIG[k].label}`}
                onClick={() => !current && onUpdateStatus(job.url, k)}
                className={`${h} rounded-[6px] inline-flex items-center gap-1.5 whitespace-nowrap transition-colors ${
                  current ? 'bg-accent-soft text-accent font-semibold'
                    : past ? 'text-ink-2 hover:bg-hover'
                      : 'text-ink-3 outline-1 outline-dashed outline-line-strong -outline-offset-1 hover:text-ink hover:bg-hover'
                }`}
              >
                {past && <Check size={13} strokeWidth={2.6} aria-hidden />}
                {STATUS_CONFIG[k].label}
              </button>
            </React.Fragment>
          );
        })}
      </div>
      {closed && (
        <span className={`text-[13px] font-semibold ${status === 'rejected' ? 'text-danger' : 'text-ink-2'}`}>
          נסגר: {STATUS_CONFIG[status].label}
        </span>
      )}
      <CloseMenu job={job} onUpdateStatus={onUpdateStatus} compact={size === 'sm'} />
    </div>
  );
};

export default ApplicationStepper;
