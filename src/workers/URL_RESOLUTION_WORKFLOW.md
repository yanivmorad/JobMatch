# URL Resolution Workflow - Updated

## Problem Solved

**Previous Issue**: The worker was resolving HireMeTech URLs twice:
1. First resolution in the worker to check for duplicates
2. Second resolution inside `scraper.scrape()` during actual scraping
3. This wasted time and resources

**New Solution**: Two-pass approach
1. **First pass**: Resolve URL, update database, continue to next job
2. **Second pass**: Worker picks up the updated URL and scrapes it (no resolution needed)

## New Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ ITERATION 1: URL Resolution & Database Update              │
└─────────────────────────────────────────────────────────────┘

Job URL: https://hiremetech.com/job/123
Status: WAITING_FOR_SCRAPE
         │
         ▼
┌────────────────────────────────────────┐
│ Detect: Is this HireMeTech?            │
│ → YES                                  │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Resolve URL                            │
│ Result: https://greenhouse.io/job/456  │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Check: Does greenhouse URL exist?      │
│ → NO (new job)                         │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ UPDATE DATABASE:                       │
│ - url = https://greenhouse.io/job/456  │
│ - status = WAITING_FOR_SCRAPE          │
└────────────────────────────────────────┘
         │
         ▼
    CONTINUE to next job
    (Don't scrape yet!)

═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│ ITERATION 2: Actual Scraping (Next Worker Cycle)           │
└─────────────────────────────────────────────────────────────┘

Job URL: https://greenhouse.io/job/456  ← Updated!
Status: WAITING_FOR_SCRAPE
         │
         ▼
┌────────────────────────────────────────┐
│ Detect: Is this HireMeTech?            │
│ → NO (already resolved!)               │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ SCRAPE THE URL                         │
│ - Jina AI (primary)                    │
│ - Playwright (fallback)                │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ SAVE TO DATABASE:                      │
│ - full_description                     │
│ - company                              │
│ - job_title                            │
│ - status = WAITING_FOR_AI              │
└────────────────────────────────────────┘
         │
         ▼
    ✅ DONE!
```

## Code Changes

### 1. `db/jobs_repository.py`
Added new function:
```python
async def update_job_url(job_id: int, new_url: str):
    """
    Update the URL for a job (e.g., when HireMeTech URL resolves to company URL).
    Also resets status to WAITING_FOR_SCRAPE so the worker picks it up again.
    """
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE jobs 
        SET url = $1, status = 'WAITING_FOR_SCRAPE'
        WHERE id = $2
        """,
        new_url,
        job_id,
    )
```

### 2. `workers/worker_manager.py`
Updated logic:

**When HireMeTech URL is detected:**
1. Resolve to company URL
2. Check if company URL exists in DB
3. If duplicate → delete and skip
4. If new → **UPDATE URL in DB and continue** (don't scrape yet!)

**When normal URL is detected:**
1. Scrape directly (no resolution needed)

## Benefits

✅ **No Double Resolution**: URL is resolved only once  
✅ **Clean Separation**: Resolution and scraping are separate steps  
✅ **Database Always Accurate**: URL is updated before scraping  
✅ **Better Logging**: Clear visibility into what's happening  
✅ **Easier Debugging**: Each step is isolated  

## Example Logs

### Iteration 1: Resolution
```
🕷️ Processing: https://hiremetech.com/job/123
🔍 Detected HireMeTech URL, resolving...
✅ Resolved: https://hiremetech.com/job/123 → https://greenhouse.io/job/456
📝 Updating job URL in database: https://hiremetech.com/job/123 → https://greenhouse.io/job/456
✓ URL updated. Continuing to next job - worker will pick this up again with new URL.
```

### Iteration 2: Scraping
```
🕷️ Processing: https://greenhouse.io/job/456
🕷️ Scraping: https://greenhouse.io/job/456
📡 Scraping via Jina: https://greenhouse.io/job/456
✅ Scrape complete for: https://greenhouse.io/job/456
```

## Duplicate Detection

If the resolved URL already exists:
```
🕷️ Processing: https://hiremetech.com/job/123
🔍 Detected HireMeTech URL, resolving...
✅ Resolved: https://hiremetech.com/job/123 → https://greenhouse.io/job/456
⏭️ DUPLICATE DETECTED: Resolved URL 'https://greenhouse.io/job/456' 
   already exists in DB (Job ID: 42). Deleting duplicate job ID 89.
```

## Why This Approach?

1. **Separation of Concerns**: Resolution is a separate step from scraping
2. **Database Integrity**: URL is always correct before scraping
3. **Idempotent**: If worker crashes, it can resume cleanly
4. **Efficient**: No wasted resolution cycles
5. **Extensible**: Easy to add more resolution logic for other sites
