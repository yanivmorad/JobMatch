# scraper_service

| Module | Role |
|---|---|
| `resolvers.py` | `URLResolver`: turns a HireMeTech link into the company's job page (Playwright, with `HIRE_ME_TECH_TOKEN`). Any HireMeTech failure (expired token, no redirect, no browser) raises `ResolveError(public_fallback=True)`, and the job is scraped from HireMeTech's public page instead. Other links pass through. |
| `scraper.py` | `Scraper.scrape(url)`: 1. public ATS JSON API (`site_apis.py`), 2. Jina Reader (site-specific selector, then the full page), 3. Playwright (waits for real page text). Each attempt is recorded in `trace` with a reason. |
| `site_apis.py` | Workday (`/wday/cxs/...`) and BambooHR (`/careers/{id}/detail`) - SPA pages whose content comes from these endpoints. |
| `utils.py` | `validate_content()` rejects login walls, cookie walls, bot checks, closed / removed jobs and pages without job content (fewer than 2 job signals); `failure_message()` turns the reasons into the message the user sees. |

Run `python scripts/test_scraper.py data/links.txt` to check every site after a change.
