import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { adminService } from '../../services/api';
import { Card, Button, Badge, Modal, LoadingState } from '../../components/UI';
import {
  Users,
  GraduationCap,
  BookOpen,
  FolderKanban,
  CheckCircle,
  ShieldCheck,
  AlertTriangle,
  Award,
  ArrowRight,
  Clock,
  Settings,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

export const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [vivas, setVivas] = useState([]);
  const [loading, setLoading] = useState(true);

  // Edit Duration Modal
  const [isDurationOpen, setIsDurationOpen] = useState(false);
  const [selectedViva, setSelectedViva] = useState(null);
  const [durationMinutes, setDurationMinutes] = useState(2);
  const [savingDuration, setSavingDuration] = useState(false);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, vivasRes] = await Promise.all([
        adminService.getStats(),
        adminService.getVivas(),
      ]);
      setStats(statsRes.data);
      setVivas(vivasRes.data.vivas || []);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const openDurationModal = (viva) => {
    setSelectedViva(viva);
    setDurationMinutes(viva.duration_minutes || Math.round((viva.duration_seconds || 120) / 60));
    setIsDurationOpen(true);
  };

  const handleSaveDuration = async (e) => {
    e.preventDefault();
    if (!selectedViva) return;
    setSavingDuration(true);
    try {
      await adminService.updateViva(selectedViva.id, {
        duration_minutes: Number(durationMinutes) || 2,
      });
      setIsDurationOpen(false);
      fetchDashboardData();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to update duration.');
    } finally {
      setSavingDuration(false);
    }
  };

  if (loading) return <LoadingState message="Loading university system administrator overview..." />;

  const userDistribution = [
    { name: 'Students', count: stats?.total_students || 0, color: '#10b981' },
    { name: 'Faculty', count: stats?.total_faculty || 0, color: '#6366f1' },
    { name: 'Admins', count: (stats?.total_users || 0) - (stats?.total_students || 0) - (stats?.total_faculty || 0), color: '#f43f5e' },
  ];

  const sessionData = [
    { name: 'Completed Vivas', count: stats?.completed_sessions || 0 },
    { name: 'In Progress / Other', count: (stats?.total_sessions || 0) - (stats?.completed_sessions || 0) },
    { name: 'Audited Grades', count: stats?.total_audits || 0 },
    { name: 'Logged Violations', count: stats?.total_violations || 0 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            Institutional Administration Portal
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Kalasalingam Academy of Research and Education • Comprehensive System Governance
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/admin/audit">
            <Button variant="secondary" size="sm" icon={ShieldCheck}>
              Mark Audit Trail
            </Button>
          </Link>
          <Link to="/admin/users">
            <Button variant="primary" size="sm" icon={Users}>
              Manage Accounts
            </Button>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-blue-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Users
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{stats?.total_users || 0}</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card className="border-l-4 border-l-emerald-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Viva Sessions
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{stats?.completed_sessions || 0}</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card className="border-l-4 border-l-indigo-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Mark Audits Logged
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{stats?.total_audits || 0}</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card className="border-l-4 border-l-rose-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Anti-Cheat Violations
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{stats?.total_violations || 0}</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
        </Card>
      </div>

      {/* Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recharts Bar Chart: System Activities */}
        <Card title="Assessment & Activity Overview" subtitle="System participation metrics">
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sessionData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Recharts Pie Chart: User Demographics */}
        <Card title="User Demographics" subtitle="Distribution of students, faculty, and administrators">
          <div className="h-64 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={userDistribution}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {userDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Viva Assessments & Session Timer Governance */}
      <Card title="Viva Assessments & Session Timer Governance" subtitle="Review active examinations and calibrate total session time">
        {vivas.length === 0 ? (
          <p className="text-xs text-slate-500 py-4 text-center">No viva assessments found in the system.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                <tr>
                  <th className="p-3">Viva Title</th>
                  <th className="p-3">Faculty</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Questions</th>
                  <th className="p-3">Total Viva Duration</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {vivas.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="p-3 font-semibold text-slate-900">{v.title}</td>
                    <td className="p-3 text-slate-600">{v.faculty_name || 'Faculty'}</td>
                    <td className="p-3">
                      <Badge variant={v.status === 'PUBLISHED' || v.status === 'ACTIVE' ? 'success' : 'warning'}>
                        {v.status}
                      </Badge>
                    </td>
                    <td className="p-3 font-mono text-slate-600">{v.question_count} in bank</td>
                    <td className="p-3">
                      <span className="inline-flex items-center gap-1 font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                        <Clock className="w-3 h-3" />
                        {v.duration_minutes || Math.round((v.duration_seconds || 120) / 60)} minutes
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        icon={Settings}
                        onClick={() => openDurationModal(v)}
                      >
                        Configure Duration
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Admin Edit Duration Modal */}
      <Modal
        isOpen={isDurationOpen}
        onClose={() => setIsDurationOpen(false)}
        title={`Configure Viva Duration: ${selectedViva?.title}`}
      >
        <form onSubmit={handleSaveDuration} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Total Viva Session Duration
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="60"
                step="1"
                required
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(e.target.value)}
                className="w-24 p-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
              />
              <span className="text-sm text-slate-600 font-medium">minutes</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Authoritative countdown duration configured for students. The timer does not reset between questions.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsDurationOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={savingDuration}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default AdminDashboard;
