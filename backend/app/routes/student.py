from datetime import datetime, timezone
from pathlib import Path
import os
import uuid
import logging
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.viva import Viva, VivaStatus
from app.models.viva_session import VivaSession, SessionStatus
from app.models.session_question import SessionQuestion
from app.models.question import Question
from app.models.answer import Answer
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.models.violation import Violation, ViolationType
from app.middleware.auth import student_required
from app.services.viva_service import VivaService
from app.services.asr_service import ASRService
from app.services.llm_service import LLMEvaluationService

logger = logging.getLogger(__name__)

student_bp = Blueprint("student", __name__, url_prefix="/api/student")


def _is_session_expired(session: VivaSession) -> bool:
    """Helper to check if session has exceeded its authoritative server timer."""
    if not session.expires_at:
        return False
    now = datetime.now(timezone.utc)
    exp = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
    return now >= exp


def _get_current_active_question(session: VivaSession):
    """
    Finds the active sequential question.
    Returns: (current_sq, completed_history)
    """
    sqs = SessionQuestion.query.filter_by(session_id=session.id).order_by(SessionQuestion.question_order).all()
    current_sq = None
    history = []

    for sq in sqs:
        is_evaluated = bool(sq.answer and sq.answer.evaluation)
        if is_evaluated:
            history.append({
                "question_order": sq.question_order,
                "score": sq.answer.evaluation.ai_score,
                "max_score": sq.answer.evaluation.max_score,
                "reason": sq.answer.evaluation.evaluation_reason,
                "status": "EVALUATED",
            })
        elif current_sq is None:
            current_sq = sq

    return current_sq, history


@student_bp.route("/vivas", methods=["GET"])
@student_required
def get_available_vivas():
    """List all vivas that are active or published, with student's personal status."""
    vivas = Viva.query.filter(Viva.status.in_([VivaStatus.PUBLISHED, VivaStatus.ACTIVE])).order_by(Viva.created_at.desc()).all()
    student_id = g.current_user.id

    result_list = []
    for viva in vivas:
        session = VivaSession.query.filter_by(
            viva_id=viva.id,
            student_id=student_id,
        ).order_by(VivaSession.started_at.desc()).first()

        item = viva.to_dict()
        if session:
            item["session_id"] = session.id
            item["session_status"] = session.status
            if session.result:
                item["final_score"] = session.result.final_score
                item["max_score"] = session.result.max_score
            else:
                item["final_score"] = None
                item["max_score"] = 20.0
        else:
            item["session_id"] = None
            item["session_status"] = "NOT_STARTED"
            item["final_score"] = None
            item["max_score"] = 20.0

        result_list.append(item)

    return jsonify({"vivas": result_list}), 200


