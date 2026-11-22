import React from 'react';
import { AlertCircle, ArrowLeft, Ban, Check } from 'lucide-react';
import { RowScore, VerdictBadge } from '../ui/Score';
import { RunBar } from '../run/RunMini';
import { runSummary } from '../../utils/queueView';
import { PIPELINE_STAGES, STATUS_CONFIG } from '../../constants/statusConfig';
import {
  SCORE_BANDS, isSameDay, runCounts, jobHeading, jobKey, reasonLine, relativeTime, scoreBand, sortForReview, verdictOf,
} from '../../utils/jobView';

const Panel = ({ title, action, children, className = '' }) => (
  <section className={`bg-surface rounded-lg shadow-[0_0_0_1px_var(--line)] flex flex-col ${className}`}>
    <div className="flex items-center gap-3 px-5 max-sm:px-4 pt-4 pb-2">
      <h2 className="text-[15px] font-bold flex-1">{title}</h2>
      {action}
    </div>
    {children}
  </section>
);

const LinkButton = ({ onClick, children }) => (
  <button type="button" onClick={onClick} className="text-[13px] font-semibold text-accent hover:underline inline-flex items-center gap-1">
    {children}<ArrowLeft size={14} aria-hidden />
  </button>
);

// כל אריח הוא דלת למסך שלו - לא מדד יוהרה
const Tile = ({ label, value, sub, onClick, tone, loading, extra }) => (
  <button
    type="button"
    onClick={onClick}
    className={`text-start rounded-lg px-[18px] py-4 flex flex-col gap-1 transition-shadow ${tone === 'danger' ? 'bg-danger-soft hover:shadow-[0_0_0_1px_var(--danger)]' : 'bg-surface shadow-[0_0_0_1px_var(--line)] hover:shadow-[0_0_0_1px_var(--line-strong)]'}`}
  >
    <span className={`text-xs font-semibold flex items-center gap-1.5 ${tone === 'danger' ? 'text-danger' : 'text-ink-2'}`}>
      {tone === 'danger' && <AlertCircle size={14} aria-hidden />}{label}
    </span>
    <span className="flex items-center gap-2 min-h-[34px]">
      {loading ? <span className="skeleton h-7 w-10" /> : <span className="num text-[28px] font-semibold leading-tight">{value}</span>}
      {extra}
    </span>
    <span className="text-xs text-ink-3">{sub}</span>
  </button>
);

