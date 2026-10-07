import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar';

export const AppLayout = () => {
  return (
    <div className="min-h-screen bg-[#f4f7fa] flex flex-col font-sans">
      {/* Single Unified Institutional Navigation Header */}
      <Navbar />

      {/* Main Content Area naturally below navigation */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <Outlet />
      </main>

      {/* Institutional Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 px-4 text-center text-xs text-slate-500">
        <p>© 2026 Kalasalingam Academy of Research and Education. All Rights Reserved.</p>
        <p className="mt-0.5 text-[11px] text-slate-400">
          KARE Viva Evaluation System • Kalasalingam LMS Institutional Architecture
        </p>
      </footer>
    </div>
  );
};

export default AppLayout;
