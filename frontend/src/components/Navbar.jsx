import React, { useState } from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LogOut,
  Menu,
  X,
  GraduationCap,
  BookOpen,
  Shield,
  LayoutDashboard,
  FolderKanban,
  Award,
  Users,
  ShieldCheck,
} from 'lucide-react';

export const Navbar = () => {
  const { user, logout, isStudent, isFaculty, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getHomePath = () => {
    if (isAdmin) return '/admin/dashboard';
    if (isFaculty) return '/faculty/dashboard';
    if (isStudent) return '/student/dashboard';
    return '/';
  };

  // Student Navigation
  const studentNavItems = [
    { label: 'Dashboard', to: '/student/dashboard' },
    { label: 'Available Vivas', to: '/student/vivas' },
    { label: 'My Viva Results', to: '/student/results' },
  ];

  // Faculty Navigation
  const facultyNavItems = [
    { label: 'Dashboard', to: '/faculty/dashboard' },
    { label: 'My Vivas', to: '/faculty/vivas' },
    { label: 'Students', to: '/faculty/students' },
    { label: 'Results', to: '/faculty/results' },
  ];

  // Admin Navigation — Mark Audit is STRICTLY ADMIN ONLY
  const adminNavItems = [
    { label: 'Dashboard', to: '/admin/dashboard' },
    { label: 'Users', to: '/admin/users' },
    { label: 'Vivas', to: '/admin/vivas' },
    { label: 'Results', to: '/admin/results' },
    { label: 'Mark Audit', to: '/admin/mark-audit', adminOnly: true },
  ];

  const currentNavItems = isStudent
    ? studentNavItems
    : isFaculty
    ? facultyNavItems
    : isAdmin
    ? adminNavItems
    : [{ label: 'Home', to: '/' }];

  const getRoleBadge = (role) => {
    switch (role) {
      case 'ADMIN':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
            <Shield className="w-2.5 h-2.5" /> Admin
          </span>
        );
      case 'FACULTY':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-300">
            <BookOpen className="w-2.5 h-2.5" /> Faculty
          </span>
        );
      case 'STUDENT':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <GraduationCap className="w-2.5 h-2.5" /> Student
          </span>
        );
    }
  };

  const getUserInitial = () => {
    if (user?.name) return user.name.charAt(0).toUpperCase();
    if (user?.email) return user.email.charAt(0).toUpperCase();
    return 'U';
  };

  return (
    <header className="sticky top-0 z-50 bg-[#5bb2f5] border-b border-[#439edb] shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left: Official KARE Logo (Exactly ONCE in global navigation) */}
          <div className="flex items-center gap-4 lg:gap-6">
            <Link to={getHomePath()} className="flex items-center shrink-0" title="KARE Viva Evaluation System">
              <div className="bg-white px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-lg border border-white/60 shadow-xs flex items-center">
                <img
                  src="/kare_logo.png"
                  alt="Kalasalingam Academy of Research and Education"
                  className="h-7 sm:h-8 md:h-9 w-auto max-w-[180px] sm:max-w-[210px] object-contain"
                />
              </div>
            </Link>

            {/* Desktop Horizontal Navigation Links (LMS Style with active amber bar) */}
            {user && (
              <nav className="hidden md:flex items-center gap-1 lg:gap-2">
                {currentNavItems.map((item, index) => {
                  const currentFullUrl = location.pathname + location.search;
                  const isActive = item.to.includes('?')
                    ? currentFullUrl === item.to
                    : location.pathname === item.to && !location.search;

                  return (
                    <Link
                      key={`${item.to}-${index}`}
                      to={item.to}
                      className={`relative px-3 py-2 text-sm font-medium transition-colors ${
                        isActive
                          ? 'text-[#072448] font-bold border-b-[3px] border-amber-400'
                          : 'text-[#0a2f58] hover:text-[#061830] hover:bg-white/20 rounded-md'
                      }`}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            )}
          </div>

          {/* Right: User Information & Actions */}
          <div className="flex items-center gap-2 sm:gap-3">
            {user ? (
              <>
                {/* User info text (hidden on small screens) */}
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs sm:text-sm font-semibold text-[#09264c] leading-tight">
                    {user.name}
                  </span>
                  <div className="flex items-center justify-end gap-1.5 mt-0.5">
                    {getRoleBadge(user.role)}
                  </div>
                </div>

                {/* Initial Avatar Circle (Purple circle matching LMS reference) */}
                <div
                  className="w-8 h-8 rounded-full bg-[#8b3d88] text-white flex items-center justify-center font-bold text-xs uppercase shadow-xs shrink-0 select-none border border-white/40"
                  title={`${user.name} (${user.role})`}
                >
                  {getUserInitial()}
                </div>

                {/* Logout Button */}
                <button
                  onClick={handleLogout}
                  title="Sign out of portal"
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-[#0c315b] bg-white/85 hover:bg-white hover:text-rose-700 rounded-lg shadow-xs border border-white/60 transition-all cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Logout</span>
                </button>

                {/* Mobile Menu Button */}
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="md:hidden p-1.5 rounded-lg text-[#0c315b] hover:bg-white/30 transition-colors cursor-pointer"
                  aria-label="Toggle navigation menu"
                >
                  {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="px-3 py-1.5 text-xs font-semibold text-[#0a2f58] hover:text-[#061830] hover:bg-white/20 rounded-lg transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-3.5 py-1.5 text-xs font-semibold text-white bg-[#0284c7] hover:bg-[#0369a1] rounded-lg transition-colors shadow-xs"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && user && (
        <div className="md:hidden bg-[#51a7e6] border-t border-[#4196d2] px-4 py-3 space-y-1 shadow-md">
          {/* User details summary on mobile */}
          <div className="pb-2 mb-2 border-b border-white/20 sm:hidden">
            <p className="text-xs font-semibold text-[#09264c]">{user.name}</p>
            <p className="text-[11px] text-white/80">{user.email}</p>
            <div className="mt-1">{getRoleBadge(user.role)}</div>
          </div>

          {currentNavItems.map((item, index) => {
            const currentFullUrl = location.pathname + location.search;
            const isActive = item.to.includes('?')
              ? currentFullUrl === item.to
              : location.pathname === item.to && !location.search;
            return (
              <Link
                key={`mobile-${item.to}-${index}`}
                to={item.to}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-white/30 text-[#072448] font-bold border-l-4 border-amber-400 pl-2'
                    : 'text-[#09264c] hover:bg-white/20'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
};

export default Navbar;