@student_bp.route("/vivas/<int:viva_id>/start", methods=["POST"])
@student_required
def start_viva(viva_id):
    """
    Start or resume a viva session for the student.
    Enforces sequential questions: returns ONLY Question 1 at start.
    Never exposes Question 2 or Question 3 before previous questions are submitted.
    """
    try:
        session = VivaService.start_student_session(
            student_id=g.current_user.id,
            viva_id=viva_id,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Check if session was terminated for violation
    if session.status == SessionStatus.TERMINATED_FOR_VIOLATION:
        return jsonify({
            "message": "Your viva was automatically submitted because you did not return within the allowed 10-second period.",
            "terminated": True,
            "is_completed": True,
            "session": session.to_dict(),
            "result": session.result.to_dict(include_audits=False) if session.result else None,
        }), 200

    # Check if student attempted to reload while active violation countdown expired (>10s)
    if session.status == SessionStatus.IN_PROGRESS and session.active_violation_started_at:
        now = datetime.now(timezone.utc)
        v_start = session.active_violation_started_at if session.active_violation_started_at.tzinfo else session.active_violation_started_at.replace(tzinfo=timezone.utc)
        elapsed = (now - v_start).total_seconds()
        if elapsed >= 10.0:
            result = VivaService.finalize_session(session.id, status=SessionStatus.TERMINATED_FOR_VIOLATION)
            session.active_violation_started_at = None
            session.active_violation_type = None
            db.session.commit()
            return jsonify({
                "message": "Your viva was automatically submitted because you did not return within the allowed 10-second period.",
                "terminated": True,
                "is_completed": True,
                "session": session.to_dict(),
                "result": result.to_dict(include_audits=False),
            }), 200

    # Check if session time already expired
    if _is_session_expired(session):
        result = VivaService.finalize_session(session.id, status=SessionStatus.TIME_EXPIRED)
        return jsonify({
            "message": "Your viva session time has ended.",
            "time_expired": True,
            "session": session.to_dict(),
            "result": result.to_dict(include_audits=False),
        }), 200

    current_sq, history = _get_current_active_question(session)

    if not current_sq:
        # All 3 questions answered
        result = VivaService.finalize_session(session.id, status=SessionStatus.COMPLETED)
        return jsonify({
            "message": "Viva assessment completed.",
            "session": session.to_dict(),
            "is_completed": True,
            "result": result.to_dict(include_audits=False),
        }), 200

    # ONLY send the current active question
    question_payload = {
        "id": current_sq.id,
        "question_order": current_sq.question_order,
        "total_questions": 3,
        "question_text": current_sq.question.question_text,
        "max_marks": 10,
        "original_asr_transcript": current_sq.answer.original_asr_transcript if current_sq.answer else "",
        "edited_transcript": current_sq.answer.edited_transcript if current_sq.answer else "",
        "has_audio": bool(current_sq.answer and current_sq.answer.audio_path),
    }

    return jsonify({
        "message": "Viva session active.",
        "session": session.to_dict(),
        "current_question": question_payload,
        "questions": [sq.to_dict(include_answer=False) for sq in session.session_questions],
        "history": history,
    }), 200


@student_bp.route("/sessions/<int:session_id>", methods=["GET"])
@student_required
def get_session(session_id):
    """
    Get active session status and currently active question.
    Strictly delivers only the active sequential question.
    """
    session = db.session.get(VivaSession, session_id)
    if not session or session.student_id != g.current_user.id:
        return jsonify({"error": "Session not found."}), 404

    # Check if session was terminated for violation
    if session.status == SessionStatus.TERMINATED_FOR_VIOLATION:
        return jsonify({
            "message": "Your viva was automatically submitted because you did not return within the allowed 10-second period.",
            "terminated": True,
            "is_completed": True,
            "session": session.to_dict(),
            "result": session.result.to_dict(include_audits=False) if session.result else None,
        }), 200

    # Check if student attempted to reload while active violation countdown expired (>10s)
    if session.status == SessionStatus.IN_PROGRESS and session.active_violation_started_at:
        now = datetime.now(timezone.utc)
        v_start = session.active_violation_started_at if session.active_violation_started_at.tzinfo else session.active_violation_started_at.replace(tzinfo=timezone.utc)
        elapsed = (now - v_start).total_seconds()
        if elapsed >= 10.0:
            result = VivaService.finalize_session(session.id, status=SessionStatus.TERMINATED_FOR_VIOLATION)
            session.active_violation_started_at = None
            session.active_violation_type = None
            db.session.commit()
            return jsonify({
                "message": "Your viva was automatically submitted because you did not return within the allowed 10-second period.",
                "terminated": True,
                "is_completed": True,
                "session": session.to_dict(),
                "result": result.to_dict(include_audits=False),
            }), 200

    # Check expiration
    if session.status == SessionStatus.IN_PROGRESS and _is_session_expired(session):
        result = VivaService.finalize_session(session.id, status=SessionStatus.TIME_EXPIRED)
        return jsonify({
            "message": "Your viva session time has ended.",
            "time_expired": True,
            "is_completed": True,
            "session": session.to_dict(),
            "result": result.to_dict(include_audits=False),
        }), 200

    if session.status in (SessionStatus.COMPLETED, SessionStatus.TIME_EXPIRED, SessionStatus.TERMINATED_FOR_VIOLATION):
        return jsonify({
            "session": session.to_dict(),
            "is_completed": True,
            "time_expired": session.status == SessionStatus.TIME_EXPIRED,
            "terminated": session.status == SessionStatus.TERMINATED_FOR_VIOLATION,
            "result": session.result.to_dict(include_audits=False) if session.result else None,
        }), 200

    current_sq, history = _get_current_active_question(session)

    if not current_sq:
        result = VivaService.finalize_session(session.id, status=SessionStatus.COMPLETED)
        return jsonify({
            "session": session.to_dict(),
            "is_completed": True,
            "result": result.to_dict(include_audits=False),
        }), 200

    question_payload = {
        "id": current_sq.id,
        "question_order": current_sq.question_order,
        "total_questions": 3,
        "question_text": current_sq.question.question_text,
        "max_marks": 10,
        "original_asr_transcript": current_sq.answer.original_asr_transcript if current_sq.answer else "",
        "edited_transcript": current_sq.answer.edited_transcript if current_sq.answer else "",
        "has_audio": bool(current_sq.answer and current_sq.answer.audio_path),
    }

    return jsonify({
        "session": session.to_dict(),
        "current_question": question_payload,
        "history": history,
    }), 200


@student_bp.route("/session-questions/<int:sq_id>/audio", methods=["POST"])
@student_bp.route("/answers/<int:sq_id>/transcribe", methods=["POST"])
@student_bp.route("/answers/<int:sq_id>/audio", methods=["POST"])
@student_required
def upload_audio(sq_id):
    """
    Upload recorded audio for the current question.
    Converts audio via FFmpeg and runs Speech Recognition.
    Validates server timer before processing.
    """
    sq = db.session.get(SessionQuestion, sq_id)
    if not sq or sq.session.student_id != g.current_user.id:
        return jsonify({"error": "Question not found in your session."}), 404

    session = sq.session
    if session.status != SessionStatus.IN_PROGRESS:
        return jsonify({"error": "Viva session is not active."}), 400

    # Verify session has not expired
    if _is_session_expired(session):
        VivaService.finalize_session(session.id, status=SessionStatus.TIME_EXPIRED)
        return jsonify({
            "error": "Your viva session time has ended.",
            "time_expired": True,
        }), 403

    # Enforce sequential active question
    current_active_sq, _ = _get_current_active_question(session)
    if current_active_sq and current_active_sq.id != sq.id:
        return jsonify({"error": f"You must answer Question {current_active_sq.question_order} first."}), 400

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided."}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "Empty audio file."}), 400

    audio_dir = Path(current_app.config["AUDIO_FOLDER"])
    audio_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(audio_file.filename).suffix or ".webm"
    safe_name = f"sess_{sq.session_id}_q{sq.question_order}_{uuid.uuid4().hex[:8]}{ext}"
    saved_path = audio_dir / safe_name
    audio_file.save(str(saved_path))

    # Transcribe via Speech Recognition service
    asr_service = ASRService(current_app.config)
    question_context = sq.question.question_text if sq.question else ""
    mime_type = request.content_type or "audio/webm"

    try:
        asr_transcript = asr_service.transcribe_audio(saved_path, context_hint=question_context, mime_type=mime_type)
    except Exception as e:
        logger.error("Speech recognition error during audio processing: %s", e)
        asr_transcript = ""

    # Preserve or update answer record
    answer = sq.answer
    if not answer:
        answer = Answer(
            session_question_id=sq.id,
            audio_path=str(saved_path),
            original_asr_transcript=asr_transcript,
            edited_transcript=asr_transcript,
            submitted_at=datetime.now(timezone.utc),
        )
        db.session.add(answer)
    else:
        answer.audio_path = str(saved_path)
        if asr_transcript:
            answer.original_asr_transcript = asr_transcript
            answer.edited_transcript = asr_transcript
        answer.submitted_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify({
        "message": "Speech recognition complete.",
        "original_asr_transcript": answer.original_asr_transcript,
        "edited_transcript": answer.edited_transcript,
    }), 200


@student_bp.route("/session-questions/<int:sq_id>/transcript", methods=["POST"])
@student_bp.route("/answers/<int:sq_id>/transcript", methods=["POST"])
@student_required
def update_transcript(sq_id):
    """Allows student to edit the transcript before submitting."""
    sq = db.session.get(SessionQuestion, sq_id)
    if not sq or sq.session.student_id != g.current_user.id:
        return jsonify({"error": "Question not found in your session."}), 404

    session = sq.session
    if session.status != SessionStatus.IN_PROGRESS or _is_session_expired(session):
        return jsonify({"error": "Session is no longer active.", "time_expired": True}), 403

    data = request.get_json() or {}
    edited_text = (data.get("transcript") or "").strip()

    if not edited_text:
        return jsonify({"error": "Transcript cannot be empty."}), 400

    answer = sq.answer
    if not answer:
        answer = Answer(
            session_question_id=sq.id,
            original_asr_transcript=edited_text,
            edited_transcript=edited_text,
            submitted_at=datetime.now(timezone.utc),
        )
        db.session.add(answer)
    else:
        answer.edited_transcript = edited_text

    db.session.commit()

    return jsonify({
        "message": "Transcript saved.",
        "edited_transcript": answer.edited_transcript,
    }), 200


@student_bp.route("/session-questions/<int:sq_id>/submit", methods=["POST"])
@student_bp.route("/answers/<int:sq_id>/submit", methods=["POST"])
@student_required
def submit_answer(sq_id):
    """
    Submits student's edited transcript for Ollama llama3.2:3b evaluation.
    Enforces sequential progression:
    - If Question 1 submitted: evaluates and returns Question 2.
    - If Question 2 submitted: evaluates and returns Question 3.
    - If Question 3 submitted: calculates final score (Best 2 of 3, max 20) and completes session.
    """
    sq = db.session.get(SessionQuestion, sq_id)
    if not sq or sq.session.student_id != g.current_user.id:
        return jsonify({"error": "Question not found in your session."}), 404

    session = sq.session
    if session.status != SessionStatus.IN_PROGRESS:
        return jsonify({"error": "Viva session is already completed or inactive."}), 400

    # 1. Authoritative Server Timer Check
    if _is_session_expired(session):
        result = VivaService.finalize_session(session.id, status=SessionStatus.TIME_EXPIRED)
        return jsonify({
            "error": "Your viva session time has ended.",
            "time_expired": True,
            "result": result.to_dict(include_audits=False),
        }), 403

    # 2. Strict Sequential Order Enforcement
    if sq.question_order > 1:
        prev_sq = SessionQuestion.query.filter_by(
            session_id=session.id,
            question_order=sq.question_order - 1,
        ).first()
        if not prev_sq or not prev_sq.answer or not prev_sq.answer.evaluation:
            return jsonify({
                "error": f"Please answer Question {sq.question_order - 1} before submitting this question."
            }), 400

    data = request.get_json() or {}
    text_to_eval = (data.get("transcript") or "").strip()

    # 3. Preserve Transcript in Database BEFORE Calling Evaluation
    eval_started_at = datetime.now(timezone.utc)
    answer = sq.answer
    if not answer:
        if not text_to_eval:
            return jsonify({"error": "Please provide an answer before submitting."}), 400
        answer = Answer(
            session_question_id=sq.id,
            original_asr_transcript=text_to_eval,
            edited_transcript=text_to_eval,
            submitted_at=datetime.now(timezone.utc),
        )
        db.session.add(answer)
        db.session.flush()
    else:
        if text_to_eval:
            answer.edited_transcript = text_to_eval
        answer.submitted_at = datetime.now(timezone.utc)

    db.session.commit()

    # 4. Evaluate using Ollama llama3.2:3b against PDF Reference Answer
    eval_service = LLMEvaluationService(current_app.config)
    try:
        eval_result = eval_service.evaluate_answer(
            question=sq.question.question_text,
            reference_answer=sq.question.reference_answer,
            student_answer=answer.edited_transcript or "",
        )
    except Exception as e:
        logger.error("Evaluation service error: %s", e)
        eval_result = {
            "score": 5.0,
            "max_score": 10.0,
            "correct_points": ["Answer recorded"],
            "missing_points": [],
            "reason": "Evaluation temporarily deferred. Score estimated pending faculty review.",
        }

    score = eval_result["score"]
    reason = eval_result["reason"]

    evaluation = answer.evaluation
    if not evaluation:
        evaluation = Evaluation(
            answer_id=answer.id,
            ai_score=score,
            max_score=10.0,
            evaluation_reason=reason,
            evaluation_json=eval_result,
            evaluated_at=datetime.now(timezone.utc),
        )
        db.session.add(evaluation)
    else:
        evaluation.ai_score = score
        evaluation.evaluation_reason = reason
        evaluation.evaluation_json = eval_result
        evaluation.evaluated_at = datetime.now(timezone.utc)

    # Compensate session expiry timer: stop/freeze timer during evaluation
    # Add elapsed evaluation duration to session.expires_at so AI evaluation time doesn't consume exam time
    eval_elapsed = datetime.now(timezone.utc) - eval_started_at
    if session.expires_at:
        current_exp = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
        session.expires_at = current_exp + eval_elapsed

    db.session.commit()

    # 5. Determine Next Step (Sequential Questions)
    if sq.question_order < 3:
        # Fetch the immediate next question ONLY
        next_sq = SessionQuestion.query.filter_by(
            session_id=session.id,
            question_order=sq.question_order + 1,
        ).first()

        next_question_payload = {
            "id": next_sq.id,
            "question_order": next_sq.question_order,
            "total_questions": 3,
            "question_text": next_sq.question.question_text,
            "max_marks": 10,
            "original_asr_transcript": next_sq.answer.original_asr_transcript if next_sq.answer else "",
            "edited_transcript": next_sq.answer.edited_transcript if next_sq.answer else "",
            "has_audio": bool(next_sq.answer and next_sq.answer.audio_path),
        }

        session_dict = session.to_dict()
        return jsonify({
            "message": "Answer evaluated successfully.",
            "evaluation": evaluation.to_dict(),
            "next_question": next_question_payload,
            "session": session_dict,
            "remaining_seconds": session_dict["remaining_seconds"],
            "has_next": True,
            "is_completed": False,
        }), 200
    else:
        # Question 3 submitted: Calculate Best 2 of 3 (maximum 20 marks)
        result = VivaService.finalize_session(session.id, status=SessionStatus.COMPLETED)
        return jsonify({
            "message": "Viva evaluation completed successfully.",
            "evaluation": evaluation.to_dict(),
            "is_completed": True,
            "result": result.to_dict(include_audits=False),
        }), 200


@student_bp.route("/sessions/<int:session_id>/finalize", methods=["POST"])
@student_required
def finalize_viva(session_id):
    """
    Completes or expires the viva session.
    Calculates final score using the BEST 2 OF 3 questions in backend Python code.
    Maximum final score: 20 marks.
    """
    session = db.session.get(VivaSession, session_id)
    if not session or session.student_id != g.current_user.id:
        return jsonify({"error": "Session not found."}), 404

    target_status = SessionStatus.TIME_EXPIRED if _is_session_expired(session) else SessionStatus.COMPLETED

    try:
        result = VivaService.finalize_session(session.id, status=target_status)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "message": "Viva session finalized.",
        "status": session.status,
        "result": result.to_dict(include_audits=False),
    }), 200


