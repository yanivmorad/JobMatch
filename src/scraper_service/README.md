# Scraper Service - Modular Architecture

## Overview
The scraper logic has been refactored into a modular package for better maintainability and extensibility.

## Structure

```
src/
├── scraper_service/
│   ├── __init__.py       # Package initialization
│   ├── utils.py          # Text cleaning and validation utilities
│   └── resolvers.py      # URL resolution for special sites (HireMeTech, etc.)
└── scraper.py            # Main Scraper class (uses the service modules)
```

## Components

### 1. `utils.py`
Contains pure utility functions:
- `is_content_valid(text)` - Validates scraped content
- `clean_text(text)` - Cleans text (removes URLs, images, excess whitespace)

### 2. `resolvers.py`
Contains the `URLResolver` class that handles special job sites:
- **HireMeTech**: Authenticates and resolves to actual company URLs
- Extensible for additional sites

### 3. `scraper.py`
Main `Scraper` class that:
1. Uses `URLResolver` to handle special sites
2. Scrapes with Jina AI (primary)
3. Falls back to Playwright (secondary)
4. Uses `utils` functions for validation and cleaning

## Usage

The external API remains unchanged:

```python
from scraper import Scraper

scraper = Scraper()
result = scraper.scrape("https://hiremetech.com/job/123")

# Returns:
# {
#     "source": "jina" or "local_browser",
#     "original_url": "https://hiremetech.com/job/123",
#     "resolved_url": "https://company.com/careers/456",
#     "full_description": "cleaned text..."
# }
```

## Benefits

✅ **Modular**: Easy to add new site resolvers  
✅ **Testable**: Each component can be tested independently  
✅ **Maintainable**: Clear separation of concerns  
✅ **Backward Compatible**: No changes needed to existing code using `Scraper`

## Adding New Site Resolvers

To add support for a new job site:

1. Edit `scraper_service/resolvers.py`
2. Add a new method to `URLResolver` class (e.g., `_resolve_newsite`)
3. Update the `resolve()` method to detect and handle the new site

Example:
```python
def resolve(self, url: str) -> str:
    if "hiremetech.com" in url:
        return self._resolve_hiremetech(url)
    elif "newsite.com" in url:  # Add new site
        return self._resolve_newsite(url)
    return url
```
