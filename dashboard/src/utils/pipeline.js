import { FAILED_AT_STAGE, isFailed, isWorking, jobStage } from '../constants/jobStatus.js';

export const PIPELINE_STEPS = [
  { key: 'resolve', label: 'פענוח הקישור' },
  { key: 'scrape', label: 'סריקת תיאור המשרה' },
  { key: 'ai', label: 'ניתוח מול קורות החיים' },
];
const STEP_INDEX = { resolve: 0, scrape: 1, ai: 2, done: 3 };

// מצב כל צעד עבור סטטוס: done / working / waiting / failed / off
export const stepStates = (status) => {
  if (isFailed(status)) {
    const at = STEP_INDEX[FAILED_AT_STAGE[status] || 'resolve'];
    return PIPELINE_STEPS.map((_, i) => (i < at ? 'done' : i === at ? 'failed' : 'off'));
  }
  const current = STEP_INDEX[jobStage(status)] ?? 0;
  return PIPELINE_STEPS.map((_, i) => {
    if (i < current) return 'done';
    if (i === current) return isWorking(status) ? 'working' : 'waiting';
    return 'off';
  });
};