const OverviewScreen = ({ jobs, activeJobs, runJobs, failedCount, onNavigate, onOpenJob, now, loading }) => {
  const sorted = sortForReview(activeJobs);
  const recommended = sorted.filter((j) => verdictOf(j) === 'yes').length;
  const newToday = activeJobs.filter((j) => isSameDay(j.analyzed_at, now)).length;
  const openApps = jobs.filter((j) => !j.is_archived && PIPELINE_STAGES.includes(j.application_status));
  const ghosted = jobs.filter((j) => j.application_status === 'ghosted').length;
  const stageCounts = PIPELINE_STAGES.map((k) => ({ k, n: openApps.filter((j) => j.application_status === k).length }));

  const summary = runSummary(runJobs);
  const counts = runCounts(summary);
  const lastRunAt = runJobs.reduce((t, j) => {
    const v = new Date(j.created_at).getTime();
    return Number.isNaN(v) ? t : Math.max(t, v);
  }, 0);

  const bands = ['strong', 'partial', 'weak'].map((b) => ({ b, n: activeJobs.filter((j) => scoreBand(j.suitability_score) === b).length }));
  const bandTotal = bands.reduce((a, x) => a + x.n, 0);

  return (
    <div className="px-7 max-sm:px-4 py-6 max-sm:py-4 grid grid-cols-1 xl:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)] gap-5 content-start">
      <div className="xl:col-span-2 grid grid-cols-4 max-lg:grid-cols-2 gap-3">
        <Tile label="מחכות להחלטה" value={activeJobs.length} sub={newToday ? `נותחו היום: ${newToday}` : 'אין חדשות היום'} onClick={() => onNavigate('active')} loading={loading} />
        <Tile
          label="מומלצות להגשה"
          value={recommended}
          sub={`מתוך ${activeJobs.length} שנותחו`}
          onClick={() => onNavigate('active')}
          loading={loading}
          extra={recommended > 0 && <span className="inline-flex items-center gap-1 h-[22px] px-2 rounded-full text-xs font-semibold bg-go-soft text-go"><Check size={12} strokeWidth={3} aria-hidden />להגיש</span>}
        />
        <Tile label="הגשות פעילות" value={openApps.length} sub={ghosted ? `${ghosted} נסגרו ללא מענה` : 'מעקב אחרי תהליכים'} onClick={() => onNavigate('applied')} loading={loading} />
        {failedCount > 0 ? (
          <Tile label="דורשות טיפול" value={failedCount} sub="נכשלו בצינור · לתיקון" onClick={() => onNavigate('add')} tone="danger" loading={loading} />
        ) : (
          <Tile label="כישלונות בצינור" value={0} sub="הכל עבר תקין" onClick={() => onNavigate('add')} loading={loading} />
        )}
      </div>

      <Panel title="הבאות בתור" action={activeJobs.length > 0 && <LinkButton onClick={() => onNavigate('active')}>לכל {activeJobs.length}</LinkButton>}>
        <ul className="pb-2">
          {loading && Array.from({ length: 5 }, (_, i) => (
            <li key={i} className="flex gap-3.5 items-center px-5 py-3 border-t border-line" aria-hidden>
              <span className="skeleton w-10 h-7" /><span className="flex-1 flex flex-col gap-2"><span className="skeleton h-3 w-2/3" /><span className="skeleton h-2.5 w-1/3" /></span>
            </li>
          ))}
          {!loading && sorted.length === 0 && (
            <li className="px-5 py-8 text-center text-ink-2">אין משרות שמחכות להחלטה. משרות חדשות יופיעו כאן אחרי הניתוח.</li>
          )}
          {!loading && sorted.slice(0, 6).map((j) => {
            const { title, sub } = jobHeading(j);
            const reason = reasonLine(j);
            return (
              <li key={jobKey(j)} className="border-t border-line first:border-t-0 sm:first:border-t">
                <button type="button" onClick={() => onOpenJob(j)} className="w-full text-start flex gap-3.5 items-center px-5 max-sm:px-4 py-2.5 hover:bg-hover">
                  <RowScore score={j.suitability_score} size="sm" />
                  <span className="flex-1 min-w-0 flex flex-col">
                    <span className="truncate font-semibold" dir="auto">{title}{sub && <span className="font-normal text-ink-2"> · {sub}</span>}</span>
                    <span className="truncate text-xs text-ink-3">
                      {reason.kind === 'blocker' && <Ban size={12} className="inline-block align-[-2px] me-1 text-danger" aria-label="חוסם:" />}
                      <span dir="auto">{reason.text}</span>
                    </span>
                  </span>
                  <span className={verdictOf(j) === 'yes' ? '' : 'max-sm:hidden'}><VerdictBadge job={j} /></span>
                </button>
              </li>
            );
          })}
        </ul>
      </Panel>

      <div className="flex flex-col gap-5">
        <Panel
          title="הריצה האחרונה"
          action={<span className="text-xs text-ink-3">{summary.total ? `${lastRunAt ? relativeTime(lastRunAt, now) : ''} · ${summary.total} קישורים` : ''}</span>}
        >
          <div className="px-5 max-sm:px-4 pb-4 flex flex-col gap-3" aria-live="polite">
            {summary.total ? (
              <>
                <RunBar summary={summary} height="h-2" />
                <p className="flex flex-wrap gap-x-4 gap-y-1 text-[13px]">
                  <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-go-fill" aria-hidden />{counts.done} הושלמו</span>
                  {counts.failed > 0 && <span className="flex items-center gap-1.5 text-danger font-semibold"><span className="size-2 rounded-full bg-danger-fill" aria-hidden />{counts.failed} נכשלו</span>}
                  <span className="flex items-center gap-1.5 text-ink-2"><span className={`size-2 rounded-full box-border ${counts.processing ? 'bg-accent pulse-dot' : 'border-2 border-accent'}`} aria-hidden />{counts.processing} בעיבוד</span>
                </p>
              </>
            ) : (
              <p className="text-[13px] text-ink-2">שום קישור לא נכנס בשעה האחרונה.</p>
            )}
            <LinkButton onClick={() => onNavigate('add')}>{summary.total ? 'לפירוט הריצה' : 'להוספת משרות'}</LinkButton>
          </div>
        </Panel>

        <Panel title="איכות התור">
          <div className="px-5 max-sm:px-4 pb-4 flex flex-col gap-3">
            {bandTotal ? (
              <>
                <div className="flex gap-0.5 h-3" role="img" aria-label={bands.map((x) => `${SCORE_BANDS[x.b].label}: ${x.n}`).join(', ')}>
                  {bands.filter((x) => x.n).map((x) => (
                    <span
                      key={x.b}
                      title={`${SCORE_BANDS[x.b].label}: ${x.n}`}
                      className={`${SCORE_BANDS[x.b].fill} first:rounded-s-full last:rounded-e-full min-w-2`}
                      style={{ flexGrow: x.n, flexBasis: 0 }}
                    />
                  ))}
                </div>
                <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
                  {bands.map((x) => (
                    <li key={x.b} className="flex items-center gap-1.5"><span className={`size-2.5 rounded-sm ${SCORE_BANDS[x.b].fill}`} aria-hidden /><strong className="num font-semibold text-ink">{x.n}</strong> {SCORE_BANDS[x.b].label.replace('התאמה ', '')}</li>
                  ))}
                </ul>
                <p className="text-xs text-ink-3">חזקה 70+, חלקית 50–69, חלשה מתחת ל-50.</p>
              </>
            ) : (
              <p className="text-[13px] text-ink-2">אין משרות לבדיקה.</p>
            )}
          </div>
        </Panel>

        <Panel title="הגשות" action={<LinkButton onClick={() => onNavigate('applied')}>ללוח</LinkButton>}>
          <ol className="px-5 max-sm:px-4 pb-4 flex items-center gap-2 text-[13px]">
            {stageCounts.map(({ k, n }, i) => (
              <React.Fragment key={k}>
                {i > 0 && <span className="text-ink-3" aria-hidden>←</span>}
                <li className={`flex-1 flex flex-col items-center py-2 rounded-md ${n ? 'bg-accent-soft text-accent' : 'bg-sunken text-ink-2'}`}>
                  <strong className="num text-xl font-semibold">{n}</strong>{STATUS_CONFIG[k].label}
                </li>
              </React.Fragment>
            ))}
          </ol>
        </Panel>
      </div>
    </div>
  );
};

export default OverviewScreen;
