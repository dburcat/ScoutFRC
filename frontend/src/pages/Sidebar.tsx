import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Trophy, Users, RefreshCw, LogOut } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Events',    path: '/events',    icon: Trophy },
  { name: 'Teams',     path: '/teams',     icon: Users },
  { name: 'Sync',      path: '/sync',      icon: RefreshCw },
];

const Sidebar = () => {
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-screen w-[200px] bg-sand-100 border-r border-sand-300 flex flex-col px-4 py-7 z-40">

      {/* Logo */}
      <div className="pb-5 mb-8 border-b border-sand-300">
        <div className="font-serif text-[22px] text-sand-900 leading-none">Scouter</div>
        <div className="font-serif italic text-[13px] text-sand-500 mt-1">FRC Analytics</div>
      </div>

      {/* Nav */}
      <nav className="flex-1 flex flex-col gap-0.5">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] transition-colors no-underline
               ${isActive
                 ? 'bg-sand-200 text-sand-900 font-medium'
                 : 'text-sand-500 hover:bg-sand-200 hover:text-sand-900'
               }`
            }
          >
            <item.icon size={15} strokeWidth={1.75} />
            {item.name}
          </NavLink>
        ))}
      </nav>

      {/* User + logout */}
      <div className="pt-4 border-t border-sand-300">
        {user && (
          <div className="flex items-center gap-2.5 px-1 mb-2.5">
            <div className="w-7 h-7 rounded-full bg-sand-200 border border-sand-300 flex items-center justify-center text-[11px] font-medium text-sand-600 shrink-0">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <div className="text-[12px] font-medium text-sand-900 truncate">{user.username}</div>
              <div className="text-[10px] text-sand-500">{user.role}</div>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-1.5 rounded-md text-[13px] text-sand-500 hover:text-red-700 hover:bg-red-50 transition-colors"
        >
          <LogOut size={14} />
          Sign out
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;