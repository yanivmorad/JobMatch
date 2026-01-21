// src/components/ActiveJobsTab.jsx
import React from 'react';
import JobCard from './JobCard'; // וודא שהנתיב נכון

const ActiveJobsTab = ({ jobs, onAction, onDelete, onRefresh }) => {
  if (jobs.length === 0) {
    return (
      <div className="text-center py-20 bg-white rounded-3xl border-2 border-dashed border-slate-200">
        <h3 className="text-xl font-medium text-slate-400">אין משרות פעילות כרגע...</h3>
        <p className="text-slate-400 mt-2 text-sm">זה הזמן להוסיף לינקים חדשים מהלינקדאין!</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-800">הצעות עבודה בשבילך</h2>
        <button 
          onClick={onRefresh}
          className="text-sm text-blue-600 hover:text-blue-700 font-semibold"
        >
          רענן נתונים
        </button>
      </div>

      {/* Grid של כרטיסיות */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {jobs.map((job) => (
          <JobCard 
            key={job.url} 
            job={job} 
            onAction={onAction} 
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
};

export default ActiveJobsTab;