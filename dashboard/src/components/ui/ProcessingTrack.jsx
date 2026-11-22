import React from 'react';
import { PIPELINE_STEPS, stepStates } from '../../utils/pipeline';

const Dot = ({ state }) => {
  if (state === 'failed') {
    return <span className="text-danger-fill font-bold text-[13px] leading-[8px] w-2 text-center" aria-hidden>✕</span>;
  }
  const cls = {
    done: 'bg-go-fill',
    working: 'bg-accent pulse-dot',
    waiting: 'border-2 border-accent',
    off: 'bg-line',
  }[state];
  return <span className={`size-2 rounded-full box-border shrink-0 ${cls}`} aria-hidden />;
};

// שלוש נקודות מחוברות: פענוח → סריקה → ניתוח. מחליף את פסי האחוזים המומצאים.
const ProcessingTrack = ({ status }) => {
  const states = stepStates(status);
  return (
    <span className="inline-flex items-center shrink-0" aria-hidden>
      {states.map((s, i) => (
        <React.Fragment key={PIPELINE_STEPS[i].key}>
          {i > 0 && (
            <span className={`w-4 h-0.5 ${states[i - 1] === 'done' && s !== 'off' ? 'bg-go-fill' : 'bg-line'}`} />
          )}
          <Dot state={s} />
        </React.Fragment>
      ))}
    </span>
  );
};

export default ProcessingTrack;
