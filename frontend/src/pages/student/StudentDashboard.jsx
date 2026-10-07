import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { studentService } from '../../services/api';
import { Card, Button, Badge, LoadingState, EmptyState } from '../../components/UI';
import {
  GraduationCap,
  Award,
  CheckCircle,
  Play,
  ArrowRight,
  Sparkles,
  BookOpen,
} from 'lucide-react';

export const StudentDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [vivas, setVivas] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [vivasRes, resultsRes] = await Promise.all([
          studentService.getVivas(),
          studentService.getMyResults(),
        ]);
        setVivas(vivasRes.data.vivas || []);
        setResults(resultsRes.data.results || []);
      } catch (err) {
        console.error('Failed to fetch student dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <LoadingState message="Loading your academic viva dashboard..." />;

  const completedCount = results.length;
  const avgScore =
    completedCount > 0
      ? (results.reduce((acc, r) => acc + (r.final_score || 0), 0) / completedCount).toFixed(1)
      : '0.0';

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-blue-900 rounded-2xl p-6 sm:p-8 text-white shadow-md relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/20 backdrop-blur-xs text-blue-100 border border-white/20 mb-3">
            <Sparkles className="w-3.5 h-3.5" /> Kalasalingam University Viva Portal
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Welcome, {user?.name}!
          </h1>
          <p className="mt-2 text-sm text-blue-100 leading-relaxed">
            Prepare for your oral assessment. Answer 3 syllabus-extracted questions with speech recognition
            voice input. Your final grade is calculated using your{' '}
            <strong className="text-white underline decoration-amber-400">BEST 2 of 3 questions</strong>{' '}
            (maximum 20 marks).
          </p>
          <div className="mt-4 flex gap-3">
            <Link to="/student/vivas">
              <Button variant="secondary" size="sm" className="bg-white text-blue-900 hover:bg-blue-50 font-semibold border-none">
                View Available Vivas
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-blue-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Available Assessments
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{vivas.length}</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <BookOpen className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card className="border-l-4 border-l-emerald-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Completed Vivas
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{completedCount}</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Average Mark (Out of 20)
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{avgScore} / 20</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Award className="w-5 h-5" />
            </div>
          </div>
        </Card>
      </div>

      {/* Active / Available Assessments */}
      <Card
        title="Active Viva Examinations"
        subtitle="Select an assessment to start or review your evaluation"
        action={
          <Link to="/student/vivas" className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
            Browse All <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        }
      >
        {vivas.length === 0 ? (
          <EmptyState
            title="No Active Vivas Found"
            description="There are currently no active viva examinations published by faculty."
          />
        ) : (
          <div className="divide-y divide-slate-100">
            {vivas.map((viva) => (
              <div key={viva.id} className="py-4 first:pt-0 last:pb-0 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-slate-800">{viva.title}</h4>
                    {viva.session_status === 'COMPLETED' ? (
                      <Badge variant="success">Completed</Badge>
                    ) : viva.session_status === 'IN_PROGRESS' ? (
                      <Badge variant="warning">In Progress</Badge>
                    ) : (
                      <Badge variant="primary">Ready to Start</Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 line-clamp-1">{viva.description}</p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Faculty: {viva.faculty_name || 'Department Faculty'} • {viva.question_count} Bank Questions (3 Selected)
                  </p>
                </div>

                <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                  {viva.session_status === 'COMPLETED' ? (
                    <div className="text-right">
                      <span className="text-xs text-slate-500 block">Final Score:</span>
                      <span className="text-sm font-bold text-emerald-700 font-mono">
                        {viva.final_score} / 20
                      </span>
                    </div>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      icon={Play}
                      onClick={async () => {
                        try {
                          if (!document.fullscreenElement) {
                            await document.documentElement.requestFullscreen();
                          }
                        } catch (e) {
                          // Continue to viva gate
                        }
                        navigate(`/student/viva/${viva.id}`);
                      }}
                    >
                      {viva.session_status === 'IN_PROGRESS' ? 'Resume Viva' : 'Enter Viva'}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default StudentDashboard;
