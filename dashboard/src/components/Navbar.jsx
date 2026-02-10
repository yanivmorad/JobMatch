import React from 'react';
import { Briefcase, PlusCircle, History, Send, User, Sparkles, Search } from 'lucide-react';

const Navbar = ({ activeTab, setActiveTab, counts, searchQuery, setSearchQuery }) => {
  const tabs = [
    { id: 'dashboard', label: 'דשבורד', icon: Sparkles },
    { id: 'active', label: 'משרות', icon: Briefcase, count: counts.active },
    { id: 'add', label: 'הוספה', icon: PlusCircle, count: counts.pending },
    { id: 'applied', label: 'נשלחו', icon: Send, count: counts.applied },
    { id: 'history', label: 'ארכיון', icon: History },
    { id: 'profile', label: 'פרופיל', icon: User },
  ];

  return (
    <div className="sticky top-0 z-50 px-6 py-5">
      <div className="max-w-[1600px] mx-auto w-full">
        <div className="bg-white/80 backdrop-blur-2xl border border-white/40 shadow-[0_12px_40px_-12px_rgba(0,0,0,0.08)] rounded-[2.5rem] px-8 py-3 flex items-center justify-between transition-all duration-300">
          
          {/* Logo Section - צד ימין */}
          <div 
            className="flex items-center gap-4 w-1/4 cursor-pointer group/logo"
            onClick={() => setActiveTab('dashboard')}
          >
            <div className="w-11 h-11 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/30 transition-transform group-hover/logo:rotate-6 active:scale-95">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div className="hidden xl:block">
              <h1 className="text-xl font-black text-slate-800 tracking-tight group-hover/logo:text-blue-600 transition-colors">JobMatch AI</h1>
            </div>
          </div>

          {/* Navigation Section - מרכז */}
          <div className="flex items-center justify-center gap-4 bg-slate-100/50 p-1.5 rounded-[2rem] border border-slate-200/50">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  relative flex items-center gap-3 px-6 py-3 rounded-2xl text-sm font-bold transition-all duration-300 whitespace-nowrap group
                  ${activeTab === tab.id
                    ? 'bg-white text-blue-600 shadow-sm ring-1 ring-slate-200'
                    : 'text-slate-500 hover:text-blue-600 hover:bg-white/80 hover:shadow-[0_0_20px_rgba(37,99,235,0.15)] hover:ring-1 hover:ring-blue-100'
                  }
                `}
              >
                {/* Icon עם אפקט Glow עדין ב-Hover */}
                <tab.icon className={`
                  w-5 h-5 transition-all duration-300 
                  ${activeTab === tab.id ? 'text-blue-600 scale-110' : 'text-slate-400 group-hover:text-blue-500 group-hover:drop-shadow-[0_0_8px_rgba(37,99,235,0.6)]'}
                `} />
                
                <span className="hidden md:block">{tab.label}</span>
                
                {tab.count > 0 && (
                  <span className={`
                    flex items-center justify-center min-w-[20px] h-[20px] px-1.5 rounded-full text-[10px] font-black transition-all
                    ${activeTab === tab.id 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-slate-200 text-slate-500 group-hover:bg-blue-100 group-hover:text-blue-600'
                    }
                  `}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Search Section - צד שמאל */}
          <div className="hidden lg:flex w-1/4 justify-end">
             <div className="relative flex items-center w-full max-w-[280px] bg-slate-100/80 rounded-2xl px-4 py-2 border border-slate-200/50 focus-within:ring-2 focus-within:ring-blue-100 focus-within:bg-white transition-all group">
                <Search className="w-4 h-4 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                <input 
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="חיפוש חופשי..."
                  className="bg-transparent border-none focus:ring-0 text-xs w-full mr-2 placeholder:text-slate-400 text-slate-700 font-bold"
                />
             </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Navbar;