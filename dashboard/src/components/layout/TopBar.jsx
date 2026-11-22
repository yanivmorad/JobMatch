import React from 'react';
import { Plus, Search, X } from 'lucide-react';
import Button from '../ui/Button';

// סרגל עליון של כל מסך: כותרת + שורת מצב, חיפוש חופשי, והוספת משרות
const TopBar = ({ title, subtitle, searchQuery, setSearchQuery, showSearch = true, onAdd, actions }) => (
  <header className="sticky top-0 z-30 bg-page/95 backdrop-blur-sm border-b border-line">
    <div className="min-h-[72px] max-sm:min-h-0 px-7 max-sm:px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-2.5">
      <div className="flex-1 min-w-0">
        <h1 className="text-xl max-sm:text-lg font-bold tracking-[-0.01em]">{title}</h1>
        {subtitle && <p className="text-[13px] text-ink-2 truncate">{subtitle}</p>}
      </div>
      {actions}
      {showSearch && (
        <label className="order-last sm:order-none basis-full sm:basis-auto flex items-center gap-2 w-full sm:w-[300px] h-10 px-3 rounded-md bg-surface border border-line-strong text-ink-3 focus-within:outline-2 focus-within:outline-accent focus-within:outline-offset-1">
          <Search size={16} aria-hidden />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="חיפוש משרה, חברה או קישור"
            aria-label="חיפוש משרה, חברה או קישור"
            className="flex-1 min-w-0 bg-transparent outline-none text-ink [&::-webkit-search-cancel-button]:hidden"
          />
          {searchQuery && (
            <button type="button" onClick={() => setSearchQuery('')} aria-label="ניקוי החיפוש" className="size-6 inline-flex items-center justify-center rounded hover:bg-hover text-ink-2">
              <X size={14} aria-hidden />
            </button>
          )}
        </label>
      )}
      {onAdd && (
        <Button variant="primary" onClick={onAdd} className="max-sm:hidden">
          <Plus size={16} strokeWidth={2.4} aria-hidden />
          הוספת משרות
        </Button>
      )}
    </div>
  </header>
);

export default TopBar;
