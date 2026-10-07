import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  FileText,
  Award,
  PlusCircle,
  Users,
  ShieldCheck,
  AlertTriangle,
  FolderKanban,
  CheckCircle2,
} from 'lucide-react';

export const Sidebar = () => {
  const { isStudent, isFaculty, isAdmin } = useAuth();

  const studentLinks = [
    { to: '/student/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/student/vivas', icon: FolderKanban, label: 'Available Vivas' },
    { to: '/student/results', icon: Award, label: 'My Viva Results' },
  ];

  const facultyLinks = [
    { to: '/faculty/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/faculty/vivas', icon: FolderKanban, label: 'My Vivas' },
    { to: '/faculty/students', icon: Users, label: 'Students' },
    { to: '/faculty/results', icon: Award, label: 'Results' },
  ];

  const adminLinks = [
    { to: '/admin/dashboard', icon: LayoutDashboard, label: 'System Overview' },
    { to: '/admin/users', icon: Users, label: 'User Directory' },
    { to: '/admin/vivas', icon: FolderKanban, label: 'All Vivas' },
    { to: '/admin/results', icon: Award, label: 'Results & Marks' },
    { to: '/admin/mark-audit', icon: ShieldCheck, label: 'Mark Audit Logs' },
    { to: '/admin/violations', icon: AlertTriangle, label: 'Anti-Cheat Violations' },
  ];

  const links = isStudent ? studentLinks : isFaculty ? facultyLinks : isAdmin ? adminLinks : [];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 min-h-[calc(100vh-4rem)] flex flex-col justify-between p-4 border-r border-slate-800">
      <div className="space-y-6">
        {/* Role Header */}
        <div className="px-3 pt-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {isStudent && 'Student Portal'}
            {isFaculty && 'Faculty Portal'}
            {isAdmin && 'Administrator Portal'}
          </p>
        </div>

        {/* Navigation list */}
        <nav className="space-y-1.5">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span>{link.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Institutional footer */}
      <div className="pt-4 border-t border-slate-800 px-2 text-center">
        <p className="text-[11px] text-slate-400 font-medium">
          KARE Viva Evaluation System
        </p>
        <p className="text-[10px] text-slate-500 mt-0.5">
          Version 2.0 • PostgreSQL
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;
