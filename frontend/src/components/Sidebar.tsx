import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Trophy, Users, Settings, LogOut } from 'lucide-react';
import { useAppStore } from '@/store/useStore';

const Sidebar = () => {
  const { isSidebarOpen } = useAppStore();

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Events', path: '/events', icon: Trophy },
    { name: 'Teams', path: '/teams', icon: Users },
  ];

  return (
    <aside className={`h-screen bg-gray-900 text-white transition-all duration-300 ${isSidebarOpen ? 'w-64' : 'w-20'} flex flex-col fixed left-0 top-0`}>
      <div className="p-6 font-black text-2xl tracking-tighter border-b border-gray-800 italic text-blue-500">
        {isSidebarOpen ? 'SCOUTER' : 'S'}
      </div>

      <nav className="flex-1 mt-6 px-3 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `
              flex items-center gap-4 px-4 py-3 rounded-xl transition-all
              ${isActive ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}
            `}
          >
            <item.icon size={22} />
            {isSidebarOpen && <span className="font-semibold">{item.name}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-800 space-y-2">
        <button className="flex items-center gap-4 px-4 py-3 text-gray-400 hover:text-red-400 w-full transition-colors">
          <LogOut size={22} />
          {isSidebarOpen && <span className="font-semibold">Logout</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;