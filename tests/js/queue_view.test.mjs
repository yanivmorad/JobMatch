// בדיקות ללוגיקת הניטור החי של הדשבורד (dashboard/src/utils/queueView.js).
// מורץ מ-pytest: tests/test_dashboard_queue_view.py (node --test).
import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  currentRun,
  IDLE_POLL_MS,
  isInCurrentRun,
  isPlaceholder,
  jobDisplayName,
  pollDelay,
  QUEUE_POLL_MS,
  runSummary,
  shouldRefetch,
} from '../../dashboard/src/utils/queueView.js';

const NOW = Date.parse('2026-11-22T20:30:00Z');
const minutesAgo = (m) => new Date(NOW - m * 60000).toISOString();

// --- שם המשרה בניטור ---

test('new job: company is the temporary URL -> show the site, not a cut URL', () => {
  const job = { url: 'https://www.comeet.com/jobs/supercom/46.00A/qa/96.47E', company: 'https://www.comeet.com/jobs/supercom/46.00A/qa/96.47E', job_title: null };
  assert.equal(jobDisplayName(job), 'comeet.com');
});

test('title from the WhatsApp message is shown while the job is still being scraped', () => {
  const job = { url: 'https://jobs.lever.co/CYE/52b0', company: 'https://jobs.lever.co/CYE/52b0', job_title: 'Cybersecurity Project Coordinator' };
  assert.equal(jobDisplayName(job), 'Cybersecurity Project Coordinator');
});

test('title and company together once both are known', () => {
  assert.equal(jobDisplayName({ url: 'https://x.com/1', company: 'Supercom', job_title: 'Junior QA' }), 'Junior QA · Supercom');
});

test('company only (old jobs had job_title "Unknown")', () => {
  assert.equal(jobDisplayName({ url: 'https://x.com/1', company: 'Wix', job_title: 'Unknown' }), 'Wix');
});

test('source_url (the original link) is preferred for the site name', () => {
  const job = { url: 'https://www.comeet.com/jobs/a/1', source_url: 'https://hiremetech.com/job/5', company: null, job_title: null };
  assert.equal(jobDisplayName(job), 'hiremetech.com');
});

test('nothing usable at all', () => {
  assert.equal(jobDisplayName({ url: 'manual://abc', company: null, job_title: '' }), 'משרה בתהליך');
});

test('placeholders mirror the server (job_fields.is_placeholder)', () => {
  for (const v of [null, undefined, '', '  Unknown ', 'Identifying...', 'לא צוין', 'https://a.com/1', 'manual://x', 'HireMeTech', '(שם החברה מוסתר בדף הציבורי של HireMeTech)']) {
    assert.equal(isPlaceholder(v), true, `expected placeholder: ${v}`);
  }
  for (const v of ['Supercom', 'Junior QA', 'Company Builder Ltd']) {
    assert.equal(isPlaceholder(v), false, `expected real value: ${v}`);
  }
});

// --- אילו משרות בניטור ---

test('every processing job is in the run, however old', () => {
  for (const status of ['NEW', 'PENDING_RESOLVE', 'RESOLVING', 'WAITING_FOR_SCRAPE', 'SCRAPING', 'WAITING_FOR_AI', 'ANALYZING']) {
    assert.equal(isInCurrentRun({ status, created_at: minutesAgo(600) }, NOW), true, status);
  }
});

test('a job that finished in the last hour stays visible with its outcome', () => {
  assert.equal(isInCurrentRun({ status: 'COMPLETED', analyzed_at: minutesAgo(5) }, NOW), true);
  assert.equal(isInCurrentRun({ status: 'NO_DATA', updated_at: minutesAgo(59) }, NOW), true);
  assert.equal(isInCurrentRun({ status: 'FAILED_RESOLVE', updated_at: null, created_at: minutesAgo(10) }, NOW), true);
});

test('old finished jobs are not in the run', () => {
  assert.equal(isInCurrentRun({ status: 'COMPLETED', analyzed_at: minutesAgo(61) }, NOW), false);
  assert.equal(isInCurrentRun({ status: 'FAILED_SCRAPE', updated_at: minutesAgo(120) }, NOW), false);
});

test('an old job whose updated_at moved (ghosted by maintenance) is not "finished now"', () => {
  // באג אפשרי: התחזוקה סימנה 15 הגשות ישנות כ-ghosted והזיזה להן את updated_at להיום
  const job = { status: 'COMPLETED', analyzed_at: minutesAgo(60 * 24 * 30), updated_at: minutesAgo(1) };
  assert.equal(isInCurrentRun(job, NOW), false);
});

