import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button, Card, Badge } from '../components/UI';
import {
  GraduationCap,
  BookOpen,
  ShieldCheck,
  Award,
  CheckCircle,
  Mic,
  ArrowRight,
  FileCheck2,
  Sparkles,
} from 'lucide-react';

export const HomePage = () => {
  const { user, isAuthenticated, isStudent, isFaculty, isAdmin } = useAuth();

  const getDashboardLink = () => {
    if (isAdmin) return '/admin/dashboard';
    if (isFaculty) return '/faculty/dashboard';
    return '/student/dashboard';
  };

  return (
    <div className="space-y-12 py-4">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-blue-900 via-indigo-950 to-slate-900 rounded-3xl p-8 sm:p-14 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-white/10 backdrop-blur-md text-blue-200 border border-white/20">
            <Sparkles className="w-4 h-4 text-amber-300" />
            Accredited by NAAC with &quot;A++&quot; Grade • Deemed to be University
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight leading-tight">
            KARE Viva Evaluation System
          </h1>

          <p className="text-base sm:text-lg text-slate-200 leading-relaxed max-w-2xl">
            A next-generation oral examination platform for{' '}
            <strong className="text-white">Kalasalingam Academy of Research and Education</strong>.
            Strictly powered by faculty-uploaded syllabus PDFs, speech recognition voice input, and
            transparent Best-2-of-3 grading.
          </p>

          <div className="flex flex-wrap items-center gap-4 pt-2">
            {isAuthenticated ? (
              <Link to={getDashboardLink()}>
                <Button variant="primary" size="lg" icon={ArrowRight}>
                  Open {user?.role} Portal
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="primary" size="lg" icon={GraduationCap}>
                    Student &amp; Faculty Login
                  </Button>
                </Link>
                <Link to="/register">
                  <Button variant="outline" size="lg" className="border-white text-white hover:bg-white/10">
                    Create Account
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Core Architectural Pillars */}
      <div>
        <div className="text-center max-w-xl mx-auto space-y-2 mb-8">
          <h2 className="text-2xl font-bold text-slate-900">
            Core Academic Principles
          </h2>
          <p className="text-xs sm:text-sm text-slate-500">
            Built with strict integrity, evidence-based AI grading, and institutional accountability.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="hover:shadow-md transition-shadow border-t-4 border-t-blue-600">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                <FileCheck2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">100% PDF Ground Truth</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Faculty-uploaded PDFs are the <strong>ONLY</strong> source of viva questions.
                The system strictly forbids LLM question generation, paraphrasing, or hallucination.
              </p>
            </div>
          </Card>

          <Card className="hover:shadow-md transition-shadow border-t-4 border-t-emerald-600">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Mic className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Speech Recognition + Editable Speech</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Students respond verbally into their microphone. High-fidelity speech recognition generates transcripts,
                which students can review and edit before final AI evaluation.
              </p>
            </div>
          </Card>

          <Card className="hover:shadow-md transition-shadow border-t-4 border-t-amber-500">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                <Award className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Best 2 of 3 Scoring (Max 20)</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Students answer 3 questions (10 marks each). The backend automatically selects the{' '}
                <strong>best 2 scores</strong> for the final grade (maximum 20 marks).
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
