import React, { useState, useEffect } from 'react';
import { adminService } from '../../services/api';
import { Card, Badge, LoadingState, EmptyState } from '../../components/UI';
import { ShieldCheck, History, Calendar, User, ArrowRight } from 'lucide-react';

export const AdminAuditPage = () => {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAudits = async () => {
      try {
        const res = await adminService.getAudits();
        setAudits(res.data.audits || []);
      } catch (err) {
        console.error('Failed to load audits:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAudits();
  }, []);

  if (loading) return <LoadingState message="Loading immutable mark audit logs..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
          Mark Audit Trail (Immutable Records)
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Kalasalingam Academy of Research and Education • ADMIN ONLY • Tamper-Evident History
        </p>
      </div>

      {/* Security Banner */}
      <Card className="bg-rose-50/70 border-rose-200">
        <div className="flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="text-xs text-rose-900 space-y-1">
            <h4 className="font-bold text-rose-950">Administrative Access Only (Confidential)</h4>
            <p>
              This audit ledger records all manual adjustments to AI-evaluated scores. Every record contains the original score,
              the modified score, the identity of the administrator who performed the modification, the official reason,
              and an immutable timestamp. Student and Faculty accounts are strictly blocked by backend security filters.
            </p>
          </div>
        </div>
      </Card>

      {audits.length === 0 ? (
        <EmptyState
          icon={History}
          title="No Mark Overrides Logged"
          description="All student grades currently reflect their original, untampered AI evaluations."
        />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Audit ID</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Student &amp; Viva</th>
                <th className="py-3 px-4 text-center">Previous Score</th>
                <th className="py-3 px-4 text-center">New / Status</th>
                <th className="py-3 px-4">Performed By</th>
                <th className="py-3 px-4">Official Reason</th>
                <th className="py-3 px-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {audits.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3 px-4 font-mono text-slate-400">#{a.id}</td>
                  <td className="py-3 px-4">
                    {a.action === 'DELETE_VIVA_RECORD' ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                        RECORD DELETED
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                        MARK OVERRIDE
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-900 block">{a.student_name}</span>
                    <span className="text-[11px] text-slate-500">{a.viva_title || 'Viva Assessment'}</span>
                  </td>
                  <td className="py-3 px-4 text-center font-mono font-medium text-slate-600">
                    {a.original_score} / 20
                  </td>
                  <td className="py-3 px-4 text-center">
                    {a.action === 'DELETE_VIVA_RECORD' ? (
                      <span className="text-[11px] font-semibold text-rose-600">
                        Reset / Reattempt Enabled
                      </span>
                    ) : (
                      <span className="font-mono font-bold text-blue-900 text-sm">
                        {a.edited_score} / 20
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-700 font-medium">
                    <span className="inline-flex items-center gap-1">
                      <User className="w-3 h-3 text-slate-400" />
                      {a.edited_by_name}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-700 max-w-xs">
                    <p className="line-clamp-2 bg-slate-100/70 p-1.5 rounded text-[11px] leading-relaxed">
                      {a.reason}
                    </p>
                  </td>
                  <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                    {a.created_at ? new Date(a.created_at).toLocaleString() : 'N/A'}
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

export default AdminAuditPage;
