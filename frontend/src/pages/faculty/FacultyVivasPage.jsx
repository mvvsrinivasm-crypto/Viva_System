import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { facultyService } from '../../services/api';
import { Card, Button, Badge, Modal, LoadingState, EmptyState } from '../../components/UI';
import {
  PlusCircle,
  Upload,
  FileText,
  AlertCircle,
  CheckCircle,
  FileCheck,
  Eye,
  Users,
  AlertTriangle,
  Clock,
} from 'lucide-react';

export const FacultyVivasPage = () => {
  const [vivas, setVivas] = useState([]);
  const [loading, setLoading] = useState(true);

  // Create Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [durationMinutes, setDurationMinutes] = useState(2);
  const [creating, setCreating] = useState(false);

  // Edit Duration Modal
  const [isDurationOpen, setIsDurationOpen] = useState(false);
  const [editingViva, setEditingViva] = useState(null);
  const [editDurationMinutes, setEditDurationMinutes] = useState(2);
  const [savingDuration, setSavingDuration] = useState(false);

  // Upload Modal
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedViva, setSelectedViva] = useState(null);
  const [pdfFile, setPdfFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  // Publish & Notification state
  const [publishingId, setPublishingId] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);

  const fetchVivas = async () => {
    try {
      const res = await facultyService.getVivas();
      setVivas(res.data.vivas || []);
    } catch (err) {
      console.error('Failed to fetch vivas:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVivas();
  }, []);

  const handleCreateViva = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    try {
      await facultyService.createViva({
        title,
        description,
        duration_minutes: Number(durationMinutes) || 2,
      });
      setIsCreateOpen(false);
      setTitle('');
      setDescription('');
      setDurationMinutes(2);
      fetchVivas();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to create viva.');
    } finally {
      setCreating(false);
    }
  };

  const handleOpenDurationModal = (viva) => {
    setEditingViva(viva);
    setEditDurationMinutes(viva.duration_minutes || Math.round((viva.duration_seconds || 120) / 60));
    setIsDurationOpen(true);
  };

  const handleSaveDuration = async (e) => {
    e.preventDefault();
    if (!editingViva) return;
    setSavingDuration(true);
    try {
      await facultyService.updateViva(editingViva.id, {
        duration_minutes: Number(editDurationMinutes) || 2,
      });
      setIsDurationOpen(false);
      fetchVivas();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to update viva duration.');
    } finally {
      setSavingDuration(false);
    }
  };

  const handleUploadPDF = async (e) => {
    e.preventDefault();
    if (!pdfFile || !selectedViva) return;

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', pdfFile);

    try {
      const res = await facultyService.uploadPDF(selectedViva.id, formData);
      setUploadResult(res.data);
      fetchVivas();
    } catch (err) {
      setUploadResult({
        validation_passed: false,
        validation_message: err.response?.data?.error || 'PDF extraction failed.',
      });
    } finally {
      setUploading(false);
    }
  };

  const handlePublish = async (vivaId) => {
    setPublishingId(vivaId);
    try {
      const res = await facultyService.publishViva(vivaId);
      setVivas((prev) =>
        prev.map((v) =>
          v.id === vivaId
            ? { ...v, status: 'PUBLISHED', published_at: new Date().toISOString() }
            : v
        )
      );
      setFeedbackMsg({
        type: 'success',
        text: 'Viva question bank successfully published and activated for students.',
      });
      setTimeout(() => setFeedbackMsg(null), 5000);
      fetchVivas();
    } catch (err) {
      setFeedbackMsg({
        type: 'error',
        text: err.response?.data?.error || 'Failed to publish viva. Requires at least 3 valid questions.',
      });
      setTimeout(() => setFeedbackMsg(null), 6000);
    } finally {
      setPublishingId(null);
    }
  };

  const handleToggleStatus = async (viva) => {
    const isCurrentlyActive = viva.status === 'ACTIVE' || viva.status === 'PUBLISHED';
    const nextStatus = isCurrentlyActive ? 'INACTIVE' : 'ACTIVE';
    try {
      await facultyService.updateStatus(viva.id, nextStatus);
      setVivas((prev) =>
        prev.map((v) => (v.id === viva.id ? { ...v, status: nextStatus } : v))
      );
      setFeedbackMsg({
        type: 'success',
        text: `Viva status updated to ${nextStatus}.`,
      });
      setTimeout(() => setFeedbackMsg(null), 4000);
      fetchVivas();
    } catch (err) {
      setFeedbackMsg({
        type: 'error',
        text: err.response?.data?.error || 'Failed to update status.',
      });
      setTimeout(() => setFeedbackMsg(null), 5000);
    }
  };

  if (loading) return <LoadingState message="Loading viva question banks..." />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            Viva Question Banks
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Faculty Syllabus PDF Upload &amp; Question Validation
          </p>
        </div>

        <Button variant="primary" icon={PlusCircle} onClick={() => setIsCreateOpen(true)}>
          Create New Viva
        </Button>
      </div>

      {feedbackMsg && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between text-xs sm:text-sm shadow-sm transition-all ${
            feedbackMsg.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          <div className="flex items-center gap-2.5">
            {feedbackMsg.type === 'success' ? (
              <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            )}
            <span className="font-semibold">{feedbackMsg.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setFeedbackMsg(null)}
            className="text-xs font-bold uppercase tracking-wider opacity-70 hover:opacity-100 underline ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {vivas.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No Viva Assessments Created"
          description="Create your first viva and upload a PDF containing question-answer pairs."
          action={
            <Button variant="primary" size="sm" icon={PlusCircle} onClick={() => setIsCreateOpen(true)}>
              Create Viva Assessment
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {vivas.map((v) => (
            <Card key={v.id} className="hover:shadow-md transition-shadow">
              <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900">{v.title}</h3>
                    <Badge variant={v.status === 'PUBLISHED' || v.status === 'ACTIVE' ? 'success' : 'warning'}>
                      {v.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-600">{v.description || 'No description provided.'}</p>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-1">
                    <span className="inline-flex items-center gap-1 font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                      <Clock className="w-3.5 h-3.5" />
                      Session Duration: {v.duration_minutes || Math.round((v.duration_seconds || 120) / 60)} mins
                    </span>
                    <span>•</span>
                    <span>
                      Valid Questions in Bank: <strong>{v.question_count}</strong>
                    </span>
                    <span>•</span>
                    <span>Created: {new Date(v.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto justify-end pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-100">
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Clock}
                    onClick={() => handleOpenDurationModal(v)}
                  >
                    Timer
                  </Button>

                  <Button
                    variant="secondary"
                    size="sm"
                    icon={Upload}
                    onClick={() => {
                      setSelectedViva(v);
                      setPdfFile(null);
                      setUploadResult(null);
                      setIsUploadOpen(true);
                    }}
                  >
                    Upload / Re-upload PDF
                  </Button>

                  <Link to={`/faculty/vivas/${v.id}/questions`}>
                    <Button variant="outline" size="sm" icon={Eye}>
                      Review Q&amp;A
                    </Button>
                  </Link>

                  {v.status === 'DRAFT' && (
                    <Button
                      variant="success"
                      size="sm"
                      icon={FileCheck}
                      onClick={() => handlePublish(v.id)}
                      disabled={v.question_count < 3 || publishingId === v.id}
                    >
                      {publishingId === v.id ? 'Publishing...' : 'Publish'}
                    </Button>
                  )}

                  {v.status !== 'DRAFT' && (
                    <Button
                      variant={v.status === 'ACTIVE' || v.status === 'PUBLISHED' ? 'ghost' : 'primary'}
                      size="sm"
                      onClick={() => handleToggleStatus(v)}
                    >
                      {v.status === 'ACTIVE' || v.status === 'PUBLISHED' ? 'Deactivate' : 'Activate'}
                    </Button>
                  )}

                  <Link to={`/faculty/vivas/${v.id}/results`}>
                    <Button variant="ghost" size="sm" icon={Users}>
                      Student Marks
                    </Button>
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create Viva Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create New Viva Assessment"
      >
        <form onSubmit={handleCreateViva} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Viva Title / Course Code
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. CS304 - Machine Learning Lab Viva 2026"
              className="w-full p-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Description / Examination Scope
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the topics covered in this viva examination..."
              className="w-full p-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Viva Duration (Total Session Time)
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
                placeholder="2"
                className="w-24 p-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
              />
              <span className="text-sm text-slate-600 font-medium">minutes</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Total examination time for all 3 questions. The timer runs continuously and does not reset between questions.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={creating}>
              Create Viva
            </Button>
          </div>
        </form>
      </Modal>

      {/* Edit Duration Modal */}
      <Modal
        isOpen={isDurationOpen}
        onClose={() => setIsDurationOpen(false)}
        title={`Configure Session Timer: ${editingViva?.title}`}
      >
        <form onSubmit={handleSaveDuration} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Total Viva Duration
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="60"
                step="1"
                required
                value={editDurationMinutes}
                onChange={(e) => setEditDurationMinutes(e.target.value)}
                className="w-24 p-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
              />
              <span className="text-sm text-slate-600 font-medium">minutes</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Total time allocated for a student's entire session across all 3 questions.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsDurationOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={savingDuration}>
              Save Duration
            </Button>
          </div>
        </form>
      </Modal>

      {/* Upload PDF Modal */}
      <Modal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        title={`Upload PDF for ${selectedViva?.title}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-4">
          {/* Strict Rule Notice */}
          <div className="p-3 bg-amber-50/80 rounded-lg border border-amber-200 text-xs text-amber-900 space-y-1">
            <span className="font-bold flex items-center gap-1 text-amber-950">
              <AlertTriangle className="w-4 h-4 text-amber-600" /> STRICT INSTITUTIONAL RULE:
            </span>
            <p>
              The uploaded PDF is the <strong>ONLY</strong> source of viva questions.
              Every question in the PDF must have a reference answer (e.g., <code>1. Question ... Answer: ...</code>).
              Missing answers will cause validation failure and must be corrected in the PDF.
            </p>
          </div>

          <form onSubmit={handleUploadPDF} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Select Question Bank PDF
              </label>
              <input
                type="file"
                accept=".pdf"
                required
                onChange={(e) => setPdfFile(e.target.files[0])}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={uploading}
              icon={Upload}
              disabled={!pdfFile}
            >
              Parse PDF with PyMuPDF
            </Button>
          </form>

          {/* Upload and Extraction Results Feedback */}
          {uploadResult && (
            <div className="mt-4 pt-4 border-t border-slate-200 space-y-3">
              <div
                className={`p-3 rounded-lg border text-xs flex items-start gap-2 ${
                  uploadResult.validation_passed
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-rose-50 border-rose-200 text-rose-800'
                }`}
              >
                {uploadResult.validation_passed ? (
                  <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                )}
                <div>
                  <h4 className="font-bold">
                    {uploadResult.validation_passed
                      ? 'Extraction & Validation Passed'
                      : 'Question Validation Notice'}
                  </h4>
                  <p className="mt-0.5">{uploadResult.validation_message}</p>
                </div>
              </div>

              {/* Extraction Counts */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-slate-500 block">Total Detected</span>
                  <span className="font-bold text-slate-800 text-sm mt-0.5 font-mono">
                    {uploadResult.total_detected || 0}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-200">
                  <span className="text-emerald-700 block">Valid Q&amp;A Pairs</span>
                  <span className="font-bold text-emerald-800 text-sm mt-0.5 font-mono">
                    {uploadResult.valid_count || 0}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-rose-50 border border-rose-200">
                  <span className="text-rose-700 block">Missing Answers</span>
                  <span className="font-bold text-rose-800 text-sm mt-0.5 font-mono">
                    {uploadResult.invalid_count || 0}
                  </span>
                </div>
              </div>

              {/* Preview extracted questions */}
              {uploadResult.questions?.length > 0 && (
                <div className="max-h-48 overflow-y-auto space-y-2 p-2 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                  <span className="font-bold text-slate-700 block">Extracted Questions Preview:</span>
                  {uploadResult.questions.map((q, i) => (
                    <div key={i} className="p-2 bg-white rounded border border-slate-200">
                      <p className="font-semibold text-slate-800">
                        {q.question_number}. {q.question_text}
                      </p>
                      <p className="text-slate-500 mt-1 line-clamp-2">
                        <strong>Answer:</strong> {q.reference_answer}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setIsUploadOpen(false)}>
              Close
            </Button>
            {uploadResult?.validation_passed && selectedViva && (
              <Button
                variant="success"
                icon={FileCheck}
                disabled={publishingId === selectedViva.id}
                onClick={async () => {
                  await handlePublish(selectedViva.id);
                  setIsUploadOpen(false);
                }}
              >
                {publishingId === selectedViva.id ? 'Publishing...' : 'Publish Viva Now'}
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default FacultyVivasPage;
