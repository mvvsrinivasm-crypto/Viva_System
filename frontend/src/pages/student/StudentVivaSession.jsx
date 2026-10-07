import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { studentService } from '../../services/api';
import { Card, Button, Badge, LoadingState } from '../../components/UI';
import {
  Mic,
  Square,
  Volume2,
  Send,
  AlertTriangle,
  CheckCircle2,
  Award,
  Clock,
  ShieldAlert,
  Play,
  RotateCcw,
  Sparkles,
  GraduationCap,
} from 'lucide-react';

export const StudentVivaSession = () => {
  const { id: vivaId } = useParams();
  const navigate = useNavigate();

  // Session & Question States
  const [session, setSession] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Fullscreen Entry & Gate States
  const [hasStarted, setHasStarted] = useState(false);
  const [fullscreenDenied, setFullscreenDenied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(Boolean(document.fullscreenElement));

  // Audio Recording states
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [asrLoading, setAsrLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Transcript states
  const [transcript, setTranscript] = useState('');
  const [originalAsr, setOriginalAsr] = useState('');

  // Evaluation & Completion states
  const [latestEvaluation, setLatestEvaluation] = useState(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [timeExpired, setTimeExpired] = useState(false);
  const [isTerminated, setIsTerminated] = useState(false);
  const [finalResult, setFinalResult] = useState(null);

  // Authoritative Server Session Timer states
  const [remainingSeconds, setRemainingSeconds] = useState(null);

  // 10-Second Violation Return Window states
  const [isViolationActive, setIsViolationActive] = useState(false);
  const [violationSecondsLeft, setViolationSecondsLeft] = useState(10);
  const [violationType, setViolationType] = useState('TAB_SWITCH');
  const [toastNotice, setToastNotice] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const liveTranscriptRef = useRef('');
  const violationTimerRef = useRef(null);

  // 1. Initial Load: Check session or prepare start gate
  useEffect(() => {
    const fetchSessionData = async () => {
      try {
        const res = await studentService.startViva(vivaId);
        const data = res.data;

        setSession(data.session);

        if (data.terminated || data.session?.status === 'TERMINATED_FOR_VIOLATION') {
          setIsTerminated(true);
          setIsCompleted(true);
          setFinalResult(data.result);
          setLoading(false);
          return;
        }

        if (data.time_expired || data.session?.status === 'TIME_EXPIRED') {
          setTimeExpired(true);
          setIsCompleted(true);
          setFinalResult(data.result);
          setLoading(false);
          return;
        }

        if (data.is_completed || data.session?.status === 'COMPLETED') {
          setIsCompleted(true);
          setFinalResult(data.result);
          setLoading(false);
          return;
        }

        if (data.current_question) {
          setCurrentQuestion(data.current_question);
          setTranscript(data.current_question.edited_transcript || '');
          setOriginalAsr(data.current_question.original_asr_transcript || '');
        }

        if (data.history) {
          setHistory(data.history);
        }

        // Initialize server remaining seconds
        if (data.session && data.session.expires_at) {
          const now = new Date().getTime();
          const exp = new Date(data.session.expires_at).getTime();
          const rem = Math.max(0, Math.floor((exp - now) / 1000));
          setRemainingSeconds(rem);
        }

        // Check if student was already in active violation countdown
        if (data.session && data.session.remaining_violation_seconds !== null) {
          const remV = data.session.remaining_violation_seconds;
          if (remV <= 0) {
            handleViolationTermination();
            return;
          } else {
            startViolationCountdown(remV, data.session.active_violation_type || 'TAB_SWITCH');
          }
        }

        // If already in browser fullscreen on mount, mark started immediately
        if (document.fullscreenElement) {
          setHasStarted(true);
          setIsFullscreen(true);
        }
      } catch (err) {
        console.error('Session init error:', err);
        setError(err.response?.data?.error || 'Failed to start viva session.');
      } finally {
        setLoading(false);
      }
    };

    fetchSessionData();
  }, [vivaId]);

  // 2. Authoritative Main Session Timer Countdown
  // Timer pauses during AI evaluation (submitting === true) and resumes immediately when next question starts
  useEffect(() => {
    if (!session || isCompleted || timeExpired || isTerminated || remainingSeconds === null || submitting) return;

    if (remainingSeconds <= 0) {
      handleTimeExpiry();
      return;
    }

    const interval = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          handleTimeExpiry();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [remainingSeconds, session, isCompleted, timeExpired, isTerminated, submitting]);

  // Handle Session Expiry safely
  const handleTimeExpiry = async () => {
    if (timeExpired || isCompleted || isTerminated) return;
    setTimeExpired(true);

    stopActiveAudioRecording();

    try {
      if (session) {
        const res = await studentService.finalizeViva(session.id);
        setFinalResult(res.data.result);
      }
    } catch (err) {
      console.warn('Finalize on expiry:', err);
    } finally {
      setIsCompleted(true);
    }
  };

  // 3. User Gesture: Start Viva + Automatic Fullscreen
  const handleStartVivaWithFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      }
      setIsFullscreen(true);
      setFullscreenDenied(false);
      setHasStarted(true);
    } catch (err) {
      console.warn('Fullscreen request denied:', err);
      setFullscreenDenied(true);
    }
  };

  // 4. Proctoring Event Listeners (Tab Switch & Fullscreen Exit)
  useEffect(() => {
    if (!session || isCompleted || timeExpired || isTerminated || !hasStarted) return;

    // Fullscreen change listener
    const handleFullscreenChange = () => {
      const active = Boolean(document.fullscreenElement);
      setIsFullscreen(active);

      if (!active && !isCompleted && !isTerminated) {
        triggerViolation('FULLSCREEN_EXIT');
      } else if (active && isViolationActive && !document.hidden) {
        // Restored fullscreen and tab is focused!
        handleResolveViolation();
      }
    };

    // Tab visibility change listener (Strict signal for tab switch)
    const handleVisibilityChange = () => {
      if (document.hidden) {
        triggerViolation('TAB_SWITCH');
      } else {
        // Student returned to tab
        if (isViolationActive && document.fullscreenElement) {
          handleResolveViolation();
        }
      }
    };

    // Right-click and copy/paste prevention
    const handleContextMenu = (e) => e.preventDefault();
    const handleCopy = (e) => e.preventDefault();
    const handlePaste = (e) => e.preventDefault();
    const handleCut = (e) => e.preventDefault();

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('contextmenu', handleContextMenu);
    window.addEventListener('copy', handleCopy);
    window.addEventListener('paste', handlePaste);
    window.addEventListener('cut', handleCut);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('contextmenu', handleContextMenu);
      window.removeEventListener('copy', handleCopy);
      window.removeEventListener('paste', handlePaste);
      window.removeEventListener('cut', handleCut);
    };
  }, [session, isCompleted, timeExpired, isTerminated, hasStarted, isViolationActive]);

  // Trigger violation and initiate 10-second countdown
  const triggerViolation = async (type) => {
    if (isViolationActive || isCompleted || isTerminated) return;

    setViolationType(type);
    setIsViolationActive(true);
    setViolationSecondsLeft(10);

    // 1. Immediately log violation in Neon PostgreSQL
    try {
      if (session) {
        await studentService.logViolation(session.id, type, {
          timestamp: new Date().toISOString(),
          warning_duration: '10 seconds',
        });
      }
    } catch (e) {
      console.warn('Violation log failed:', e);
    }

    startViolationCountdown(10, type);
  };

  // Start countdown interval
  const startViolationCountdown = (startSeconds, type) => {
    setIsViolationActive(true);
    setViolationSecondsLeft(startSeconds);
    if (type) setViolationType(type);

    if (violationTimerRef.current) {
      clearInterval(violationTimerRef.current);
    }

    violationTimerRef.current = setInterval(() => {
      setViolationSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(violationTimerRef.current);
          handleViolationTermination();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // Handle return before 10-second expiry
  const handleResolveViolation = async () => {
    if (violationTimerRef.current) {
      clearInterval(violationTimerRef.current);
    }

    try {
      if (session) {
        const res = await studentService.resolveViolation(session.id);
        if (res.data?.terminated) {
          // Server decided time exceeded 10.5 seconds
          setIsTerminated(true);
          setIsCompleted(true);
          setFinalResult(res.data.result);
          setIsViolationActive(false);
          return;
        }
      }
    } catch (err) {
      console.warn('Resolve violation check:', err);
    }

    setIsViolationActive(false);
    setToastNotice('Tab switch detected. This violation has been recorded.');
    setTimeout(() => setToastNotice(null), 5000);
  };

  // Handle expiration of 10 seconds -> Finalize session as TERMINATED_FOR_VIOLATION
  const handleViolationTermination = async () => {
    if (isCompleted || isTerminated) return;

    if (violationTimerRef.current) {
      clearInterval(violationTimerRef.current);
    }

    stopActiveAudioRecording();
    setIsTerminated(true);
    setIsCompleted(true);
    setIsViolationActive(false);

    try {
      if (session) {
        const res = await studentService.checkViolationExpiry(session.id);
        setFinalResult(res.data.result);
      }
    } catch (err) {
      console.error('Termination check failed:', err);
    }
  };

  // Manual return button inside violation overlay
  const handleManualReturnToViva = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      }
      setIsFullscreen(true);
      await handleResolveViolation();
    } catch (err) {
      console.warn('Failed to re-enter fullscreen:', err);
    }
  };

  // Audio helpers
  const stopActiveAudioRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {}
      setIsRecording(false);
      clearInterval(recordingTimerRef.current);
    }
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch (e) {}
    }
  };

  // 5. Audio Recording & Speech Recognition Handlers
  const startRecording = async () => {
    if (timeExpired || isCompleted || isTerminated) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);

      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);

      // Browser speech recognition
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        liveTranscriptRef.current = '';
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
          let fullText = '';
          for (let i = 0; i < event.results.length; i++) {
            fullText += event.results[i][0].transcript + ' ';
          }
          const cleanText = fullText.trim();
          liveTranscriptRef.current = cleanText;
          setTranscript(cleanText);
        };

        recognition.onerror = (event) => {
          console.warn('Speech recognition status:', event.error);
        };

        recognition.start();
        speechRecognitionRef.current = recognition;
      }
    } catch (err) {
      alert('Microphone access is required to record your oral viva answer.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(recordingTimerRef.current);
    }
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch (e) {}
    }
  };

  // Upload Audio for Speech Recognition
  const handleProcessSpeechRecognition = async () => {
    if (!audioBlob || !currentQuestion || timeExpired || isCompleted || isTerminated) return;

    setAsrLoading(true);
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'response.webm');
      const res = await studentService.uploadAudio(currentQuestion.id, formData);

      const serverAsrText = (res.data.original_asr_transcript || '').trim();
      const finalAsrText = serverAsrText || liveTranscriptRef.current || transcript;

      setOriginalAsr(finalAsrText);
      setTranscript(finalAsrText);
    } catch (err) {
      if (err.response?.data?.time_expired) {
        handleTimeExpiry();
      } else {
        if (liveTranscriptRef.current) {
          setTranscript(liveTranscriptRef.current);
          setOriginalAsr(liveTranscriptRef.current);
        } else {
          alert('Speech recognition could not process this recording. Please try recording again.');
        }
      }
    } finally {
      setAsrLoading(false);
    }
  };

  // 6. Submit Answer for Semantic Evaluation & Advance Sequentially
  const handleSubmitAnswer = async () => {
    if (!transcript.trim()) {
      alert('Please provide or review your answer transcript before submitting.');
      return;
    }

    // Stop active audio recording if still active
    stopActiveAudioRecording();

    // Stop / pause timer immediately during evaluation
    setSubmitting(true);
    try {
      const res = await studentService.submitAnswer(currentQuestion.id, transcript.trim());
      const data = res.data;

      // Update remaining seconds synchronized with server compensation
      if (data.session && data.session.remaining_seconds !== undefined && data.session.remaining_seconds !== null) {
        setRemainingSeconds(data.session.remaining_seconds);
      } else if (data.remaining_seconds !== undefined && data.remaining_seconds !== null) {
        setRemainingSeconds(data.remaining_seconds);
      }

      if (data.evaluation) {
        setLatestEvaluation(data.evaluation);
        setHistory((prev) => [
          ...prev,
          {
            question_order: currentQuestion.question_order,
            score: data.evaluation.ai_score,
            max_score: data.evaluation.max_score,
            reason: data.evaluation.evaluation_reason,
            status: 'EVALUATED',
          },
        ]);
      }

      if (data.is_completed) {
        // All 3 questions completed!
        setIsCompleted(true);
        setFinalResult(data.result);
      } else if (data.next_question) {
        // Advance to next sequential question — timer will immediately restart
        setCurrentQuestion(data.next_question);
        setTranscript(data.next_question.edited_transcript || '');
        setOriginalAsr(data.next_question.original_asr_transcript || '');
        setAudioBlob(null);
        setAudioUrl(null);
        liveTranscriptRef.current = '';
      }
    } catch (err) {
      if (err.response?.data?.time_expired) {
        handleTimeExpiry();
      } else {
        alert(err.response?.data?.error || 'Answer evaluation failed. Please verify your answer.');
      }
    } finally {
      // Re-activate countdown timer immediately for next question
      setSubmitting(false);
    }
  };

  const formatTimer = (totalSeconds) => {
    if (totalSeconds === null || totalSeconds === undefined) return '--:--';
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) return <LoadingState message="Initializing proctored viva session..." />;

  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-6 bg-white rounded-2xl shadow-sm border border-slate-200 text-center space-y-4">
        <div className="w-12 h-12 bg-rose-50 text-rose-600 rounded-xl flex items-center justify-center mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-800">Unable to Access Viva</h2>
        <p className="text-sm text-slate-600">{error}</p>
        <Button variant="primary" onClick={() => navigate('/student/vivas')}>
          Return to Assessments
        </Button>
      </div>
    );
  }

  // 7. COMPLETION / TERMINATION SCREEN
  if (isCompleted && finalResult) {
    return (
      <div className="max-w-3xl mx-auto space-y-6 py-6">
        <Card className={`border-t-4 shadow-md ${
          isTerminated
            ? 'border-t-rose-600'
            : timeExpired
            ? 'border-t-amber-600'
            : 'border-t-emerald-600'
        }`}>
          <div className="text-center space-y-4 py-4">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto ${
              isTerminated
                ? 'bg-rose-100 text-rose-600'
                : timeExpired
                ? 'bg-amber-100 text-amber-600'
                : 'bg-emerald-100 text-emerald-600'
            }`}>
              {isTerminated ? <AlertTriangle className="w-8 h-8" /> : <Award className="w-8 h-8" />}
            </div>

            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                {isTerminated
                  ? 'Viva Terminated'
                  : timeExpired
                  ? 'Viva Session Ended (Time Expired)'
                  : 'Viva Assessment Completed'}
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                Kalasalingam Academy of Research and Education • Evaluation Finalized
              </p>
            </div>

            {isTerminated && (
              <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs max-w-lg mx-auto font-medium">
                Your viva was automatically submitted because you did not return within the allowed 10-second period.
              </div>
            )}

            {timeExpired && !isTerminated && (
              <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl text-xs max-w-md mx-auto">
                Your viva session time has ended. Your score was calculated from completed questions using the best-scoring policy.
              </div>
            )}

            {/* Final Grade Display: Best 2 of 3, Max 20 */}
            <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200 inline-block min-w-[280px]">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
                Final Grade (Best 2 of 3 Questions)
              </span>
              <span className="text-4xl font-extrabold text-blue-900 font-mono mt-1 block">
                {finalResult.final_score} / 20
              </span>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Counted Questions: #{finalResult.counted_question_1} and #{finalResult.counted_question_2}
              </span>
            </div>

            {/* Individual Question Marks Breakdown */}
            <div className="grid grid-cols-3 gap-3 max-w-md mx-auto pt-2">
              <div className={`p-3 rounded-xl border text-center ${
                finalResult.counted_question_1 === 1 || finalResult.counted_question_2 === 1
                  ? 'bg-blue-50/70 border-blue-300 font-semibold text-blue-900'
                  : 'bg-white border-slate-200 text-slate-600'
              }`}>
                <span className="text-[11px] font-semibold text-slate-500 block">Question 1</span>
                <span className="text-base font-bold font-mono">
                  {finalResult.q1_score} / 10
                </span>
              </div>

              <div className={`p-3 rounded-xl border text-center ${
                finalResult.counted_question_1 === 2 || finalResult.counted_question_2 === 2
                  ? 'bg-blue-50/70 border-blue-300 font-semibold text-blue-900'
                  : 'bg-white border-slate-200 text-slate-600'
              }`}>
                <span className="text-[11px] font-semibold text-slate-500 block">Question 2</span>
                <span className="text-base font-bold font-mono">
                  {finalResult.q2_score} / 10
                </span>
              </div>

              <div className={`p-3 rounded-xl border text-center ${
                finalResult.counted_question_1 === 3 || finalResult.counted_question_2 === 3
                  ? 'bg-blue-50/70 border-blue-300 font-semibold text-blue-900'
                  : 'bg-white border-slate-200 text-slate-600'
              }`}>
                <span className="text-[11px] font-semibold text-slate-500 block">Question 3</span>
                <span className="text-base font-bold font-mono">
                  {finalResult.q3_score} / 10
                </span>
              </div>
            </div>

            <div className="pt-4 flex justify-center gap-3">
              <Button
                variant="primary"
                onClick={() => navigate('/student/results')}
                icon={Award}
              >
                View Full Results Sheet
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate('/student/dashboard')}
              >
                Return to Dashboard
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // 8. MANDATORY AUTOMATIC FULLSCREEN START GATE
  // If not yet in browser fullscreen, present the Start Viva button that requests Fullscreen on user gesture
  if (!hasStarted || !isFullscreen) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <div className="p-8 bg-white rounded-2xl shadow-sm border border-slate-200 text-center space-y-6">
          <div className="w-16 h-16 bg-blue-50 text-blue-700 rounded-2xl flex items-center justify-center mx-auto">
            <GraduationCap className="w-8 h-8" />
          </div>

          <div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
              Proctored Oral Examination
            </span>
            <h1 className="text-2xl font-bold text-slate-900 mt-3">
              {session?.viva_title || 'Oral Viva Assessment'}
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Kalasalingam Academy of Research and Education
            </p>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-2 text-left">
            <div className="font-semibold text-slate-900">Mandatory Assessment Protocol:</div>
            <ul className="list-disc list-inside space-y-1.5 text-slate-600">
              <li>
                <strong>Automatic Fullscreen:</strong> Browser will enter full screen automatically upon starting.
              </li>
              <li>
                <strong>10-Second Return Window:</strong> Switching tabs or exiting fullscreen triggers a 10-second warning countdown before automatic submission.
              </li>
              <li>
                <strong>Sequential Questions:</strong> 3 questions presented one by one. Answers are permanently submitted upon advancing.
              </li>
              <li>
                <strong>Best 2 of 3 Scoring:</strong> Final grade is determined by your top 2 scored answers (Maximum 20 marks).
              </li>
            </ul>
          </div>

          {fullscreenDenied ? (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs space-y-3">
              <div className="flex items-center justify-center gap-2 font-bold text-rose-900 text-sm">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                Fullscreen access is required to start the viva.
              </div>
              <p className="text-[11px] text-rose-700">
                Please allow browser fullscreen permission to enter this monitored oral assessment.
              </p>
              <Button
                variant="primary"
                onClick={handleStartVivaWithFullscreen}
                icon={RotateCcw}
              >
                Try Again
              </Button>
            </div>
          ) : (
            <div className="pt-2">
              <Button
                variant="primary"
                size="lg"
                onClick={handleStartVivaWithFullscreen}
                icon={Play}
                className="w-full sm:w-auto px-10 text-base"
              >
                Start Viva
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // 9. ACTIVE SEQUENTIAL VIVA SESSION UI (IN FULLSCREEN)
  const qNum = currentQuestion ? currentQuestion.question_order : 1;
  const isTimeCritical = remainingSeconds !== null && remainingSeconds <= 30;
  const isTimeEmergency = remainingSeconds !== null && remainingSeconds <= 10;

  return (
    <div className="space-y-6">
      {/* 10-Second Violation Return Overlay Modal */}
      {isViolationActive && (
        <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 text-center space-y-5 shadow-2xl border-2 border-rose-500 animate-in fade-in">
            <div className="w-16 h-16 bg-rose-100 text-rose-600 rounded-2xl flex items-center justify-center mx-auto">
              <AlertTriangle className="w-8 h-8 animate-pulse text-rose-600" />
            </div>

            <div>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 uppercase tracking-wider">
                Viva Violation Detected
              </span>
              <h3 className="text-xl font-bold text-slate-900 mt-2">
                You have left the viva session
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                {violationType === 'FULLSCREEN_EXIT'
                  ? 'Browser fullscreen mode was exited.'
                  : 'Tab switch or window defocus detected.'}
              </p>
            </div>

            <div className="p-4 bg-rose-50 rounded-xl border border-rose-200">
              <span className="text-xs text-rose-700 font-semibold block">
                Return to the viva within:
              </span>
              <span className="text-5xl font-black font-mono text-rose-600 my-1 block">
                {violationSecondsLeft}
              </span>
              <span className="text-[11px] text-rose-600 font-medium">
                seconds remaining
              </span>
            </div>

            <p className="text-xs text-slate-600">
              If you do not return, your viva will be automatically submitted and finalized.
            </p>

            <Button
              variant="danger"
              className="w-full text-sm font-bold py-2.5"
              onClick={handleManualReturnToViva}
            >
              Return to Viva (Re-enter Fullscreen)
            </Button>
          </div>
        </div>
      )}

      {/* Floating Toast Notification on Successful Return */}
      {toastNotice && (
        <div className="fixed top-4 right-4 z-40 p-3 bg-amber-50 border border-amber-300 text-amber-900 rounded-xl shadow-lg flex items-center gap-2 text-xs font-semibold">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{toastNotice}</span>
        </div>
      )}

      {/* Proctoring Header: Question Indicator + Session Timer (NO Fullscreen button) */}
      <div className="bg-slate-900 text-white rounded-2xl p-4 sm:p-5 shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-600 text-white">
              Question {qNum} of 3
            </span>
            <span className="text-xs text-slate-400 font-medium">
              KARE Viva Evaluation System
            </span>
          </div>
          <h2 className="text-base sm:text-lg font-bold text-slate-100 line-clamp-1">
            {session?.viva_title || 'Oral Viva Examination'}
          </h2>
        </div>

        {/* Prominent Session Timer Only (No fullscreen activation button) */}
        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-mono font-bold transition-all ${
            submitting
              ? 'bg-amber-500/20 text-amber-300 border-amber-500 ring-2 ring-amber-400/30'
              : isTimeEmergency
              ? 'bg-rose-500/20 text-rose-300 border-rose-500 animate-pulse'
              : isTimeCritical
              ? 'bg-amber-500/20 text-amber-300 border-amber-500'
              : 'bg-slate-800 text-slate-100 border-slate-700'
          }`}>
            <Clock className={`w-4 h-4 ${submitting ? 'text-amber-400 animate-spin' : 'text-sky-400'}`} />
            <span>
              {submitting ? 'Timer Paused: ' : 'Time Remaining: '}
              {formatTimer(remainingSeconds)}
            </span>
            {submitting && (
              <span className="text-[10px] uppercase tracking-wider bg-amber-400/30 text-amber-200 px-1.5 py-0.5 rounded font-sans font-semibold">
                Paused
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Progress Circles (● ○ ○) */}
      <div className="flex items-center justify-center gap-3">
        {[1, 2, 3].map((order) => {
          const isDone = history.some((h) => h.question_order === order);
          const isCurrent = order === qNum;
          return (
            <div key={order} className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  isDone
                    ? 'bg-emerald-600 text-white'
                    : isCurrent
                    ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                    : 'bg-slate-200 text-slate-500'
                }`}
              >
                {isDone ? <CheckCircle2 className="w-4 h-4" /> : order}
              </div>
              <span className={`text-xs font-semibold ${isCurrent ? 'text-blue-900' : 'text-slate-500'}`}>
                Question {order}
              </span>
              {order < 3 && <div className="w-6 h-0.5 bg-slate-200 mx-1" />}
            </div>
          );
        })}
      </div>

      {/* Single Current Question Card & Speech Workflow */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: ONLY the Current Question Text */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="border-t-4 border-t-blue-600 shadow-sm">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Question {qNum} of 3
                </span>
                <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                  Max: 10 Marks
                </span>
              </div>

              <div className="min-h-[120px] flex items-center">
                <h3 className="text-base sm:text-lg font-bold text-slate-900 leading-relaxed">
                  {currentQuestion?.question_text || 'Loading oral assessment question...'}
                </h3>
              </div>

              <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-xl text-xs text-blue-900 space-y-1">
                <span className="font-bold block">Oral Examination Instructions:</span>
                <p className="text-[11px] text-blue-800 leading-relaxed">
                  Record your answer verbally using the microphone. Your spoken response will be transcribed to text. You can review and edit your transcript before final submission.
                </p>
              </div>
            </div>
          </Card>

          {/* Feedback from previous question if any */}
          {latestEvaluation && (
            <Card className="bg-emerald-50/60 border-emerald-200">
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between font-bold text-emerald-950">
                  <span>Previous Question Evaluated</span>
                  <span className="font-mono text-emerald-800">
                    {latestEvaluation.ai_score} / {latestEvaluation.max_score}
                  </span>
                </div>
                {latestEvaluation.evaluation_reason && (
                  <p className="text-emerald-900/90 text-[11px] leading-relaxed">
                    {latestEvaluation.evaluation_reason}
                  </p>
                )}
              </div>
            </Card>
          )}
        </div>

        {/* Right Column: Audio Recording, Speech Recognition, & Editable Transcript */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="shadow-sm">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Oral Response &amp; Transcript
                </span>
                <span className="text-xs text-slate-400">
                  Step {audioBlob ? '2 of 2: Review Transcript' : '1 of 2: Record Voice'}
                </span>
              </div>

              {/* Audio Recording Controls */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {!isRecording ? (
                      <Button
                        variant="primary"
                        size="md"
                        icon={Mic}
                        onClick={startRecording}
                        disabled={submitting || asrLoading}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        Start Recording
                      </Button>
                    ) : (
                      <Button
                        variant="danger"
                        size="md"
                        icon={Square}
                        onClick={stopRecording}
                        className="animate-pulse"
                      >
                        Stop Recording ({recordingSeconds}s)
                      </Button>
                    )}

                    {audioUrl && !isRecording && (
                      <audio controls src={audioUrl} className="h-9 max-w-[200px]" />
                    )}
                  </div>

                  {audioBlob && !isRecording && (
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={Sparkles}
                      loading={asrLoading}
                      onClick={handleProcessSpeechRecognition}
                    >
                      Process Speech
                    </Button>
                  )}
                </div>

                {isRecording && (
                  <div className="flex items-center gap-2 text-xs text-rose-600 font-semibold animate-pulse pt-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-600" />
                    <span>Microphone is listening... Speak clearly.</span>
                  </div>
                )}
              </div>

              {/* Evaluation Notice banner when timer is paused */}
              {submitting && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-3 text-xs text-amber-900 shadow-sm animate-pulse">
                  <Clock className="w-5 h-5 text-amber-600 shrink-0 animate-spin" />
                  <div>
                    <span className="font-bold text-amber-950">AI Answer Evaluation in Progress...</span>
                    <p className="text-[11px] text-amber-800 mt-0.5">
                      Your examination countdown timer is <strong>paused</strong>. As soon as evaluation completes, the timer will immediately resume when Question {Math.min(3, qNum + 1)} begins.
                    </p>
                  </div>
                </div>
              )}

              {/* Editable Speech Transcript */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Spoken Answer Transcript (Editable)
                  </label>
                  {transcript && (
                    <span className="text-[11px] text-slate-400">
                      {transcript.trim().split(/\s+/).filter(Boolean).length} words
                    </span>
                  )}
                </div>

                <textarea
                  rows={6}
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder="Your transcribed spoken answer will appear here automatically. You may edit or clarify any technical terms before submission..."
                  className="w-full p-3 text-xs sm:text-sm border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white leading-relaxed resize-none font-sans"
                  disabled={submitting}
                />
              </div>

              {/* Submission Button */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <span className="text-[11px] text-slate-400">
                  {qNum === 3 ? 'Final question — Complete viva' : `Advances to Question ${qNum + 1}`}
                </span>

                <Button
                  variant="primary"
                  size="md"
                  icon={Send}
                  loading={submitting}
                  disabled={!transcript.trim() || isRecording}
                  onClick={handleSubmitAnswer}
                >
                  {qNum === 3 ? 'Submit Answer & Finish Viva' : 'Submit Answer & Next Question'}
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default StudentVivaSession;
