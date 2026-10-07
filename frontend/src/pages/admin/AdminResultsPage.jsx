import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { adminService } from '../../services/api';
import { Card, Button, Badge, Modal, LoadingState, EmptyState } from '../../components/UI';
import { Award, Edit3, ShieldAlert, CheckCircle, Search, History, Trash2, AlertTriangle, AlertCircle } from 'lucide-react';

export const AdminResultsPage = () => {
  const [results, setResults] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [statusNotification, setStatusNotification] = useState(null);

  // Edit Mark Modal
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [targetResult, setTargetResult] = useState(null);
  const [newScore, setNewScore] = useState('');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);

  // Delete Record Modal
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleting, setDeleting] = useState(false);

  const fetchResults = async () => {
    try {
      const res = await adminService.getResults();
      setResults(res.data.results || []);
    } catch (err) {
      console.error('Failed to load results:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const openEditModal = (result) => {
    setTargetResult(result);
    setNewScore(result.final_score.toString());
    setReason('');
    setIsEditOpen(true);
  };

  const handleSaveMark = async (e) => {
    e.preventDefault();
    if (!reason.trim()) {
      alert('A clear reason is mandatory when modifying student marks.');
      return;
    }

    const num = parseFloat(newScore);
    if (isNaN(num) || num < 0 || num > 20) {
      alert('Mark must be between 0.0 and 20.0.');
      return;
    }

    setSaving(true);
    try {
      await adminService.editMark(targetResult.result_id, num, reason.trim());
      setIsEditOpen(false);
      setStatusNotification({
        type: 'success',
        message: 'Mark successfully updated and immutable audit entry created.',
      });
      fetchResults();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to update mark.');
    } finally {
      setSaving(false);
    }
  };

  const openDeleteModal = (result) => {
    setDeleteTarget(result);
    setDeleteReason('Administrative record reset / Reattempt re-authorization');
    setIsDeleteOpen(true);
  };

  const handleDeleteRecord = async (e) => {
    e.preventDefault();
    if (!deleteTarget) return;

    setDeleting(true);
    try {
      await adminService.deleteResult(deleteTarget.result_id, deleteReason.trim());
      setIsDeleteOpen(false);
      setDeleteTarget(null);
      setStatusNotification({
        type: 'success',
        message: 'Viva record deleted successfully. The student can attend this viva again.',
      });
      fetchResults();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to delete viva record.');
    } finally {
      setDeleting(false);
    }
  };

  const filtered = results.filter((r) => {
    const q = search.toLowerCase();
    return (
      r.student_name.toLowerCase().includes(q) ||
      (r.student_reg_no && r.student_reg_no.toLowerCase().includes(q)) ||
      r.student_email.toLowerCase().includes(q) ||
      r.viva_title.toLowerCase().includes(q)
    );
  });

  if (loading) return <LoadingState message="Loading student marks and scores..." />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            Student Marks &amp; Administrative Overrides
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Kalasalingam Academy of Research and Education • Authorized Score Modifications &amp; Attempt Management
          </p>
        </div>

        <Link to="/admin/mark-audit">
          <Button variant="secondary" size="sm" icon={History}>
            View Immutable Audit Logs
          </Button>
        </Link>
      </div>

      {/* Success Notification Banner */}
      {statusNotification && (
        <div
          className={`p-4 rounded-xl border flex items-start justify-between gap-3 ${
            statusNotification.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          <div className="flex items-center gap-2 text-sm font-semibold">
            {statusNotification.type === 'success' ? (
              <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            )}
            <span>{statusNotification.message}</span>
          </div>
          <button
            onClick={() => setStatusNotification(null)}
            className="text-xs text-slate-400 hover:text-slate-600 font-bold px-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="bg-white p-3 rounded-xl border border-slate-200">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by student, register no, email, or viva..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={Award}
          title="No Student Results Found"
          description="Completed student viva submissions will appear here for administrative oversight."
        />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Student</th>
                <th className="py-3 px-4">Viva Assessment</th>
                <th className="py-3 px-4 text-center">Q1 (/10)</th>
                <th className="py-3 px-4 text-center">Q2 (/10)</th>
                <th className="py-3 px-4 text-center">Q3 (/10)</th>
                <th className="py-3 px-4 text-center">Best-2 Score (/20)</th>
                <th className="py-3 px-4">Audit Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((r) => (
                <tr key={r.result_id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-900 block">{r.student_name}</span>
                    <span className="text-[11px] text-slate-500 font-mono">
                      {r.student_reg_no || r.student_email}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-700 font-medium">{r.viva_title}</td>
                  <td className="py-3 px-4 text-center font-mono">{r.q1_score}</td>
                  <td className="py-3 px-4 text-center font-mono">{r.q2_score}</td>
                  <td className="py-3 px-4 text-center font-mono">{r.q3_score}</td>
                  <td className="py-3 px-4 text-center font-bold text-blue-900 font-mono text-sm">
                    {r.final_score} / 20
                  </td>
                  <td className="py-3 px-4">
                    {r.has_been_edited ? (
                      <Badge variant="warning">
                        Edited by Admin ({r.audit_count})
                      </Badge>
                    ) : (
                      <Badge variant="success">Original AI Score</Badge>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        icon={Edit3}
                        onClick={() => openEditModal(r)}
                      >
                        Edit Mark
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        icon={Trash2}
                        onClick={() => openDeleteModal(r)}
                        className="bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200"
                      >
                        Delete Record
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Edit Mark Modal */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Admin Mark Adjustment"
        maxWidth="max-w-md"
      >
        {targetResult && (
          <form onSubmit={handleSaveMark} className="space-y-4">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
              <div>
                <span className="text-slate-500">Student: </span>
                <strong className="text-slate-800">{targetResult.student_name}</strong>
              </div>
              <div>
                <span className="text-slate-500">Viva: </span>
                <span className="text-slate-700">{targetResult.viva_title}</span>
              </div>
              <div>
                <span className="text-slate-500">Current Final Score: </span>
                <strong className="text-blue-900 font-mono">{targetResult.final_score} / 20</strong>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                New Final Score (Out of 20)
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="20"
                required
                value={newScore}
                onChange={(e) => setNewScore(e.target.value)}
                className="w-full p-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono font-bold"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Mandatory Reason for Modification
              </label>
              <textarea
                rows={3}
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="State the official justification (e.g. Special re-evaluation approved by Academic Dean, microphone noise compensation, etc.)..."
                className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <div className="p-2.5 bg-rose-50 border border-rose-200 rounded text-[11px] text-rose-800 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
              <span>
                <strong>Immutable Audit Logging:</strong> This change will be permanently logged with your admin ID, the original score, the new score, and timestamp.
              </span>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setIsEditOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" loading={saving}>
                Confirm Mark Override
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* Delete Record Confirmation Modal */}
      <Modal
        isOpen={isDeleteOpen}
        onClose={() => !deleting && setIsDeleteOpen(false)}
        title="Delete Viva Record?"
        maxWidth="max-w-md"
      >
        {deleteTarget && (
          <form onSubmit={handleDeleteRecord} className="space-y-4">
            <div className="p-3 bg-rose-50/70 border border-rose-200 rounded-xl space-y-2">
              <div className="flex items-start gap-2 text-rose-800">
                <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <p className="font-bold text-rose-950">
                    This will remove this student's viva attempt and result.
                  </p>
                  <p className="text-rose-700">
                    The student will be allowed to attend this viva again.
                  </p>
                </div>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-500">Student:</span>
                <strong className="text-slate-800">{deleteTarget.student_name}</strong>
              </div>
              {deleteTarget.student_reg_no && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Register No:</span>
                  <span className="font-mono text-slate-700">{deleteTarget.student_reg_no}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-500">Viva Assessment:</span>
                <span className="text-slate-700 text-right">{deleteTarget.viva_title}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Recorded Score:</span>
                <strong className="text-slate-900 font-mono">{deleteTarget.final_score} / 20</strong>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Reason for Record Deletion
              </label>
              <textarea
                rows={2}
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="Reason for deleting record and resetting student eligibility..."
                className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-rose-500 resize-none bg-white"
              />
            </div>

            <div className="text-[11px] text-slate-500 space-y-1 bg-slate-50 p-2.5 rounded border border-slate-200">
              <div className="font-semibold text-slate-700">System Safeguard Guarantee:</div>
              <ul className="list-disc list-inside space-y-0.5 text-slate-600">
                <li>The student's account will <strong>NOT</strong> be deleted.</li>
                <li>The viva assessment &amp; question bank will <strong>NOT</strong> be deleted.</li>
                <li>Other students' results remain completely intact.</li>
                <li>An immutable deletion audit entry will be logged for administrative history.</li>
              </ul>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                disabled={deleting}
                onClick={() => setIsDeleteOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="danger"
                loading={deleting}
              >
                Delete Record
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};

export default AdminResultsPage;
