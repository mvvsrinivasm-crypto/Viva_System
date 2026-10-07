import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api, { facultyService } from '../../services/api';
import { Card, Button, Badge, Modal, LoadingState, EmptyState } from '../../components/UI';
import {
  Users,
  Eye,
  Download,
  Award,
  Search,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Layers,
  Sparkles,
} from 'lucide-react';

export const FacultyResultsPage = () => {
  const { id: routeVivaId } = useParams();
  const navigate = useNavigate();

  const [vivas, setVivas] = useState([]);
  const [selectedVivaId, setSelectedVivaId] = useState(routeVivaId ? Number(routeVivaId) : null);
  const [studentSummaries, setStudentSummaries] = useState([]);
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);

  // View state: 'summaries' (1 row per student) or 'attempts' (all attempts log)
  const [viewTab, setViewTab] = useState('summaries');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // 1. Initial Load: Fetch Faculty Vivas
  useEffect(() => {
    const initPage = async () => {
      try {
        const vivasRes = await facultyService.getVivas();
        const vivasList = vivasRes.data.vivas || [];
        setVivas(vivasList);

        if (routeVivaId) {
          setSelectedVivaId(Number(routeVivaId));
        } else if (vivasList.length > 0) {
          setSelectedVivaId(vivasList[0].id);
        }
      } catch (err) {
        console.error('Failed to load faculty vivas:', err);
      } finally {
        setLoading(false);
      }
    };
    initPage();
  }, [routeVivaId]);

  // 2. Fetch results whenever selectedVivaId changes
  useEffect(() => {
    if (!selectedVivaId) return;

    const fetchResults = async () => {
      try {
        const res = await facultyService.getResults(selectedVivaId);
        setStudentSummaries(res.data.student_summaries || []);
        setResults(res.data.results || []);
        setStats(res.data.stats || null);
      } catch (err) {
        console.error('Failed to load results for viva:', err);
        setStudentSummaries([]);
        setResults([]);
        setStats(null);
      }
    };
    fetchResults();
  }, [selectedVivaId]);

  const handleVivaChange = (newVivaId) => {
    setSelectedVivaId(newVivaId);
    navigate(`/faculty/vivas/${newVivaId}/results`, { replace: true });
  };

  const handleDownloadMarks = async () => {
    if (!selectedVivaId) return;
    try {
      setDownloading(true);
      const res = await api.get(`/faculty/vivas/${selectedVivaId}/results/export`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      const vivaObj = vivas.find((v) => v.id === selectedVivaId);
      const titleClean = (vivaObj?.title || 'Viva_Results').replace(/[^a-zA-Z0-9_\-]/g, '_');
      link.setAttribute('download', `${titleClean}_Marks.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to download marks report.');
    } finally {
      setDownloading(false);
    }
  };

  const currentViva = vivas.find((v) => v.id === selectedVivaId);

  // Filter student summaries
  const filteredSummaries = studentSummaries.filter((s) => {
    const q = search.toLowerCase();
    const matchSearch =
      (s.student_name && s.student_name.toLowerCase().includes(q)) ||
      (s.student_email && s.student_email.toLowerCase().includes(q)) ||
      (s.student_reg_no && s.student_reg_no.toLowerCase().includes(q));

    if (!matchSearch) return false;
    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'COMPLETED') return s.status === 'COMPLETED';
    if (statusFilter === 'EXPIRED') return s.status === 'TIME_EXPIRED' || s.status === 'ABANDONED';
    if (statusFilter === 'IN_PROGRESS') return s.status === 'IN_PROGRESS';
    return true;
  });

  // Filter attempt records
  const filteredAttempts = results.filter((r) => {
    const q = search.toLowerCase();
    const matchSearch =
      (r.student_name && r.student_name.toLowerCase().includes(q)) ||
      (r.student_email && r.student_email.toLowerCase().includes(q)) ||
      (r.student_reg_no && r.student_reg_no.toLowerCase().includes(q));

    if (!matchSearch) return false;
    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'COMPLETED') return r.status === 'COMPLETED';
    if (statusFilter === 'EXPIRED') return r.status === 'TIME_EXPIRED' || r.status === 'ABANDONED';
    if (statusFilter === 'IN_PROGRESS') return r.status === 'IN_PROGRESS';
    return true;
  });

  if (loading) return <LoadingState message="Loading student marks and viva assessments..." />;

  return (
    <div className="space-y-6">
      {/* Header & Viva Selector */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            Student Viva Results
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Kalasalingam Academy of Research and Education • Evaluated Marks &amp; Transcripts
          </p>
        </div>

        {/* Action Controls: Viva Dropdown + Download Marks */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {vivas.length > 0 && (
            <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-slate-300 shadow-xs">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Viva:</span>
              <select
                value={selectedVivaId || ''}
                onChange={(e) => handleVivaChange(Number(e.target.value))}
                className="bg-transparent text-xs font-bold text-slate-800 focus:outline-hidden cursor-pointer max-w-[240px] truncate"
              >
                {vivas.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          <Button
            variant="primary"
            size="sm"
            icon={Download}
            loading={downloading}
            disabled={results.length === 0 || !selectedVivaId}
            onClick={handleDownloadMarks}
            className="shrink-0"
          >
            Download Marks (.xlsx)
          </Button>
        </div>
      </div>

      {/* Summary Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <Card className="p-3 sm:p-4 border-l-4 border-l-blue-600">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Attended Students
          </p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-slate-900">
              {stats?.total_attended_students ?? studentSummaries.length}
            </span>
            <span className="text-xs text-slate-400">students</span>
          </div>
        </Card>

        <Card className="p-3 sm:p-4 border-l-4 border-l-emerald-600">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Evaluated Completed
          </p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-emerald-700">
              {stats?.total_completed_students ?? studentSummaries.filter((s) => s.status === 'COMPLETED').length}
            </span>
            <span className="text-xs text-emerald-600 font-medium">passed grading</span>
          </div>
        </Card>

        <Card className="p-3 sm:p-4 border-l-4 border-l-indigo-600">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Average Score
          </p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-indigo-900 font-mono">
              {stats?.average_score ? `${stats.average_score} / 20` : '-'}
            </span>
          </div>
        </Card>

        <Card className="p-3 sm:p-4 border-l-4 border-l-amber-500">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Highest Score
          </p>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-amber-700 font-mono">
              {stats?.highest_score ? `${stats.highest_score} / 20` : '-'}
            </span>
          </div>
        </Card>
      </div>

      {/* Selected Viva Info Banner */}
      {currentViva && (
        <div className="flex items-center gap-3 p-3 bg-blue-50/70 border border-blue-200 rounded-xl text-xs text-blue-900">
          <Award className="w-4 h-4 text-blue-600 shrink-0" />
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span>
              <strong>Assessment:</strong> {currentViva.title}
            </span>
            <span>•</span>
            <span>
              <strong>Question Bank:</strong> {currentViva.question_count} Questions
            </span>
            <span>•</span>
            <span>
              <strong>Grading Policy:</strong> Best 2 of 3 (Maximum 20.0 Marks)
            </span>
            <span>•</span>
            <span>
              <strong>Total Historical Sessions:</strong> {results.length} attempts
            </span>
          </div>
        </div>
      )}

      {/* Controls Bar: Tab Switching + Search + Status Filter */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 shadow-xs">
        {/* View Tabs */}
        <div className="flex items-center bg-slate-100 p-1 rounded-lg shrink-0">
          <button
            type="button"
            onClick={() => setViewTab('summaries')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
              viewTab === 'summaries'
                ? 'bg-white text-blue-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Award className="w-3.5 h-3.5" />
            Evaluated Student Marks ({studentSummaries.length})
          </button>
          <button
            type="button"
            onClick={() => setViewTab('attempts')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
              viewTab === 'attempts'
                ? 'bg-white text-blue-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            All Attempt Records ({results.length})
          </button>
        </div>

        {/* Search & Filter */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed Only</option>
            <option value="EXPIRED">Expired / Abandoned</option>
            <option value="IN_PROGRESS">In Progress</option>
          </select>

          {/* Search Input */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search student, reg no..."
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            />
          </div>
        </div>
      </div>

      {/* Main Results Table */}
      {viewTab === 'summaries' ? (
        filteredSummaries.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No Student Results Found"
            description={
              search
                ? `No student records match "${search}".`
                : currentViva
                ? `No evaluated student submissions for ${currentViva.title} yet.`
                : 'Please select a viva assessment.'
            }
          />
        ) : (
          <Card className="overflow-x-auto shadow-sm">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Student Name</th>
                  <th className="py-3 px-4">Register No.</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-center">Q1 (/10)</th>
                  <th className="py-3 px-4 text-center">Q2 (/10)</th>
                  <th className="py-3 px-4 text-center">Q3 (/10)</th>
                  <th className="py-3 px-4 text-center font-bold text-blue-900">Final Mark (Best 2/20)</th>
                  <th className="py-3 px-4 text-center">Attempts</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredSummaries.map((s) => (
                  <tr key={s.student_id} className="hover:bg-blue-50/40 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-slate-900">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-xs shrink-0">
                          {s.student_name ? s.student_name.charAt(0).toUpperCase() : 'S'}
                        </div>
                        <div>
                          <div className="text-slate-900 font-bold">{s.student_name}</div>
                          <div className="text-[11px] text-slate-400 font-normal">{s.student_email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-blue-900">
                      {s.student_reg_no || '9921004123'}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge
                        variant={
                          s.status === 'COMPLETED'
                            ? 'success'
                            : s.status === 'TERMINATED_FOR_VIOLATION'
                            ? 'danger'
                            : s.status === 'TIME_EXPIRED'
                            ? 'warning'
                            : 'default'
                        }
                      >
                        {s.status === 'TERMINATED_FOR_VIOLATION'
                          ? 'Terminated'
                          : s.status === 'TIME_EXPIRED'
                          ? 'Time Expired'
                          : s.status}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-medium">
                      {s.q1_score !== null ? `${s.q1_score}` : '-'}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-medium">
                      {s.q2_score !== null ? `${s.q2_score}` : '-'}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-medium">
                      {s.q3_score !== null ? `${s.q3_score}` : '-'}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      {s.final_score !== null ? (
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold font-mono bg-emerald-100 text-emerald-800 border border-emerald-300">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          {s.final_score} / 20
                        </span>
                      ) : (
                        <span className="text-slate-400 font-mono">-</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center text-slate-500 font-mono">
                      {s.total_attempts}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={Eye}
                        onClick={() => setSelectedStudent(s)}
                      >
                        View Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      ) : (
        /* Historical Attempt Records Tab */
        filteredAttempts.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No Attempt Records Found"
            description="No viva attempts match the current search or status filter."
          />
        ) : (
          <Card className="overflow-x-auto shadow-sm">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Session</th>
                  <th className="py-3 px-4">Student Name</th>
                  <th className="py-3 px-4">Register No.</th>
                  <th className="py-3 px-4">Viva Date / Started</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-center">Q1</th>
                  <th className="py-3 px-4 text-center">Q2</th>
                  <th className="py-3 px-4 text-center">Q3</th>
                  <th className="py-3 px-4 text-center">Best 2/20</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAttempts.map((r) => (
                  <tr key={r.session_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-700">
                      #{r.session_id}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      <div>{r.student_name}</div>
                      <div className="text-[11px] text-slate-400 font-normal">{r.student_email}</div>
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-blue-900">
                      {r.student_reg_no || '9921004123'}
                    </td>
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {r.started_at ? new Date(r.started_at).toLocaleString() : '-'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge
                        variant={
                          r.status === 'COMPLETED'
                            ? 'success'
                            : r.status === 'TERMINATED_FOR_VIOLATION'
                            ? 'danger'
                            : r.status === 'TIME_EXPIRED'
                            ? 'warning'
                            : 'default'
                        }
                      >
                        {r.status === 'TERMINATED_FOR_VIOLATION'
                          ? 'Terminated'
                          : r.status === 'TIME_EXPIRED'
                          ? 'Time Expired'
                          : r.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-center font-mono">{r.q1_score ?? '-'}</td>
                    <td className="py-3 px-4 text-center font-mono">{r.q2_score ?? '-'}</td>
                    <td className="py-3 px-4 text-center font-mono">{r.q3_score ?? '-'}</td>
                    <td className="py-3 px-4 text-center font-bold text-blue-900 font-mono text-sm">
                      {r.final_score !== null ? `${r.final_score} / 20` : '-'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={Eye}
                        onClick={() => setSelectedStudent(r)}
                      >
                        View Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      )}

      {/* Student Transcript Details Modal */}
      <Modal
        isOpen={!!selectedStudent}
        onClose={() => setSelectedStudent(null)}
        title={`Viva Answers & AI Evaluations: ${selectedStudent?.student_name}`}
        maxWidth="max-w-3xl"
      >
        {selectedStudent && (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
            <div className="p-3.5 bg-blue-50 rounded-xl border border-blue-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
              <div>
                <span className="text-slate-600 block">Candidate:</span>
                <span className="font-bold text-blue-950 text-sm">
                  {selectedStudent.student_name}
                </span>
                <div className="text-slate-500 font-mono mt-0.5">
                  Reg: {selectedStudent.student_reg_no || '9921004123'} • {selectedStudent.student_email}
                </div>
              </div>
              <div className="text-left sm:text-right">
                <span className="text-slate-600 block">Final Evaluated Grade:</span>
                <span className="font-bold text-emerald-800 text-lg font-mono">
                  {selectedStudent.final_score !== null ? `${selectedStudent.final_score} / 20.0` : 'Not Evaluated'}
                </span>
                <div className="text-[11px] text-slate-500 font-medium">
                  Grading: Best 2 of 3 Questions
                </div>
              </div>
            </div>

            {/* Questions breakdown */}
            <div className="space-y-3">
              {(selectedStudent.questions || []).map((q, idx) => (
                <div key={idx} className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5 text-xs">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <span className="font-bold text-slate-800">Question {q.order}</span>
                    <Badge variant={q.score >= 7 ? 'success' : q.score >= 4 ? 'warning' : 'danger'}>
                      Score: {q.score !== null ? `${q.score} / 10` : '0 / 10'}
                    </Badge>
                  </div>

                  <p className="font-semibold text-slate-900 leading-snug">{q.question_text}</p>

                  {q.reference_answer && (
                    <div className="p-2 bg-blue-50/50 rounded border border-blue-100 text-blue-900 text-[11px]">
                      <span className="font-bold block uppercase text-[10px] text-blue-600 tracking-wider">
                        PDF Syllabus Reference:
                      </span>
                      {q.reference_answer}
                    </div>
                  )}

                  <div className="p-2.5 bg-white rounded border border-slate-200 text-slate-700">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase block mb-1">
                      Student Speech Transcript:
                    </span>
                    <p className="font-mono text-slate-800 leading-relaxed">
                      {q.transcript || 'No speech transcript submitted.'}
                    </p>
                  </div>

                  {q.reason && (
                    <div className="text-slate-700 italic bg-slate-100 p-2.5 rounded border border-slate-200">
                      <strong className="text-slate-900 not-italic">AI Marking Justification:</strong> {q.reason}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => setSelectedStudent(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default FacultyResultsPage;
