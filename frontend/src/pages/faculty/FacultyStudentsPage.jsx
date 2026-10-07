import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { facultyService } from '../../services/api';
import { Card, Badge, Button, Modal, LoadingState, EmptyState } from '../../components/UI';
import {
  Users,
  Search,
  Building2,
  Eye,
  Award,
  CheckCircle2,
  ExternalLink,
  BookOpen,
} from 'lucide-react';

export const FacultyStudentsPage = () => {
  const [students, setStudents] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedStudent, setSelectedStudent] = useState(null);

  useEffect(() => {
    const fetchStudents = async () => {
      try {
        const res = await facultyService.getStudentsDirectory();
        setStudents(res.data.students || []);
      } catch (err) {
        console.error('Failed to load students directory:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStudents();
  }, []);

  const filtered = students.filter((s) => {
    const q = search.toLowerCase();
    return (
      (s.name && s.name.toLowerCase().includes(q)) ||
      (s.email && s.email.toLowerCase().includes(q)) ||
      (s.registration_number && s.registration_number.toLowerCase().includes(q)) ||
      (s.department && s.department.toLowerCase().includes(q))
    );
  });

  if (loading) return <LoadingState message="Loading university student directory and marks..." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            Student Directory &amp; Evaluated Marks
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Kalasalingam Academy of Research and Education • Enrolled Students &amp; Viva Assessment Scores
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Users className="w-3.5 h-3.5" />
            {students.length} Registered Students
          </span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by student name, register no, email..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          />
        </div>
      </div>

      {/* Students Table */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No Students Found"
          description="No registered students match your current search query."
        />
      ) : (
        <Card className="overflow-x-auto shadow-sm">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider">
                <th className="py-3.5 px-4">Student Name</th>
                <th className="py-3.5 px-4">Register Number</th>
                <th className="py-3.5 px-4">Institutional Email</th>
                <th className="py-3.5 px-4">Department</th>
                <th className="py-3.5 px-4">Viva Assessments &amp; Marks</th>
                <th className="py-3.5 px-4 text-center">Completed Vivas</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((s) => {
                const completedVivas = (s.vivas || []).filter(
                  (v) => v.status === 'COMPLETED' && v.final_score !== null
                );

                return (
                  <tr key={s.id} className="hover:bg-blue-50/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-xs shrink-0">
                          {s.name ? s.name.charAt(0).toUpperCase() : 'S'}
                        </div>
                        <span className="font-semibold text-slate-900">{s.name}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-blue-900">
                      {s.registration_number || 'N/A'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 font-mono">
                      {s.email}
                    </td>
                    <td className="py-3.5 px-4 text-slate-700">
                      <span className="inline-flex items-center gap-1 text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                        <Building2 className="w-3 h-3 text-slate-400" />
                        {s.department || 'School of Computing'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {completedVivas.length > 0 ? (
                        <div className="flex flex-wrap items-center gap-1.5">
                          {completedVivas.map((v, vIdx) => (
                            <span
                              key={vIdx}
                              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold font-mono bg-emerald-50 text-emerald-800 border border-emerald-300"
                              title={`${v.viva_title}: ${v.final_score} / 20.0`}
                            >
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              {v.viva_title.length > 22
                                ? `${v.viva_title.slice(0, 20)}...`
                                : v.viva_title}
                              : <strong className="text-emerald-900">{v.final_score} / 20</strong>
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-400 italic text-[11px]">
                          No completed viva records
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <Badge variant={s.completed_vivas_count > 0 ? 'success' : 'default'}>
                        {s.completed_vivas_count || 0} Vivas
                      </Badge>
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
                );
              })}
            </tbody>
          </table>
        </Card>
      )}

      {/* Student Viva Details Modal */}
      <Modal
        isOpen={!!selectedStudent}
        onClose={() => setSelectedStudent(null)}
        title={`Student Details & Evaluated Marks: ${selectedStudent?.name}`}
        maxWidth="max-w-3xl"
      >
        {selectedStudent && (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
            {/* Student Profile Card */}
            <div className="p-3.5 bg-blue-50 rounded-xl border border-blue-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
              <div>
                <span className="text-slate-600 block">Student Profile:</span>
                <span className="font-bold text-blue-950 text-sm">
                  {selectedStudent.name}
                </span>
                <div className="text-slate-600 font-mono mt-0.5">
                  Reg No: <strong>{selectedStudent.registration_number}</strong> • {selectedStudent.email}
                </div>
                <div className="text-slate-500 mt-0.5">
                  Department: {selectedStudent.department}
                </div>
              </div>
              <div className="text-left sm:text-right">
                <span className="text-slate-600 block">Assessments Completed:</span>
                <span className="font-bold text-blue-900 text-base font-mono">
                  {selectedStudent.completed_vivas_count || 0} Assessments
                </span>
              </div>
            </div>

            {/* Viva Assessment History */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-blue-600" />
                Attended Viva Examinations
              </h3>

              {(!selectedStudent.vivas || selectedStudent.vivas.length === 0) ? (
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-center text-slate-500 text-xs">
                  This student has not yet attended any oral viva evaluations for your courses.
                </div>
              ) : (
                selectedStudent.vivas.map((v, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-3 text-xs"
                  >
                    {/* Viva Header */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-2 border-b border-slate-100 gap-2">
                      <div>
                        <span className="font-bold text-slate-900 text-sm block">
                          {v.viva_title}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          {v.completed_at ? `Completed: ${new Date(v.completed_at).toLocaleString()}` : 'Date: -'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            v.status === 'COMPLETED'
                              ? 'success'
                              : v.status === 'TIME_EXPIRED'
                              ? 'warning'
                              : 'default'
                          }
                        >
                          {v.status}
                        </Badge>
                        <span className="text-sm font-bold font-mono text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-300">
                          {v.final_score !== null ? `${v.final_score} / 20.0` : '-'}
                        </span>
                        <Link to={`/faculty/vivas/${v.viva_id}/results`}>
                          <Button variant="ghost" size="sm" icon={ExternalLink}>
                            Results Sheet
                          </Button>
                        </Link>
                      </div>
                    </div>

                    {/* Question breakdown */}
                    {v.questions && v.questions.length > 0 && (
                      <div className="space-y-2.5 pt-1">
                        <span className="text-[11px] font-semibold text-slate-500 uppercase block">
                          Question Evaluations &amp; Spoken Speech:
                        </span>
                        {v.questions.map((q, qIdx) => (
                          <div
                            key={qIdx}
                            className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-800">
                                Question {q.order}
                              </span>
                              <Badge variant={q.score >= 7 ? 'success' : q.score >= 4 ? 'warning' : 'danger'}>
                                {q.score !== null ? `${q.score} / 10` : '0 / 10'}
                              </Badge>
                            </div>
                            <p className="font-semibold text-slate-900">{q.question_text}</p>
                            <div className="p-2 bg-white rounded border border-slate-200 text-slate-700 font-mono text-[11px]">
                              <span className="text-[10px] text-slate-400 font-sans uppercase block mb-0.5">
                                Spoken Answer:
                              </span>
                              {q.transcript || 'No transcript recorded.'}
                            </div>
                            {q.reason && (
                              <div className="text-slate-600 italic bg-slate-100 p-2 rounded text-[11px]">
                                <strong>AI Feedback:</strong> {q.reason}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
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

export default FacultyStudentsPage;
