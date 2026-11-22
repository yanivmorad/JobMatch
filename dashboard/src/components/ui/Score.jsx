import React from 'react';
import { Check, X } from 'lucide-react';
import { SCORE_BANDS, scoreBand, verdictOf } from '../../utils/jobView';

// מד ציון: המספר בדיו, המד בצבע הרצועה (מילוי + מסילה מאותה רצועה)
const Meter = ({ value, band, className = '' }) => {
  const b = SCORE_BANDS[band];
  return (
    <span className={`block overflow-hidden rounded-full ${b ? b.track : 'bg-sunken'} ${className}`}>
      <span
        className={`block h-full rounded-full transition-[width] duration-500 ${b ? b.fill : ''}`}
        style={{ width: `${Math.max(0, Math.min(100, Number(value) || 0))}%` }}
      />
    </span>
  );
};

// בשורת רשימה: מספר 22px מעל מד 36×4
export const RowScore = ({ score, size = 'md' }) => {
  const band = scoreBand(score);
  if (!band) {
    return <span className="w-11 shrink-0 text-center text-ink-3" aria-label="אין ציון">—</span>;
  }
  return (
    <span
      className="w-11 shrink-0 flex flex-col items-center gap-[5px] pt-0.5"
      role="meter"
      aria-valuenow={score}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`ציון התאמה ${score}, ${SCORE_BANDS[band].label}`}
    >
      <span className={`num font-semibold leading-none ${size === 'sm' ? 'text-lg' : 'text-[22px]'}`}>{score}</span>
      <Meter value={score} band={band} className="w-9 h-1" />
    </span>
  );
};

// בפרט המשרה: מספר-גיבור + /100 + מד מלא + מילת הרצועה
export const HeroScore = ({ score }) => {
  const band = scoreBand(score);
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-semibold text-ink-2">ציון התאמה</span>
      <div className="flex items-baseline gap-1.5">
        <span className="num text-[48px] max-sm:text-[40px] font-semibold leading-none tracking-[-0.03em]">{band ? score : '—'}</span>
        <span className="text-ink-3">/100</span>
      </div>
      <Meter value={score} band={band} className="h-1.5 w-full" />
      {band && <span className={`text-xs font-semibold ${SCORE_BANDS[band].text}`}>{SCORE_BANDS[band].label}</span>}
    </div>
  );
};

// פסק הדין: להגיש (✓ ירוק) / לא להגיש (✕ ניטרלי - זו עצה, לא שגיאה)
export const VerdictBadge = ({ job, size = 'sm' }) => {
  const v = verdictOf(job);
  if (size === 'lg') {
    if (v === 'none') return <span className="text-lg font-semibold text-ink-3">ללא המלצה</span>;
    const yes = v === 'yes';
    return (
      <span className={`inline-flex items-center gap-2.5 text-xl max-sm:text-lg font-bold ${yes ? 'text-go' : 'text-ink'}`}>
        <span className={`size-7 rounded-full inline-flex items-center justify-center text-ink-inverse ${yes ? 'bg-go-fill' : 'bg-ink'}`}>
          {yes ? <Check size={15} strokeWidth={3} aria-hidden /> : <X size={15} strokeWidth={3} aria-hidden />}
        </span>
        {v === 'other' ? job.recommendation : yes ? 'להגיש' : 'לא להגיש'}
      </span>
    );
  }
  if (v === 'none') return null;
  const yes = v === 'yes';
  return (
    <span className={`inline-flex items-center gap-1 h-[22px] px-2 rounded-full text-xs font-semibold whitespace-nowrap ${yes ? 'bg-go-soft text-go' : 'bg-sunken text-ink-2'}`}>
      {yes ? <Check size={12} strokeWidth={3} aria-hidden /> : <X size={12} strokeWidth={3} aria-hidden />}
      {v === 'other' ? job.recommendation : yes ? 'להגיש' : 'לא להגיש'}
    </span>
  );
};
