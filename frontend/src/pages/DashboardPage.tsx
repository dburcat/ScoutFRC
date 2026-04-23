import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '@/store/useStore'; // Import the Zustand store
import api from '@/api/client';

const DashboardPage = () => {
  // 1. Hook into the Global Store
  const { selectedEventId, setSelectedEvent } = useAppStore();

  // 2. Use the Global State to drive the data fetch
  const { data: scoutingData, isLoading, isError } = useQuery({
    // Adding selectedEventId to the key makes the fetch reactive
    queryKey: ['matches', selectedEventId], 
    queryFn: async () => {
      // If an event is selected, we filter by ID; otherwise, we get all matches
      const endpoint = selectedEventId 
        ? `/matches/?event_id=${selectedEventId}` 
        : '/matches/';
      const res = await api.get(endpoint);
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-500 font-medium">Loading match data...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6 bg-red-50 text-red-700 rounded-lg border border-red-200">
        Error loading match schedule. Please check if the backend is running.
      </div>
    );
  }

  return (
    <section className="animate-fadeIn">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold mb-1 text-gray-800 tracking-tight">Match Schedule</h2>
          <p className="text-gray-500">
            Viewing: <span className="font-semibold text-blue-600">{selectedEventId || 'All Events'}</span>
          </p>
        </div>

        {/* 3. Action Button to test the Zustand Store */}
        <div className="flex gap-2">
          {selectedEventId && (
            <button 
              onClick={() => setSelectedEvent(null)}
              className="px-3 py-1 text-xs text-gray-500 hover:text-gray-800 bg-gray-100 rounded transition"
            >
              Reset Filter
            </button>
          )}
          <button 
            onClick={() => setSelectedEvent('2026-championship')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition shadow-sm"
          >
            Switch to Championship
          </button>
        </div>
      </div>
      
      <div className="overflow-x-auto rounded-xl shadow-sm border border-gray-200 bg-white">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-gray-600 uppercase text-xs font-bold tracking-widest">
              <th className="p-4">Match / Team</th>
              <th className="p-4">Total Score</th>
              <th className="p-4">Auto Points</th>
              <th className="p-4">Endgame / Video</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {scoutingData && scoutingData.length > 0 ? (
              scoutingData.map((match: any) => (
                <React.Fragment key={match.match_id}>
                  {/* Match Group Header */}
                  <tr className="bg-gray-50/50 font-bold border-t border-gray-200">
                    <td className="p-4 text-gray-900 font-bold">Match {match.match_number}</td>
                    <td className="p-4 text-xs text-gray-500 uppercase">{match.match_type}</td>
                    <td className="p-4">
                      <span className="px-2 py-1 rounded-md bg-green-50 text-green-700 text-[10px] font-bold uppercase">
                        {match.processing_status}
                      </span>
                    </td>
                    <td className="p-4">
                      {match.video_url && (
                        <a href={match.video_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline text-sm">
                          Watch Video
                        </a>
                      )}
                    </td>
                  </tr>

                  {/* Alliances Detail */}
                  {match.alliances?.map((alliance: any) => (
                    <React.Fragment key={alliance.alliance_id}>
                      <tr className={alliance.color === 'red' ? 'bg-red-50/30' : 'bg-blue-50/30'}>
                        <td colSpan={4} className={`p-2 pl-4 text-[10px] font-black uppercase tracking-tighter ${
                          alliance.color === 'red' ? 'text-red-600' : 'text-blue-600'
                        }`}>
                          {alliance.color} Alliance
                        </td>
                      </tr>

                      {alliance.robot_performances?.map((perf: any) => (
                        <tr key={perf.perf_id} className="hover:bg-gray-50/80 transition-colors">
                          <td className="p-4 pl-10 text-gray-700 font-semibold border-l-4 border-transparent hover:border-blue-400">
                            Team {perf.team_id}
                          </td>
                          <td className="p-4 font-mono font-bold text-gray-800">
                            {perf.total_score || 0}
                          </td>
                          <td className="p-4 text-sm text-gray-500">
                            {perf.auto_score || 0}
                          </td>
                          <td className="p-4 text-sm text-gray-500">
                            {perf.endgame_score || 0}
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </React.Fragment>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="p-20 text-center text-gray-400 italic">
                  No match data found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default DashboardPage;