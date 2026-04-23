import React from 'react';
import { useQuery } from '@tanstack/react-query'; // 1. Import hook
import api from '@/api/axios';

const DashboardPage = () => {
  // 2. Replace useEffect/useState with useQuery
  const { data: scoutingData, isLoading, isError } = useQuery({
    queryKey: ['matches'],
    queryFn: async () => {
      const res = await api.get('/matches/');
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
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-1 text-gray-800 tracking-tight">Match Schedule</h2>
        <p className="text-gray-500">Real-time performance data sorted by alliance.</p>
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
                  {/* Match Header Row */}
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

                  {/* Alliance and Robot Nesting */}
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