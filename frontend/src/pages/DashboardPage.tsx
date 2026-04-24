import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '@/store/useStore'; 
import api from '@/api/client';
import { Trophy, Activity, Hash, Layout } from 'lucide-react';

const DashboardPage = () => {
  const { selectedEventId, setSelectedEvent } = useAppStore();

  const { data: scoutingData, isLoading, isError } = useQuery({
    queryKey: ['matches', selectedEventId], 
    queryFn: async () => {
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
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-3xl font-black mb-1 text-gray-900 tracking-tight">Match Schedule</h2>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Trophy size={14} className="text-blue-500" />
            Active Event: <span className="font-bold text-gray-700">{selectedEventId || 'Global Stream'}</span>
          </div>
        </div>

        <div className="flex gap-3">
          {selectedEventId && (
            <button 
              onClick={() => setSelectedEvent(null)}
              className="px-4 py-2 text-sm font-bold text-gray-500 hover:text-gray-800 bg-white border border-gray-200 rounded-xl transition shadow-sm"
            >
              Clear Filter
            </button>
          )}
          <button 
            onClick={() => setSelectedEvent('2026-championship')}
            className="px-5 py-2 bg-blue-600 text-white rounded-xl text-sm font-bold hover:bg-blue-700 transition shadow-lg shadow-blue-100 flex items-center gap-2"
          >
            <Activity size={16} /> Championship View
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl shadow-sm border border-gray-200 bg-white">
        <table className="w-full border-collapse text-left border">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-gray-400 uppercase text-[10px] font-black tracking-widest">
              <th className="p-4 w-32 flex items-center gap-2"><Layout size={12}/> Alliance</th>
              <th className="p-4"><Hash size={12} className="inline mr-1"/> Team 1</th>
              <th className="p-4"><Hash size={12} className="inline mr-1"/> Team 2</th>
              <th className="p-4"><Hash size={12} className="inline mr-1"/> Team 3</th>
              <th className="p-4 text-right">Score</th>
              <th className="p-4 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {scoutingData && scoutingData.length > 0 ? (
              scoutingData.map((match: any) => (
                <React.Fragment key={match.match_id}>
                  {/* Match Identifier Row */}
                  <tr className="bg-gray-50/30">
                    <td colSpan={5} className="px-4 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-tighter">
                      {match.match_type} — Match {match.match_number}
                    </td>
                  </tr>

                  {/* Alliance Data Rows */}
                  {match.alliances?.map((alliance: any) => (
                    <tr 
                      key={alliance.alliance_id} 
                      className={`group transition-colors ${
                        alliance.color === 'red' ? 'hover:bg-red-50/50' : 'hover:bg-blue-50/50'
                      }`}
                    >
                      {/* Column 1: Alliance Color Label */}
                      <td className={`p-4 border-l-4 transition-all ${
                        alliance.color === 'red' 
                          ? 'border-red-500 bg-red-50/20 text-red-700' 
                          : 'border-blue-500 bg-blue-50/20 text-blue-700'
                      }`}>
                        <span className="font-black uppercase tracking-widest text-xs italic">
                          {alliance.color}
                        </span>
                      </td>

                      {/* Columns 2-4: Horizontal Team List */}
                      {alliance.robot_performances?.map((perf: any) => (
                        <td key={perf.perf_id} className="p-4">
                          <div className="flex flex-col">
                            <span className="text-sm font-black text-gray-800">
                            </span>
                            <span className="text-[9px] text-gray-400 font-bold uppercase tracking-tighter">
                              Robot {perf.perf_id.toString().slice(-1)}
                            </span>
                          </div>
                        </td>
                      ))}

                      {/* Column 5: Total Score */}
                      <td className="p-4 text-right">
                        <div className="flex flex-col items-end">
                          <span className="text-xl font-black text-gray-900 leading-none">
                            {alliance.total_score}
                          </span>
                        </div>
                      </td>

                      {/* Column 6: Match Status */}
                      <td className="p-4 text-right">
                        <span className={`px-2 py-1 text-xs font-bold rounded-full ${
                          match.processing_status === 'completed' 
                            ? 'bg-green-100 text-green-800'
                            : match.processing_status === 'in_progress'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-500'
                        }`}>
                          {match.processing_status.replace('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </React.Fragment>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="p-24 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center text-gray-300">
                      <Layout size={24} />
                    </div>
                    <p className="text-gray-400 font-medium italic">No matches found for this filter.</p>
                  </div>
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