import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { facultyService } from '../../services/api';
import { Card, Button, Badge, LoadingState, EmptyState } from '../../components/UI';
import { ArrowLeft, BookOpen, CheckCircle, ShieldCheck, FileText } from 'lucide-react';

export const FacultyQuestionsReview = () => {
  const { id: vivaId } = useParams();
  const [viva, setViva] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [vivaRes, qRes] = await Promise.all([
          facultyService.getViva(vivaId),
          facultyService.getQuestions(vivaId),
        ]);
        setViva(vivaRes.data.viva);
        setQuestions(qRes.data.questions || []);
      } catch (err) {
        console.error('Failed to load questions:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [vivaId]);

  if (loading) return <LoadingState message="Loading extracted question bank..." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/faculty/vivas">
          <Button variant="secondary" size="sm" icon={ArrowLeft}>
            Back to Vivas
          </Button>
        </Link>
        <div>
          <h1 className="text-xl font-bold text-slate-900">
            {viva?.title} — Question Bank Review
          </h1>
          <p className="text-xs text-slate-500">
            Extracted strictly from uploaded PDF document
          </p>
        </div>
      </div>

      {/* Institutional Compliance Notice */}
      <Card className="bg-emerald-50/70 border-emerald-200">
        <div className="flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs text-emerald-900 space-y-1">
            <h4 className="font-bold text-emerald-950">Grounded Syllabus Question Bank</h4>
            <p>
              All questions below were extracted directly from the faculty-uploaded PDF using PyMuPDF.
              The system strictly enforces that no viva questions are generated, paraphrased, or modified by an LLM.
            </p>
          </div>
        </div>
      </Card>

      {questions.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No Questions Extracted"
          description="Upload a PDF file to extract question-answer pairs for this viva."
        />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>Total Valid Questions: <strong>{questions.length}</strong></span>
            <span>Selection: <strong>Exactly 3 questions selected per student viva session</strong></span>
          </div>

          {questions.map((q, idx) => (
            <Card key={q.id} className="border-slate-200">
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    Question #{q.question_number || idx + 1}
                  </span>
                  <Badge variant="success">Validated from PDF</Badge>
                </div>

                <h3 className="text-sm sm:text-base font-semibold text-slate-900">
                  {q.question_text}
                </h3>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                  <span className="font-semibold text-slate-700 block uppercase tracking-wider text-[11px]">
                    Official Reference Answer (PDF Ground Truth):
                  </span>
                  <p className="text-slate-600 leading-relaxed font-mono">
                    {q.reference_answer}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default FacultyQuestionsReview;