@student_bp.route("/sessions/<int:session_id>/violations", methods=["POST"])
@student_required
def log_violation(session_id):
    """
    Record browser anti-cheating violation (fullscreen exit, tab switch, etc.).
    Immediately initiates a 10-second return window countdown for TAB_SWITCH and FULLSCREEN_EXIT.
    """
    session = db.session.get(VivaSession, session_id)
    if not session or session.student_id != g.current_user.id:
        return jsonify({"error": "Session not found."}), 404

    data = request.get_json() or {}
    v_type = data.get("type") or data.get("violation_type") or "WINDOW_BLUR"
    metadata = data.get("metadata", {})

    if v_type not in ViolationType.ALL:
        v_type = ViolationType.FULLSCREEN_EXIT if "FULLSCREEN" in v_type else ViolationType.WINDOW_BLUR

    # Set active violation timer if tab switch or fullscreen exit occurred
    if v_type in (ViolationType.TAB_SWITCH, ViolationType.FULLSCREEN_EXIT, ViolationType.WINDOW_BLUR):
        if not session.active_violation_started_at and session.status == SessionStatus.IN_PROGRESS:
            session.active_violation_started_at = datetime.now(timezone.utc)
            session.active_violation_type = v_type
        metadata["warning_duration"] = "10 seconds"

    violation = Violation(
        session_id=session.id,
        student_id=g.current_user.id,
        type=v_type,
        timestamp=datetime.now(timezone.utc),
        metadata_json=metadata,
    )
    db.session.add(violation)
    db.session.commit()

    total_violations = Violation.query.filter_by(session_id=session.id).count()

    return jsonify({
        "status": "violation_logged",
        "total_violations": total_violations,
        "warning_seconds": 10,
        "active_violation_started_at": session.active_violation_started_at.isoformat() if session.active_violation_started_at else None,
        "violation": violation.to_dict(),
    }), 201


