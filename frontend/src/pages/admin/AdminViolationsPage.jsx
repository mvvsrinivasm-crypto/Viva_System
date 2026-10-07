import React, { useState, useEffect } from 'react';
import { adminService } from '../../services/api';
import { Card, Badge, LoadingState, EmptyState } from '../../components/UI';
import { AlertTriangle, ShieldAlert, Clock, User } from 'lucide-react';

export const AdminViolationsPage = () => {
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchViolations = async () => {
      try {
        const res = await adminService.getViolations();
        setViolations(res.data.violations || []);
      } catch (err) {
        console.error('Failed to load violations:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchViolations();
  }, []);

  if (loading) return <LoadingState message="Loading anti-cheating violation records..." />;

  const getViolationBadge = (type) => {
    switch (type) {
      case 'FULLSCREEN_EXIT':
        return <Badge variant="danger">FULLSCREEN_EXIT</Badge>;
      case 'TAB_SWITCH':
        return <Badge variant="warning">TAB_SWITCH</Badge>;
      case 'COPY_ATTEMPT':
      case 'PASTE_ATTEMPT':
      case 'CUT_ATTEMPT':
        return <Badge variant="purple">{type}</Badge>;
      case 'CONTEXT_MENU_ATTEMPT':
        return <Badge variant="primary">CONTEXT_MENU</Badge>;
      default:
        return <Badge variant="default">{type}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
          Anti-Cheat Violation Monitoring
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Kalasalingam Academy of Research and Education • Distraction-Free Proctored Mode Logs
        </p>
      </div>

      {violations.length === 0 ? (
        <EmptyState
          icon={ShieldAlert}
          title="No Violations Recorded"
          description="No anti-cheating infractions have been logged during student viva sessions."
        />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Violation ID</th>
                <th className="py-3 px-4">Session ID</th>
                <th className="py-3 px-4">Student</th>
                <th className="py-3 px-4">Violation Type</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Details / Metadata</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {violations.map((v) => (
                <tr key={v.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3 px-4 font-mono text-slate-400">#{v.id}</td>
                  <td className="py-3 px-4 font-mono text-slate-500">Session #{v.session_id}</td>
                  <td className="py-3 px-4 font-semibold text-slate-900">
                    <span className="flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-slate-400" />
                      {v.student_name}
                    </span>
                  </td>
                  <td className="py-3 px-4">{getViolationBadge(v.type)}</td>
                  <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                    {v.timestamp ? new Date(v.timestamp).toLocaleString() : 'N/A'}
                  </td>
                  <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                    {v.metadata ? JSON.stringify(v.metadata) : 'None'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
};

export default AdminViolationsPage;
