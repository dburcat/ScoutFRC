import { useQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Users, Loader, AlertCircle } from 'lucide-react';
import { type Team } from '@/types/models';
import { teamsQuery } from '@/api/queries';
import { clsx } from 'clsx';

export default function TeamsPage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'number' | 'name' | 'location' | 'rookie'>('number');

  const { data: teams = [], isLoading, isFetching, error } = useQuery(teamsQuery());

  // Filter teams by search query (number, name, school)
  const filteredTeams = useMemo(() => {
    if (!searchQuery.trim()) return teams;

    const query = searchQuery.toLowerCase();
    return teams.filter(team => 
      team.team_number.toString().includes(query) ||
      team.team_name?.toLowerCase().includes(query) ||
      team.school_name?.toLowerCase().includes(query) ||
      team.city?.toLowerCase().includes(query) ||
      team.state_prov?.toLowerCase().includes(query)
    );
  }, [teams, searchQuery]);

  // Sort teams based on selected sort option
  const sortedTeams = useMemo(() => {
    const sorted = [...filteredTeams];
    
    switch (sortBy) {
      case 'number':
        return sorted.sort((a, b) => a.team_number - b.team_number);
      case 'name':
        return sorted.sort((a, b) => 
          (a.team_name || '').localeCompare(b.team_name || '')
        );
      case 'location':
        return sorted.sort((a, b) => {
          const aLoc = `${a.state_prov || ''}${a.city || ''}`;
          const bLoc = `${b.state_prov || ''}${b.city || ''}`;
          return aLoc.localeCompare(bLoc);
        });
      case 'rookie':
        return sorted.sort((a, b) => (b.rookie_year || 0) - (a.rookie_year || 0));
      default:
        return sorted;
    }
  }, [filteredTeams, sortBy]);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <div className="px-6 py-3.5 border-b border-app-border flex-shrink-0 flex items-center justify-between gap-3">
        <div>
          <p className="text-[15px] font-medium text-white">Teams</p>
          <p className="text-[11px] text-slate-600 mt-0.5">
            {filteredTeams.length} of {teams.length} teams
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="bg-app-card border border-app-border rounded px-2 py-1 text-xs text-white cursor-pointer hover:border-app-muted focus:outline-none focus:ring-1 focus:ring-brand"
          >
            <option value="number">Sort: Team #</option>
            <option value="name">Sort: Name</option>
            <option value="location">Sort: Location</option>
            <option value="rookie">Sort: Rookie year</option>
          </select>
          <div className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', {
            'bg-green-500': !isFetching,
            'bg-brand animate-pulse': isFetching,
          })} />
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-6xl mx-auto space-y-4">
          {/* Search */}
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-600"
            />
            <input
              type="text"
              placeholder="Search by team number, name, school, or location…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg bg-app-card border border-app-border text-white placeholder-slate-600 focus:outline-none focus:border-brand/60 focus:ring-1 focus:ring-brand/20 text-sm"
            />
          </div>

          {/* Loading state */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader size={32} className="text-slate-700 mx-auto mb-3 animate-spin" />
                <p className="text-slate-500 text-sm">Loading teams…</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <AlertCircle size={32} className="text-red-500/50 mx-auto mb-3" />
                <p className="text-slate-500 text-sm">Failed to load teams</p>
                <p className="text-slate-700 text-xs mt-1">Please try refreshing</p>
              </div>
            </div>
          ) : filteredTeams.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Users size={32} className="text-slate-700 mx-auto mb-3" />
                <p className="text-slate-500 text-sm">
                  {teams.length === 0 ? 'No teams synced yet' : 'No matches for your search'}
                </p>
                <p className="text-slate-700 text-xs mt-1">
                  {teams.length === 0 
                    ? 'The scheduler will populate this automatically' 
                    : 'Try different search terms'}
                </p>
              </div>
            </div>
          ) : (
            <div className="bg-app-card border border-app-border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-app-border bg-app-muted/30">
                    <th className="px-4 py-3 text-left font-medium text-slate-400 w-16">#</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400">Team name</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400 hidden sm:table-cell">School</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400 hidden md:table-cell">Location</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400 hidden lg:table-cell">Rookie year</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedTeams.map((team, idx) => (
                    <tr
                      key={team.team_id}
                      onClick={() => navigate(`/teams/${team.team_id}`)}
                      className={clsx(
                        'border-b border-app-border hover:bg-app-muted/50 transition-colors cursor-pointer',
                        idx % 2 === 0 ? 'bg-app-card' : 'bg-app-muted/20'
                      )}
                    >
                      <td className="px-4 py-3 font-mono text-slate-300 font-medium">
                        {team.team_number}
                      </td>
                      <td className="px-4 py-3 text-white font-medium truncate">
                        {team.team_name || '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 truncate hidden sm:table-cell">
                        {team.school_name || '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 truncate hidden md:table-cell">
                        {team.city
                          ? `${team.city}${team.state_prov ? ', ' + team.state_prov : ''}`
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 hidden lg:table-cell">
                        {team.rookie_year || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
