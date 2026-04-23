import { create } from 'zustand';

interface AppState {
  selectedEventId: string | null;
  setSelectedEvent: (id: string | null) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedEventId: null,
  setSelectedEvent: (id) => set({ selectedEventId: id }),
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
}));