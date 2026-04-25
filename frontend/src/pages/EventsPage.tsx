import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/useStore';
import api from '@/api/client';
import { MapPin, Users, Activity, Search } from 'lucide-react';

const YEARS = ['2026', '2025', '2024', '2023'];

const EventsPage = () => {
  const navigate = useNavigate();
  const { setSelectedEvent } = useAppStore();
  const [yearFilter, setYearFilter] = useState('2024');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: events, isLoading } = useQuery({
    queryKey: ['events', yearFilter],
    queryFn: async () => {
      const res = await api.get(`/events/?year=${yearFilter}`);
      return res.data;
    },
  });

  const filteredEvents = useMemo(() => {
    if (!events) return [];
    return events.filter((event: any) =>
      event.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (event.location ?? '').toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [events, searchQuery]);

  return (
    <div className="px-12 pt-12 pb-20 max-w-5xl">

      {/* Header */}
      <div className="mb-10">
        <p className="font-sans text-[11px] tracking-widest uppercase text-sand-400 mb-2">
          Competition database
        </p>
        <h1 className="font-serif text-[40px] text-sand-900 leading-tight mb-7">
          Events <em className="italic text-sand-400">& competitions</em>
        </h1>

        {/* Controls */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-[360px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-sand-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by name or location…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-white border border-sand-300 rounded-md font-sans text-[13px] text-sand-900 placeholder-sand-400 outline-none focus:border-sand-500 transition-colors"
            />
          </div>

          <div className="flex gap-1">
            {YEARS.map(y => (
              <button
                key={y}
                onClick={() => setYearFilter(y)}
                className={`px-4 py-2 rounded-md border font-sans text-[13px] transition-colors
                  ${yearFilter === y
                    ? 'bg-sand-900 border-sand-900 text-sand-50 font-medium'
                    : 'bg-white border-sand-300 text-sand-500 hover:border-sand-500 hover:text-sand-900'
                  }`}
              >
                {y}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="border-t border-sand-200 mb-6" />

      {/* Count */}
      {!isLoading && (
        <p className="font-sans text-[12px] text-sand-400 mb-5">
          {filteredEvents.length} event{filteredEvents.length !== 1 ? 's' : ''} found
        </p>
      )}

      {/* Skeleton */}
      {isLoading && (
        <div className="flex flex-col gap-px">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-[76px] bg-sand-100 border border-sand-200 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {/* List */}
      {!isLoading && filteredEvents.length > 0 && (
        <div className="flex flex-col">
          {filteredEvents.map((event: any, idx: number) => (
            <button
              key={event.event_id}
              onClick={() => {
                setSelectedEvent(event.event_id);
                navigate(`/events/${event.event_id}`);
              }}
              className={`
                grid grid-cols-[1fr_auto] items-center gap-6 px-6 py-5
                bg-white border border-sand-200 text-left cursor-pointer
                hover:bg-sand-50 hover:z-10 transition-colors relative
                ${idx === 0 ? 'rounded-t-lg' : '-mt-px'}
                ${idx === filteredEvents.length - 1 ? 'rounded-b-lg' : ''}
              `}
            >
              <div>
                <div className="font-sans text-[15px] font-medium text-sand-900 mb-1.5">
                  {event.name}
                </div>
                <div className="flex items-center gap-4">
                  {event.location && (
                    <span className="flex items-center gap-1 font-sans text-[12px] text-sand-400">
                      <MapPin size={11} />
                      {event.location}
                    </span>
                  )}
                  <span className="font-sans text-[12px] text-sand-400">
                    {event.start_date} → {event.end_date}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1.5 px-3 py-1 bg-sand-100 rounded-full font-sans text-[11px] text-sand-600 font-medium">
                  <Users size={11} />
                  {event.team_count ?? '—'} teams
                </span>
                <span className="flex items-center gap-1.5 px-3 py-1 bg-accent-light rounded-full font-sans text-[11px] text-accent font-medium">
                  <Activity size={11} />
                  {event.match_count ?? '—'} matches
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Empty */}
      {!isLoading && filteredEvents.length === 0 && (
        <div className="py-20 text-center border border-dashed border-sand-300 rounded-lg">
          <Search size={32} className="text-sand-300 mx-auto mb-4" />
          <div className="font-serif italic text-[20px] text-sand-400 mb-2">No events found</div>
          <p className="font-sans text-[13px] text-sand-400 mb-5">
            Try a different year or clear your search
          </p>
          <button
            onClick={() => setSearchQuery('')}
            className="px-5 py-2 border border-sand-300 rounded-md font-sans text-[13px] text-sand-600 hover:border-sand-500 transition-colors"
          >
            Clear search
          </button>
        </div>
      )}
    </div>
  );
};

export default EventsPage;