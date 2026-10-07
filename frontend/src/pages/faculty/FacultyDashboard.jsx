import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { facultyService } from '../../services/api';
import { Card, Button, Badge, LoadingState, EmptyState } from '../../components/UI';
import {
  BookOpen,
  PlusCircle,
  FileCheck,
  Users,
  CheckCircle,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

export const FacultyDashboard = () => {
  const { user } = useAuth();
  const [vivas, setVivas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVivas = async () => {
      try {
        const res = await facultyService.getVivas();
        setVivas(res.data.vivas || []);
      } catch (err) {
        console.error('Failed to load faculty vivas:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchVivas();
  }, []);

  if (loading) return <LoadingState message="Loading faculty portal overview..." />;

  const publishedCount = vivas.filter((v) => v.status === 'PUBLISHED' || v.status === 'ACTIVE').length;

  return (
    <div className="space-y-6">
      {/* Faculty Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-900 rounded-2xl p-6 sm:p-8 text-white shadow-md relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 backdrop-blur-xs text-blue-200 border border-white/20 mb-3">
            <Sparkles className="w-3.5 h-3.5" /> Department Faculty Portal
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Welcome, {user?.name}!
          </h1>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Manage your course oral assessments. Upload syllabus PDFs to extract question banks,
            review student answer transcripts, and view evaluated marks.
          </p>
          <div className="mt-4 flex gap-3">
            <Link to="/faculty/vivas">
              <Button variant="primary" size="sm" icon={PlusCircle}>
                Manage Question Banks &amp; Upload PDF
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-blue-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Question Banks
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
                Published &amp; Active Vivas
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">{publishedCount}</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <FileCheck className="w-5 h-5" />
            </div>
          </div>
        </Card>

        <Card className="border-l-4 border-l-indigo-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Assessment System
              </p>
              <h3 className="text-2xl font-bold text-slate-800 mt-1">Best-2 of 3</h3>
            </div>
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
          </div>
        </Card>
      </div>

      {/* Vivas Management Table */}
      <Card
        title="My Viva Question Banks"
        subtitle="Upload syllabus PDF documents and publish validated viva assessments"
        action={
          <Link to="/faculty/vivas" className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
            Manage All <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        }
      >
        {vivas.length === 0 ? (
          <EmptyState
            title="No Vivas Created Yet"
            description="Create a viva and upload a PDF containing questions and reference answers."
            action={
              <Link to="/faculty/vivas">
                <Button variant="primary" size="sm" icon={PlusCircle}>
                  Create First Viva
                </Button>
              </Link>
            }
          />
        ) : (
          <div className="divide-y divide-slate-100">
            {vivas.map((v) => (
              <div key={v.id} className="py-4 first:pt-0 last:pb-0 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-slate-900">{v.title}</h4>
                    <Badge variant={v.status === 'PUBLISHED' || v.status === 'ACTIVE' ? 'success' : 'warning'}>
                      {v.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 line-clamp-1">{v.description}</p>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Questions Stored: {v.question_count} • Created: {new Date(v.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  <Link to={`/faculty/vivas/${v.id}/questions`}>
                    <Button variant="secondary" size="sm">
                      Review Questions
                    </Button>
                  </Link>
                  <Link to={`/faculty/vivas/${v.id}/results`}>
                    <Button variant="outline" size="sm">
                      Student Marks
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};

export default FacultyDashboard;
