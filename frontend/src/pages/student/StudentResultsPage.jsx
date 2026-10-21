import React, { useState, useEffect } from 'react';
import { studentService } from '../../services/api';
import { Card, Badge, LoadingState, EmptyState } from '../../components/UI';
import { Award, Calendar, CheckCircle2, ChevronDown, ChevronUp, FileText } from 'lucide-react';

export const StudentResultsPage = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedReviews, setExpandedReviews] = useState({});

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const res = await studentService.getMyResults();
        const data = res.data.results || [];
        setResults(data);
        if (data.length > 0) {
          setExpandedReviews({ [data[0].id]: true });
        }
      } catch (err) {
        console.error('Failed to load results:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
  }, []);

  const toggleReview = (id) => {
    setExpandedReviews((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  if (loading) return <LoadingState message="Loading your viva assessment grades..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
          My Viva Assessment Results
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Kalasalingam Academy of Research and Education • Academic Grade Transcripts
        </p>
      </div>

      {results.length === 0 ? (
        <EmptyState
          icon={Award}
          title="No Completed Vivas Yet"
          description="Complete an active viva examination to view your evaluated scores and best-2-of-3 grade breakdown."
        />
      ) : (
        <div className="space-y-4">
          {results.map((r) => (
            <Card key={r.id} className="border-slate-200">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900">{r.viva_title}</h3>
                    <Badge variant={r.status === 'TERMINATED_FOR_VIOLATION' ? 'danger' : r.status === 'TIME_EXPIRED' ? 'warning' : 'success'}>
                      {r.status === 'TERMINATED_FOR_VIOLATION' ? 'Terminated (Violation)' : r.status === 'TIME_EXPIRED' ? 'Time Expired' : 'Completed'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Finalized: {r.finalized_at ? new Date(r.finalized_at).toLocaleDateString() : 'Recent'}</span>
                  </div>
                </div>

                <div className="text-right sm:border-l sm:border-slate-100 sm:pl-6">
                  <span className="text-xs text-slate-500 block uppercase font-semibold tracking-wider">
                    Official Final Score
                  </span>
                  <div className="text-3xl font-extrabold text-blue-900 font-mono">
                    {r.final_score} <span className="text-base text-slate-400 font-normal">/ 20</span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    Calculated from Best 2 Questions
                  </span>
                </div>
              </div>

              {/* Question Breakdown Row */}
              <div className="mt-4 grid grid-cols-3 gap-3">
                <div className={`p-3 rounded-lg border text-center ${r.counted_question_1 === 1 || r.counted_question_2 === 1 ? 'bg-blue-50/70 border-blue-200 font-semibold text-blue-900' : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
                  <span className="text-xs block">Question 1</span>
                  <span className="text-lg font-mono block mt-1">{r.q1_score} / 10</span>
                  {(r.counted_question_1 === 1 || r.counted_question_2 === 1) && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-bold mt-1">
                      <CheckCircle2 className="w-3 h-3" /> Best 2 Counted
                    </span>
                  )}
                </div>

                <div className={`p-3 rounded-lg border text-center ${r.counted_question_1 === 2 || r.counted_question_2 === 2 ? 'bg-blue-50/70 border-blue-200 font-semibold text-blue-900' : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
                  <span className="text-xs block">Question 2</span>
                  <span className="text-lg font-mono block mt-1">{r.q2_score} / 10</span>
                  {(r.counted_question_1 === 2 || r.counted_question_2 === 2) && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-bold mt-1">
                      <CheckCircle2 className="w-3 h-3" /> Best 2 Counted
                    </span>
                  )}
                </div>

                <div className={`p-3 rounded-lg border text-center ${r.counted_question_1 === 3 || r.counted_question_2 === 3 ? 'bg-blue-50/70 border-blue-200 font-semibold text-blue-900' : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
                  <span className="text-xs block">Question 3</span>
                  <span className="text-lg font-mono block mt-1">{r.q3_score} / 10</span>
                  {(r.counted_question_1 === 3 || r.counted_question_2 === 3) && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-bold mt-1">
                      <CheckCircle2 className="w-3 h-3" /> Best 2 Counted
                    </span>
                  )}
                </div>
              </div>

              {/* Post-Exam Question-by-Question Review */}
              {r.questions_review && r.questions_review.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => toggleReview(r.id)}
                    className="w-full flex items-center justify-between p-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-600" />
                      Detailed Post-Exam Review & Model Answers ({r.questions_review.length} Questions)
                    </span>
                    {expandedReviews[r.id] ? (
                      <ChevronUp className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                  </button>

                  {expandedReviews[r.id] && (
                    <div className="mt-3 space-y-3">
                      {r.questions_review.map((q) => (
                        <div
                          key={q.question_order}
                          className="p-4 rounded-xl border border-slate-200 bg-white space-y-3 shadow-sm text-left"
                        >
                          {/* Question Header & Score */}
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                            <div className="space-y-0.5">
                              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                                Question {q.question_order}
                              </span>
                              <h4 className="text-sm font-semibold text-slate-900 leading-snug">
                                {q.question_text}
                              </h4>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {q.is_counted && (
                                <Badge variant="success" className="text-[10px]">
                                  Counted in Final Score
                                </Badge>
                              )}
                              <span className="text-sm font-bold font-mono text-blue-900 px-2.5 py-1 bg-blue-50 border border-blue-200 rounded-lg">
                                {q.score} / {q.max_score || 10.0}
                              </span>
                            </div>
                          </div>

                          {/* Student's Actual Answer */}
                          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                              Your Spoken / Submitted Answer:
                            </span>
                            <p className="text-xs text-slate-800 italic leading-relaxed whitespace-pre-wrap">
                              "{q.student_answer || 'No answer recorded.'}"
                            </p>
                          </div>

                          {/* Reason for Scoring */}
                          <div className="p-3 bg-blue-50/50 rounded-lg border border-blue-100">
                            <span className="text-[11px] font-bold text-blue-900 uppercase tracking-wider block mb-1">
                              Evaluator Feedback & Scoring Reason:
                            </span>
                            <p className="text-xs text-blue-950 leading-relaxed">
                              {q.reason || 'Graded against academic rubric.'}
                            </p>
                          </div>

                          {/* Suggested Full-Mark Answer */}
                          {q.improved_answer && (
                            <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-200">
                              <span className="text-[11px] font-bold text-emerald-900 uppercase tracking-wider block mb-1">
                                Suggested Full-Mark Answer (Reference):
                              </span>
                              <p className="text-xs text-emerald-950 leading-relaxed whitespace-pre-wrap">
                                {q.improved_answer}
                              </p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentResultsPage;
