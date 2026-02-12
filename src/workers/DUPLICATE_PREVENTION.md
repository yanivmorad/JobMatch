# Worker URL Resolution & Duplicate Prevention

## Overview
The scrape worker now includes intelligent URL resolution and duplicate detection to prevent wasting resources on URLs that already exist in the database.

## Problem Solved

**Before**: When a HireMeTech URL was added:
1. Worker would scrape the HireMeTech page
2. Resolver would get the actual company URL
3. Content would be saved with the company URL
4. **BUT**: If someone later added the same HireMeTech job again, it would scrape it again, even though the company URL already exists in the DB

**After**: The worker now uses a **two-pass approach**:
1. **Pass 1**: Detects HireMeTech URLs, resolves them, updates the database, and continues to next job
2. **Pass 2**: Worker picks up the updated URL and scrapes it (no resolution needed)

## Workflow

```
PASS 1: Resolution & Database Update
─────────────────────────────────────
Job URL: https://hiremetech.com/job/123
         │
         ▼
┌────────────────────────────────────────┐
│ STEP 1: Detect Special URL            │
│ Is this HireMeTech? → YES              │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ STEP 2: Resolve URL                   │
│ Use resolver.resolve()                 │
│ Result: https://greenhouse.io/job/456  │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ STEP 3: Check Database                │
│ Does greenhouse.io/job/456 exist?      │
└────────────────────────────────────────┘
         │
         ├─► YES → Delete duplicate job
         │         Skip to next job
         │
         └─► NO  → Update URL in database
                   Set status = WAITING_FOR_SCRAPE
                   Continue to next job
                   (Don't scrape yet!)

═══════════════════════════════════════════

PASS 2: Actual Scraping (Next Iteration)
─────────────────────────────────────────
Job URL: https://greenhouse.io/job/456 ← Updated!
         │
         ▼
┌────────────────────────────────────────┐
│ STEP 1: Detect Special URL            │
│ Is this HireMeTech? → NO               │
│ (Already resolved!)                    │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ STEP 2: Scrape the URL                │
│ - Jina AI (primary)                    │
│ - Playwright (fallback)                │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ STEP 3: Save to Database               │
│ - full_description                     │
│ - company, job_title                   │
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
async def delete_job_by_id(job_id: int):
    """Delete a job by its ID"""
    pool = await get_pool()
    await pool.execute("DELETE FROM jobs WHERE id = $1", job_id)

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
Updated `scrape_worker()` with two-pass logic:

**PASS 1**: Pre-scrape URL resolution
- Detects if URL is from HireMeTech
- Uses `scraper.resolver.resolve()` to get company URL
- Checks for duplicates
- Updates URL in database
- Continues to next job (no scraping yet!)

**PASS 2**: Actual scraping (next iteration)
- Worker picks up the updated URL
- No resolution needed (already done!)
- Scrapes and saves content

## Benefits

✅ **No Double Resolution**: URL is resolved only once  
✅ **Prevents Duplicate Scraping**: Checks before any expensive operations  
✅ **Database Always Accurate**: URL is updated before scraping  
✅ **Saves Resources**: No wasted API calls or processing time  
✅ **Cleaner Logs**: Clear separation between resolution and scraping  

## Example Logs

### Scenario 1: New HireMeTech Job (Pass 1 - Resolution)
```
🕷️ Processing: https://hiremetech.com/job/123
🔍 Detected HireMeTech URL, resolving...
✅ Resolved: https://hiremetech.com/job/123 → https://greenhouse.io/job/456
📝 Updating job URL in database: https://hiremetech.com/job/123 → https://greenhouse.io/job/456
✓ URL updated. Continuing to next job - worker will pick this up again with new URL.
```

### Scenario 2: Same Job (Pass 2 - Scraping)
```
🕷️ Processing: https://greenhouse.io/job/456
🕷️ Scraping: https://greenhouse.io/job/456
📡 Scraping via Jina: https://greenhouse.io/job/456
✅ Scrape complete for: https://greenhouse.io/job/456
```

### Scenario 3: Duplicate Detected
```
🕷️ Processing: https://hiremetech.com/job/789
🔍 Detected HireMeTech URL, resolving...
✅ Resolved: https://hiremetech.com/job/789 → https://greenhouse.io/job/456
⏭️ DUPLICATE DETECTED: Resolved URL 'https://greenhouse.io/job/456' 
   already exists in DB (Job ID: 42). Deleting duplicate job ID 89.
```

## Future Enhancements

This pattern can be extended to other job sites:

```python
# In scrape_worker
if "hiremetech.com" in original_url:
    resolved_url = await asyncio.to_thread(
        scraper.resolver.resolve, original_url
    )
elif "othersite.com" in original_url:
    resolved_url = await asyncio.to_thread(
        scraper.resolver.resolve, original_url
    )
```

Just add the site detection logic to `scraper_service/resolvers.py` and it will work automatically!
