# scraper_service

| Module | Role |
|---|---|
| `resolvers.py` | `URLResolver`: turns a HireMeTech link into the company's job page with `HIRE_ME_TECH_TOKEN`: first HireMeTech's own API (no browser), then a Playwright click on "Apply" when the API gives no link. Any HireMeTech failure (expired/rejected token, no link, no browser) raises `ResolveError(public_fallback=True)`, and the job is read from HireMeTech's public API instead. Other links pass through. |
| `hiremetech.py` | `GET /api/jobs/{id}` - the endpoint HireMeTech's page calls. Without login it returns the full description, level, experience and skills; only the company name and apply link are masked. With a valid token they are included. |
| `scraper.py` | `Scraper.scrape(url)`: 1. public JSON API (`site_apis.py`), 2. Jina Reader (site-specific selector, then the full page), 3. the raw HTML (`html_extract.py`, for server-rendered pages Jina truncates), 4. Playwright (waits for real page text). Each attempt is recorded in `trace` with a reason. |
| `site_apis.py` | Workday (`/wday/cxs/...`), BambooHR (`/careers/{id}/detail`) and HireMeTech (`/api/jobs/{id}`) - SPA pages whose content comes from these endpoints. A HireMeTech job with only a title ends as NO_DATA instead of being scored on the title. |
| `html_extract.py` | Raw HTML -> the Jina-style document (`main`/`article`, no scripts/nav/footer). Its soft failures (`direct_*`, e.g. an empty SPA shell) never decide "no data" on their own. |
| `utils.py` | `validate_content()` rejects login walls, cookie walls, bot checks, closed / removed jobs and pages without job content (fewer than 2 job signals); `failure_message()` turns the reasons into the message the user sees. |

Run `python scripts/test_scraper.py data/links.txt` to check every site after a change.