test('completed job without analyzed_at / bad dates are not shown', () => {
  assert.equal(isInCurrentRun({ status: 'COMPLETED', analyzed_at: null }, NOW), false);
  assert.equal(isInCurrentRun({ status: 'COMPLETED', analyzed_at: 'not a date' }, NOW), false);
});

test('small clock skew (server a bit ahead of the browser) still counts as recent', () => {
  assert.equal(isInCurrentRun({ status: 'COMPLETED', analyzed_at: minutesAgo(-1) }, NOW), true);
});

test('the run is ordered by submission (id), so rows do not jump around', () => {
  const jobs = [
    { id: 386, status: 'COMPLETED', analyzed_at: minutesAgo(1) },
    { id: 12, status: 'COMPLETED', analyzed_at: minutesAgo(9999) },
    { id: 380, status: 'SCRAPING' },
    { id: 383, status: 'NO_DATA', updated_at: minutesAgo(2) },
  ];
  assert.deepEqual(currentRun(jobs, NOW).map(j => j.id), [380, 383, 386]);
});

test('the real 22.11 run: 8 links, one closed, all visible with their state', () => {
  const run = [
    { id: 379, status: 'NO_DATA', updated_at: minutesAgo(18) },
    ...[380, 381, 382, 383, 384, 385, 386].map((id, i) => ({ id, status: 'COMPLETED', analyzed_at: minutesAgo(17 - i) })),
  ];
  const visible = currentRun(run, NOW);
  assert.equal(visible.length, 8);
  assert.deepEqual(runSummary(visible), { total: 8, resolve: 0, scrape: 0, ai: 0, done: 7, failed: 1 });
});

test('summary counts each stage', () => {
  const jobs = ['PENDING_RESOLVE', 'RESOLVING', 'WAITING_FOR_SCRAPE', 'SCRAPING', 'SCRAPING', 'WAITING_FOR_AI', 'ANALYZING', 'COMPLETED', 'FAILED_ANALYSIS', 'DUPLICATE']
    .map(status => ({ status }));
  assert.deepEqual(runSummary(jobs), { total: 10, resolve: 2, scrape: 3, ai: 2, done: 1, failed: 2 });
});

// --- רענון ---

test('poll fast while something is processing, slower when idle - but always poll', () => {
  assert.equal(pollDelay(true), QUEUE_POLL_MS);
  assert.equal(pollDelay(false), IDLE_POLL_MS);
  assert.ok(IDLE_POLL_MS > 0 && IDLE_POLL_MS <= 30000);
});

test('jobs added outside the dashboard are noticed on the first check', () => {
  // הבאג: הדשבורד טען 155 משרות שהושלמו, 8 נוספו דרך ה-API -> לא הופיעו בכלל
  const loaded = Array.from({ length: 155 }, () => ({ status: 'COMPLETED' }));
  const snapshot = { counts: { COMPLETED: 155, PENDING_RESOLVE: 8 }, version: '1795378254.5:163' };
  assert.equal(shouldRefetch(null, snapshot, loaded), true);
});

test('first check with nothing new does not refetch the whole list', () => {
  const loaded = [{ status: 'COMPLETED' }, { status: 'SCRAPING' }];
  const snapshot = { counts: { COMPLETED: 1, SCRAPING: 1 }, version: 'v1' };
  assert.equal(shouldRefetch(null, snapshot, loaded), false);
});

test('first check: same total but a job moved stage -> refetch', () => {
  const loaded = [{ status: 'SCRAPING' }, { status: 'COMPLETED' }];
  const snapshot = { counts: { COMPLETED: 2 }, version: 'v1' };
  assert.equal(shouldRefetch(null, snapshot, loaded), true);
});

test('later checks refetch only when the version changed', () => {
  const snapshot = { counts: { COMPLETED: 2 }, version: 'v2' };
  assert.equal(shouldRefetch('v1', snapshot, []), true);
  assert.equal(shouldRefetch('v2', snapshot, []), false);
});

test('a broken snapshot never triggers a refetch loop', () => {
  assert.equal(shouldRefetch(null, null, []), false);
  assert.equal(shouldRefetch('v1', {}, []), false);
  assert.equal(shouldRefetch('v1', { version: null }, []), false);
});