@student_bp.route("/sessions/<int:session_id>/violations/resolve", methods=["POST"])
@student_required
def resolve_violation(session_id):
    """
    Student returned to the viva session before the 10-second warning countdown expired.
    Server checks timestamp:
    - If elapsed <= 10.5 seconds: clears active violation, cancels warning, resumes viva.
    - If elapsed > 10.5 seconds: server-authoritative termination for violation.
    """
    session = db.session.get(VivaSession, session_id)
    if not session or session.student_id != g.current_user.id:
        return jsonify({"error": "Session not found."}), 404

    if session.status != SessionStatus.IN_PROGRESS:
        return jsonify({
            "terminated": True,
            "status": session.status,
            "result": session.result.to_dict(include_audits=False) if session.result else None,
        }), 200

    if not session.active_violation_started_at:
        return jsonify({
            "terminated": False,
            "message": "No active violation countdown was running.",
        }), 200

    now = datetime.now(timezone.utc)
    v_start = session.active_violation_started_at if session.active_violation_started_at.tzinfo else session.active_violation_started_at.replace(tzinfo=timezone.utc)
    elapsed = (now - v_start).total_seconds()

    if elapsed > 10.5:
        # Student took more than 10 seconds to return! Server-authoritative termination.
        result = VivaService.finalize_session(session.id, status=SessionStatus.TERMINATED_FOR_VIOLATION)
        session.active_violation_started_at = None
        session.active_violation_type = None
        db.session.commit()
        return jsonify({
            "terminated": True,
            "status": SessionStatus.TERMINATED_FOR_VIOLATION,
            "message": "Your viva was automatically submitted because you did not return within the allowed 10-second period.",
            "result": result.to_dict(include_audits=False),
        }), 200

    # Student returned within the 10-second window!
    session.active_violation_started_at = None
    session.active_violation_type = None
    db.session.commit()

    return jsonify({
        "terminated": False,
        "message": "Tab switch / fullscreen exit detected. This violation has been recorded.",
        "elapsed_seconds": round(elapsed, 1),
    }), 200


