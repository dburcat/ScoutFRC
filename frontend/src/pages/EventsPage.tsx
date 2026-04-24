import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/useStore';
import api from '@/api/client';
import { Calendar, MapPin, Users, Activity, Search, Trophy } from 'lucide-react';

const EventsPage = () => {
  const navigate = useNavigate();
  const { setSelectedEvent } = useAppStore();
  const [yearFilter, setYearFilter] = useState('2025');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: events, isLoading } = useQuery({
    queryKey: ['events', yearFilter],
    queryFn: async () => {
      const res = await api.get(`/events/?year=${yearFilter}`);
      return res.data;
    },
  });

  // Client-side filtering for immediate feedback
  const filteredEvents = useMemo(() => {
    if (!events) return [];
    return events.filter((event: any) =>
      event.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      event.location.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [events, searchQuery]);

  if (isLoading) return (
    <div className="flex justify-center items-center h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  );

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
        <div>
          <div className="flex items-center gap-2 mb-2 text-blue-600 font-bold uppercase tracking-wider text-sm">
            <Trophy size={18} />
            Competition Database
          </div>
          <h1 className="text-4xl font-black text-gray-900 tracking-tight">Search Events</h1>
        </div>

        <div className="flex flex-1 md:justify-end items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Filter by name or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm"
            />
          </div>

          <select 
            value={yearFilter} 
            onChange={(e) => setYearFilter(e.target.value)}
            className="border border-gray-200 rounded-xl px-4 py-3 bg-white shadow-sm font-semibold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="2026">2026</option>
            <option value="2025">2025</option>
          </select>
        </div>
      </div>

      {/* Grid */}
      {filteredEvents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredEvents.map((event: any) => (
            <button 
              key={event.event_id}
              onClick={() => {
                setSelectedEvent(event.event_id);
                navigate('/dashboard');
              }}
              className="text-left bg-white rounded-2xl border border-gray-100 p-6 hover:border-blue-500 hover:shadow-xl transition-all duration-300 group flex flex-col"
            >
              <h3 className="text-xl font-bold text-gray-800 group-hover:text-blue-600 mb-4 line-clamp-1 transition-colors">
                {event.name}
              </h3>
              
              <div className="space-y-3 text-sm text-gray-500 mb-8">
                <div className="flex items-center gap-2">
                  <MapPin size={16} className="text-blue-400" /> {event.location}
                </div>
                <div className="flex items-center gap-2">
                  <Calendar size={16} className="text-blue-400" /> {event.date}
                </div>
              </div>

              <div className="mt-auto pt-5 border-t border-gray-50 flex justify-between items-center">
                <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 rounded-full">
                  <Users size={14} className="text-blue-600" />
                  <span className="text-xs font-bold text-blue-700">{event.team_count} Teams</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 bg-green-50 rounded-full">
                  <Activity size={14} className="text-green-600" />
                  <span className="text-xs font-bold text-green-700">{event.match_count} Matches</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-32 bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200">
          <Search size={48} className="mx-auto text-gray-300 mb-4" />
          <p className="text-gray-500 font-medium text-lg">No events matching "{searchQuery}"</p>
          <button 
            onClick={() => setSearchQuery('')}
            className="mt-2 text-blue-600 font-bold hover:underline"
          >
            Clear search
          </button>
        </div>
      )}
    </div>
  );
};

export default EventsPage;