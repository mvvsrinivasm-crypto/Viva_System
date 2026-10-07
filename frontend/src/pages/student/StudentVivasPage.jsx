import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { studentService } from '../../services/api';
import { Card, Button, Badge, LoadingState, EmptyState } from '../../components/UI';
import { BookOpen, CheckCircle, Play, ShieldAlert, Award, Info } from 'lucide-react';

export const StudentVivasPage = () => {
  const navigate = useNavigate();
  const [vivas, setVivas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVivas = async () => {
      try {
        const res = await studentService.getVivas();
        setVivas(res.data.vivas || []);
      } catch (err) {
        console.error('Failed to load vivas:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchVivas();
  }, []);

  if (loading) return <LoadingState message="Fetching available viva assessments..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
          Available Viva Examinations
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Kalasalingam Academy of Research and Education • Oral Assessment Portal
        </p>
      </div>

      {/* Rules Notice Card */}
      <Card className="bg-blue-50/60 border-blue-200">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 mt-0.5 shrink-0" />
          <div className="space-y-1 text-xs text-blue-900">
            <h4 className="font-bold text-blue-950 text-sm">Viva Assessment Instructions &amp; Scoring Policy:</h4>
            <ul className="list-disc list-inside space-y-0.5 text-blue-800">
              <li>
                <strong>Question Source:</strong> Exactly 3 questions selected strictly from the faculty PDF question bank.
              </li>
              <li>
                <strong>Oral Answering:</strong> Record your speech verbally. Speech recognition transcribes your audio into text.
              </li>
              <li>
                <strong>Transcript Review:</strong> You can edit the speech transcript before final AI grading.
              </li>
              <li>
                <strong>Best-2-of-3 Scoring:</strong> Each question carries 10 marks. Your final viva score is computed using your{' '}
                <strong>BEST 2 QUESTIONS</strong> (Maximum 20 marks).
              </li>
              <li>
                <strong>Total Session Timer:</strong> The countdown timer applies to your entire session across all 3 questions and does not reset between questions.
              </li>
              <li>
                <strong>Anti-Cheating Environment:</strong> Fullscreen mode is enforced. Tab switches, window unfocus, and copy/paste actions are logged.
              </li>
            </ul>
          </div>
        </div>
      </Card>

      {/* Vivas Grid */}
      {vivas.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No Published Vivas Available"
          description="Check back later or contact your course faculty."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {vivas.map((viva) => (
            <Card key={viva.id} className="flex flex-col justify-between hover:shadow-md transition-shadow">
              <div className="space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-base font-bold text-slate-800 line-clamp-2">
                    {viva.title}
                  </h3>
                  {viva.session_status === 'COMPLETED' ? (
                    <Badge variant="success">Completed</Badge>
                  ) : viva.session_status === 'IN_PROGRESS' ? (
                    <Badge variant="warning">In Progress</Badge>
                  ) : (
                    <Badge variant="primary">Available</Badge>
                  )}
                </div>

                <p className="text-xs text-slate-600 line-clamp-3">
                  {viva.description || 'No detailed instructions provided.'}
                </p>

                <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs text-slate-500 gap-2">
                  <span>Faculty: <strong>{viva.faculty_name || 'Faculty'}</strong></span>
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                      ⏱ {viva.duration_minutes || Math.round((viva.duration_seconds || 120) / 60)} min session
                    </span>
                    <span className="font-mono text-slate-600">3 Questions • Max 20</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                {viva.session_status === 'COMPLETED' ? (
                  <>
                    <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold">
                      <Award className="w-4 h-4 text-emerald-600" />
                      <span>Final Score: {viva.final_score} / 20</span>
                    </div>
                    <Link to="/student/results">
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    </Link>
                  </>
                ) : (
                  <>
                    <span className="text-[11px] text-slate-500 flex items-center gap-1">
                      <ShieldAlert className="w-3.5 h-3.5 text-slate-400" /> Monitored Session
                    </span>
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
                          // Continue to viva page gate
                        }
                        navigate(`/student/viva/${viva.id}`);
                      }}
                    >
                      {viva.session_status === 'IN_PROGRESS' ? 'Resume Session' : 'Start Assessment'}
                    </Button>
                  </>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentVivasPage;