@student_bp.route("/sessions/<int:session_id>/violations/check-expiry", methods=["POST"])
@student_required
def check_violation_expiry(session_id):
    """
    Triggered when 10-second warning countdown expires or on heartbeat.
    Server verifies current_time >= active_violation_started_at + 10s.
    If student did not return, safely finalizes and terminates session with TERMINATED_FOR_VIOLATION.
    """
    session = db.session.get(VivaSession, session_id)
    if not session or session.student_id != g.current_user.id:
        return jsonify({"error": "Session not found."}), 404

    if session.status != SessionStatus.IN_PROGRESS:
        return jsonify({
            "terminated": True,
            "status": session.status,
            "result": session.result.to_dict(include_audits=False) if session.result else None,
        }), 200

    if session.active_violation_started_at:
        now = datetime.now(timezone.utc)
        v_start = session.active_violation_started_at if session.active_violation_started_at.tzinfo else session.active_violation_started_at.replace(tzinfo=timezone.utc)
        elapsed = (now - v_start).total_seconds()
        if elapsed >= 9.5:
            result = VivaService.finalize_session(session.id, status=SessionStatus.TERMINATED_FOR_VIOLATION)
            session.active_violation_started_at = None
            session.active_violation_type = None
            db.session.commit()
            return jsonify({
                "terminated": True,
                "status": SessionStatus.TERMINATED_FOR_VIOLATION,
                "message": "Your viva was automatically submitted because you did not return within the allowed 10-second period.",
                "result": result.to_dict(include_audits=False),
            }), 200

    return jsonify({
        "terminated": False,
        "session": session.to_dict(),
    }), 200


@student_bp.route("/results", methods=["GET"])
@student_required
def get_my_results():
    """List student's own completed results. Audits are NEVER exposed to student."""
    sessions = VivaSession.query.filter(
        VivaSession.student_id == g.current_user.id,
        VivaSession.status.in_([SessionStatus.COMPLETED, SessionStatus.TIME_EXPIRED, SessionStatus.TERMINATED_FOR_VIOLATION])
    ).order_by(VivaSession.completed_at.desc()).all()

    results_data = []
    for s in sessions:
        if s.result:
            r_data = s.result.to_dict(include_audits=False)
            r_data["viva_title"] = s.viva.title if s.viva else "Viva"
            r_data["status"] = s.status
            r_data["completed_at"] = s.completed_at.isoformat() if s.completed_at else None
            results_data.append(r_data)

    return jsonify({"results": results_data}), 200
