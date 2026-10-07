import React, { useState, useEffect } from 'react';
import { studentService } from '../../services/api';
import { Card, Badge, LoadingState, EmptyState } from '../../components/UI';
import { Award, Calendar, CheckCircle2 } from 'lucide-react';

export const StudentResultsPage = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const res = await studentService.getMyResults();
        setResults(res.data.results || []);
      } catch (err) {
        console.error('Failed to load results:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
  }, []);

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
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentResultsPage;
