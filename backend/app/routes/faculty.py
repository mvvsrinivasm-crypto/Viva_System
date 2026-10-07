import io
import re
from datetime import datetime, timezone
from pathlib import Path
import os
import uuid
from flask import Blueprint, request, jsonify, g, current_app, send_file
from werkzeug.utils import secure_filename
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.models.user import User, Role
from app.models.viva import Viva, VivaStatus
from app.models.document import Document
from app.models.question import Question
from app.models.viva_session import VivaSession, SessionStatus
from app.models.session_question import SessionQuestion
from app.models.answer import Answer
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.middleware.auth import faculty_required
from app.services.pdf_service import PDFService, PDFExtractionError

faculty_bp = Blueprint("faculty", __name__, url_prefix="/api/faculty")


@faculty_bp.route("/students", methods=["GET"])
@faculty_required
def get_faculty_students():
    """
    List all university students with evaluated viva marks, attendance, and details.
    Allows faculty to inspect each student's evaluated viva scores directly in the student directory.
    """
    students = User.query.filter_by(role=Role.STUDENT).order_by(User.name.asc()).all()

    # Get vivas owned by the logged-in faculty
    faculty_vivas = Viva.query.filter_by(faculty_id=g.current_user.id).all()
    fac_viva_ids = [v.id for v in faculty_vivas]
    viva_map = {v.id: v for v in faculty_vivas}

    sessions = []
    if fac_viva_ids:
        sessions = (
            VivaSession.query.filter(VivaSession.viva_id.in_(fac_viva_ids))
            .options(
                selectinload(VivaSession.result),
                selectinload(VivaSession.session_questions).selectinload(SessionQuestion.question),
                selectinload(VivaSession.session_questions)
                .selectinload(SessionQuestion.answer)
                .selectinload(Answer.evaluation),
            )
            .order_by(VivaSession.started_at.desc())
            .all()
        )

    sessions_by_student = {}
    for s in sessions:
        sessions_by_student.setdefault(s.student_id, []).append(s)

    students_data = []
    for st in students:
        st_sessions = sessions_by_student.get(st.id, [])
        viva_history = []
        vivas_seen = set()
        completed_scores = []

        for s in st_sessions:
            if s.viva_id in vivas_seen:
                continue
            all_viva_attempts = [att for att in st_sessions if att.viva_id == s.viva_id]
            comp_attempts = [
                att for att in all_viva_attempts
                if att.status == SessionStatus.COMPLETED and att.result
            ]
            best_att = (
                max(comp_attempts, key=lambda a: a.result.final_score)
                if comp_attempts
                else all_viva_attempts[0]
            )
            vivas_seen.add(s.viva_id)

            v_obj = viva_map.get(s.viva_id)
            score = best_att.result.final_score if best_att.result else None
            if score is not None and best_att.status == SessionStatus.COMPLETED:
                completed_scores.append(score)

            q_list = []
            for sq in best_att.session_questions:
                q_list.append({
                    "order": sq.question_order,
                    "question_text": sq.question.question_text if sq.question else "",
                    "reference_answer": sq.question.reference_answer if sq.question else "",
                    "transcript": sq.answer.edited_transcript if sq.answer else None,
                    "score": sq.answer.evaluation.ai_score if sq.answer and sq.answer.evaluation else None,
                    "reason": sq.answer.evaluation.evaluation_reason if sq.answer and sq.answer.evaluation else None,
                })

            viva_history.append({
                "viva_id": s.viva_id,
                "viva_title": v_obj.title if v_obj else f"Viva #{s.viva_id}",
                "session_id": best_att.id,
                "status": best_att.status,
                "final_score": score,
                "max_score": 20.0,
                "q1_score": best_att.result.q1_score if best_att.result else None,
                "q2_score": best_att.result.q2_score if best_att.result else None,
                "q3_score": best_att.result.q3_score if best_att.result else None,
                "completed_at": best_att.completed_at.isoformat() if best_att.completed_at else None,
                "started_at": best_att.started_at.isoformat() if best_att.started_at else None,
                "total_attempts": len(all_viva_attempts),
                "questions": q_list,
            })

        st_dict = st.to_dict()
        st_dict["vivas"] = viva_history
        st_dict["completed_vivas_count"] = len(completed_scores)
        st_dict["latest_score"] = (
            viva_history[0]["final_score"]
            if viva_history and viva_history[0]["final_score"] is not None
            else None
        )
        st_dict["average_score"] = (
            round(sum(completed_scores) / len(completed_scores), 1)
            if completed_scores
            else None
        )
        students_data.append(st_dict)

    return jsonify({"students": students_data}), 200


@faculty_bp.route("/vivas", methods=["GET"])
@faculty_required
def get_faculty_vivas():
    """List all vivas managed by current faculty."""
    vivas = Viva.query.filter_by(faculty_id=g.current_user.id).order_by(Viva.created_at.desc()).all()
    return jsonify({"vivas": [v.to_dict() for v in vivas]}), 200


@faculty_bp.route("/vivas", methods=["POST"])
@faculty_required
def create_viva():
    """Create a new viva assessment container."""
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()

    if not title:
        return jsonify({"error": "Viva title is required."}), 400

    # Total viva session timer configuration
    duration_minutes = data.get("duration_minutes")
    if duration_minutes is not None:
        try:
            duration_seconds = max(30, int(float(duration_minutes) * 60))
        except (ValueError, TypeError):
            duration_seconds = 120
    else:
        try:
            duration_seconds = int(data.get("duration_seconds", 120))
        except (ValueError, TypeError):
            duration_seconds = 120

    viva = Viva(
        title=title,
        description=description,
        faculty_id=g.current_user.id,
        status=VivaStatus.DRAFT,
        question_count=0,
        duration_seconds=duration_seconds,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(viva)
    db.session.commit()

    return jsonify({
        "message": "Viva created successfully.",
        "viva": viva.to_dict(),
    }), 201


@faculty_bp.route("/vivas/<int:viva_id>", methods=["PUT"])
@faculty_required
def update_viva(viva_id):
    """Update viva metadata and session duration."""
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found."}), 404

    data = request.get_json() or {}
    if "title" in data and data["title"].strip():
        viva.title = data["title"].strip()
    if "description" in data:
        viva.description = data["description"].strip()

    if "duration_minutes" in data:
        try:
            viva.duration_seconds = max(30, int(float(data["duration_minutes"]) * 60))
        except (ValueError, TypeError):
            pass
    elif "duration_seconds" in data:
        try:
            viva.duration_seconds = max(30, int(data["duration_seconds"]))
        except (ValueError, TypeError):
            pass

    db.session.commit()
    return jsonify({
        "message": "Viva updated successfully.",
        "viva": viva.to_dict(),
    }), 200


@faculty_bp.route("/vivas/<int:viva_id>", methods=["GET"])
@faculty_required
def get_viva_details(viva_id):
    """Get single viva details."""
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found."}), 404

    data = viva.to_dict()
    data["documents"] = [doc.to_dict() for doc in viva.documents.all()]
    return jsonify({"viva": data}), 200


@faculty_bp.route("/vivas/<int:viva_id>/upload", methods=["POST"])
@faculty_required
def upload_pdf(viva_id):
    """
    Upload PDF question bank.
    Uses PyMuPDF to extract questions and reference answers.
    STRICT RULE: The PDF is the ONLY source of questions. No LLM generation.
    If questions lack reference answers, returns validation failure.
    """
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found."}), 404

    if "file" not in request.files:
        return jsonify({"error": "No PDF file attached."}), 400

    pdf_file = request.files["file"]
    if not pdf_file or pdf_file.filename == "":
        return jsonify({"error": "Empty file name."}), 400

    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    file_bytes = pdf_file.read()
    if len(file_bytes) == 0:
        return jsonify({"error": "Uploaded file is 0 bytes."}), 400

    # 1. Parse Q&A pairs strictly from PDF text via PyMuPDF
    try:
        raw_text = PDFService.extract_text_from_pdf(file_bytes)
        parsed = PDFService.parse_qa_pairs(raw_text)
    except PDFExtractionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF document: {str(e)}"}), 500

    # 2. Save document to disk
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_hash = PDFService.calculate_file_hash(file_bytes)
    safe_name = f"viva_{viva.id}_{uuid.uuid4().hex[:8]}_{secure_filename(pdf_file.filename)}"
    storage_path = upload_dir / safe_name
    storage_path.write_bytes(file_bytes)

    # 3. Create or replace Document record
    # If there was a previous document for this draft viva, remove old questions
    existing_doc = viva.documents.first()
    if existing_doc:
        Question.query.filter_by(viva_id=viva.id).delete()
        db.session.delete(existing_doc)
        db.session.flush()

    doc = Document(
        viva_id=viva.id,
        uploaded_by=g.current_user.id,
        file_name=pdf_file.filename,
        file_hash=file_hash,
        storage_path=str(storage_path),
        uploaded_at=datetime.now(timezone.utc),
    )
    db.session.add(doc)
    db.session.flush()

    # 4. Insert valid questions into PostgreSQL
    for q_data in parsed["questions"]:
        question = Question(
            viva_id=viva.id,
            document_id=doc.id,
            question_number=q_data["question_number"],
            question_text=q_data["question_text"],
            reference_answer=q_data["reference_answer"],
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(question)

    viva.question_count = parsed["valid_count"]
    db.session.commit()

    return jsonify({
        "message": "PDF processed successfully.",
        "validation_passed": parsed["validation_passed"],
        "validation_message": parsed["validation_message"],
        "total_detected": parsed["total_detected"],
        "valid_count": parsed["valid_count"],
        "invalid_count": parsed["invalid_count"],
        "questions": parsed["questions"],
        "invalid_questions": parsed["invalid_questions"],
    }), 200


@faculty_bp.route("/vivas/<int:viva_id>/questions", methods=["GET"])
@faculty_required
def get_viva_questions(viva_id):
    """Get all extracted questions and reference answers for review."""
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found."}), 404

    questions = Question.query.filter_by(viva_id=viva.id).order_by(Question.question_number).all()
    return jsonify({
        "viva_id": viva.id,
        "question_count": len(questions),
        "questions": [q.to_dict(include_answer=True) for q in questions],
    }), 200


@faculty_bp.route("/vivas/<int:viva_id>/publish", methods=["POST"])
@faculty_required
def publish_viva(viva_id):
    """
    Publish question bank.
    Must have at least 3 valid questions.
    """
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found."}), 404

    questions = Question.query.filter_by(viva_id=viva.id).all()
    if len(questions) < 3:
        return jsonify({
            "error": f"Cannot publish: Viva has only {len(questions)} valid questions. A minimum of 3 is required.",
        }), 400

    viva.status = VivaStatus.PUBLISHED
    viva.published_at = datetime.now(timezone.utc)
    viva.question_count = len(questions)
    db.session.commit()

    return jsonify({
        "message": "Viva question bank successfully published.",
        "viva": viva.to_dict(),
    }), 200


@faculty_bp.route("/vivas/<int:viva_id>/status", methods=["PATCH"])
@faculty_required
def update_viva_status(viva_id):
    """Toggle viva active / inactive."""
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found."}), 404

    data = request.get_json() or {}
    new_status = (data.get("status") or "").strip().upper()

    if new_status not in (VivaStatus.ACTIVE, VivaStatus.INACTIVE, VivaStatus.PUBLISHED):
        return jsonify({"error": "Invalid status value."}), 400

    viva.status = new_status
    db.session.commit()

    return jsonify({
        "message": f"Viva status updated to {new_status}.",
        "viva": viva.to_dict(),
    }), 200


@faculty_bp.route("/vivas/<int:viva_id>/students", methods=["GET"])
@faculty_required
def get_attended_students(viva_id):
    """View students who attended this viva session with evaluated marks and attendance details."""
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found."}), 404

    sessions = (
        VivaSession.query.filter_by(viva_id=viva.id)
        .options(
            selectinload(VivaSession.student),
            selectinload(VivaSession.result),
            selectinload(VivaSession.session_questions).selectinload(SessionQuestion.question),
        )
        .order_by(VivaSession.started_at.desc())
        .all()
    )

    attendees = []
    for s in sessions:
        attendees.append({
            "session_id": s.id,
            "viva_id": s.viva_id,
            "student_id": s.student_id,
            "student_name": s.student.name if s.student else "Student",
            "student_email": s.student.email if s.student else "",
            "student_reg_no": s.student.registration_number if s.student else "",
            "department": s.student.department if s.student else "",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "status": s.status,
            "final_score": s.result.final_score if s.result else None,
            "max_score": 20.0,
            "q1_score": s.result.q1_score if s.result else None,
            "q2_score": s.result.q2_score if s.result else None,
            "q3_score": s.result.q3_score if s.result else None,
        })

    return jsonify({
        "viva_id": viva.id,
        "viva_title": viva.title,
        "total_attended": len(attendees),
        "students": attendees,
    }), 200


@faculty_bp.route("/vivas/<int:viva_id>/results", methods=["GET"])
@faculty_required
def get_viva_results(viva_id):
    """
    View attendance, final marks, question-wise scores, submitted transcripts, and AI evaluations.
    CRITICAL: Does NOT include audit records (audits are ADMIN ONLY).
    Returns both student-wise evaluated marks (student_summaries) and full chronological attempt records (results).
    """
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found."}), 404

    # Auto-expire/abandon any abandoned in-progress sessions past their expiration
    now = datetime.now(timezone.utc)
    stale_in_prog = VivaSession.query.filter_by(viva_id=viva.id, status=SessionStatus.IN_PROGRESS).all()
    dirty = False
    for s in stale_in_prog:
        exp = s.expires_at if (s.expires_at and s.expires_at.tzinfo) else (s.expires_at.replace(tzinfo=timezone.utc) if s.expires_at else None)
        if exp and exp < now:
            ans_cnt = sum(1 for sq in s.session_questions if sq.answer is not None)
            s.status = SessionStatus.ABANDONED if ans_cnt == 0 else SessionStatus.TIME_EXPIRED
            dirty = True
    if dirty:
        db.session.commit()

    # Query all sessions ordered newest first with optimized eager loading
    sessions = (
        VivaSession.query.filter_by(viva_id=viva.id)
        .options(
            selectinload(VivaSession.student),
            selectinload(VivaSession.result),
            selectinload(VivaSession.session_questions).selectinload(SessionQuestion.question),
            selectinload(VivaSession.session_questions)
            .selectinload(SessionQuestion.answer)
            .selectinload(Answer.evaluation),
        )
        .order_by(VivaSession.started_at.desc())
        .all()
    )

    results_list = []
    student_groups = {}

    for s in sessions:
        student_groups.setdefault(s.student_id, []).append(s)

        q_list = []
        for sq in s.session_questions:
            q_list.append({
                "order": sq.question_order,
                "question_text": sq.question.question_text if sq.question else "",
                "reference_answer": sq.question.reference_answer if sq.question else "",
                "transcript": sq.answer.edited_transcript if sq.answer else None,
                "score": sq.answer.evaluation.ai_score if sq.answer and sq.answer.evaluation else None,
                "reason": sq.answer.evaluation.evaluation_reason if sq.answer and sq.answer.evaluation else None,
            })

        item = {
            "session_id": s.id,
            "viva_id": s.viva_id,
            "viva_title": viva.title,
            "student_id": s.student_id,
            "student_name": s.student.name if s.student else "Student",
            "student_email": s.student.email if s.student else "",
            "student_reg_no": s.student.registration_number if s.student else "",
            "department": s.student.department if s.student else "",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "status": s.status,
            "final_score": s.result.final_score if s.result else None,
            "max_score": 20.0,
            "q1_score": s.result.q1_score if s.result else None,
            "q2_score": s.result.q2_score if s.result else None,
            "q3_score": s.result.q3_score if s.result else None,
            "questions": q_list,
        }
        results_list.append(item)

    # Build canonical student-level summaries (one row per student, choosing best/latest evaluated attempt)
    student_summaries = []
    for st_id, st_sessions in student_groups.items():
        comp_attempts = [
            s for s in st_sessions
            if s.status == SessionStatus.COMPLETED and s.result is not None
        ]
        if comp_attempts:
            best_session = max(comp_attempts, key=lambda s: s.result.final_score)
        else:
            scored = [s for s in st_sessions if s.result is not None]
            if scored:
                best_session = max(scored, key=lambda s: s.result.final_score)
            else:
                best_session = st_sessions[0]

        student = best_session.student
        best_questions = []
        for sq in best_session.session_questions:
            best_questions.append({
                "order": sq.question_order,
                "question_text": sq.question.question_text if sq.question else "",
                "reference_answer": sq.question.reference_answer if sq.question else "",
                "transcript": sq.answer.edited_transcript if sq.answer else None,
                "score": sq.answer.evaluation.ai_score if sq.answer and sq.answer.evaluation else None,
                "reason": sq.answer.evaluation.evaluation_reason if sq.answer and sq.answer.evaluation else None,
            })

        student_summaries.append({
            "student_id": st_id,
            "student_name": student.name if student else "Student",
            "student_email": student.email if student else "",
            "student_reg_no": student.registration_number if student else "",
            "department": student.department if student else "",
            "session_id": best_session.id,
            "status": best_session.status,
            "final_score": best_session.result.final_score if best_session.result else None,
            "max_score": 20.0,
            "q1_score": best_session.result.q1_score if best_session.result else None,
            "q2_score": best_session.result.q2_score if best_session.result else None,
            "q3_score": best_session.result.q3_score if best_session.result else None,
            "started_at": best_session.started_at.isoformat() if best_session.started_at else None,
            "completed_at": best_session.completed_at.isoformat() if best_session.completed_at else None,
            "total_attempts": len(st_sessions),
            "has_completed": len(comp_attempts) > 0,
            "questions": best_questions,
        })

    # Sort student summaries: completed/highest score first, then alphabetically
    student_summaries.sort(
        key=lambda item: (
            0 if item["status"] == SessionStatus.COMPLETED else 1,
            -(item["final_score"] or 0),
            item["student_name"],
        )
    )

    completed_students = [item for item in student_summaries if item["status"] == SessionStatus.COMPLETED and item["final_score"] is not None]
    avg_score = round(sum(item["final_score"] for item in completed_students) / len(completed_students), 1) if completed_students else 0.0
    highest_score = max((item["final_score"] for item in completed_students), default=0.0) if completed_students else 0.0

    return jsonify({
        "viva_id": viva.id,
        "viva_title": viva.title,
        "student_summaries": student_summaries,
        "results": results_list,
        "stats": {
            "total_attended_students": len(student_summaries),
            "total_completed_students": len(completed_students),
            "average_score": avg_score,
            "highest_score": highest_score,
            "total_sessions": len(results_list),
        },
    }), 200


@faculty_bp.route("/results", methods=["GET"])
@faculty_required
def get_faculty_all_results():
    """
    List student marks/results across all vivas owned by the logged-in faculty.
    Supports optional query param ?viva_id=<id> for filtering.
    Excludes admin audit records.
    Returns student_summaries and results sorted newest first.
    """
    viva_id = request.args.get("viva_id", type=int)
    faculty_vivas = Viva.query.filter_by(faculty_id=g.current_user.id).order_by(Viva.created_at.desc()).all()
    viva_options = [{"id": v.id, "title": v.title, "status": v.status} for v in faculty_vivas]

    if viva_id:
        target_viva_ids = [v.id for v in faculty_vivas if v.id == viva_id]
    else:
        target_viva_ids = [v.id for v in faculty_vivas]

    if not target_viva_ids:
        return jsonify({
            "vivas": viva_options,
            "selected_viva_id": viva_id,
            "student_summaries": [],
            "results": [],
            "stats": {"total_attended_students": 0, "total_completed_students": 0, "average_score": 0.0, "highest_score": 0.0, "total_sessions": 0},
        }), 200

    sessions = (
        VivaSession.query.filter(VivaSession.viva_id.in_(target_viva_ids))
        .options(
            selectinload(VivaSession.student),
            selectinload(VivaSession.result),
            selectinload(VivaSession.viva),
            selectinload(VivaSession.session_questions).selectinload(SessionQuestion.question),
            selectinload(VivaSession.session_questions)
            .selectinload(SessionQuestion.answer)
            .selectinload(Answer.evaluation),
        )
        .order_by(VivaSession.started_at.desc())
        .all()
    )

    results_list = []
    student_viva_groups = {}

    for s in sessions:
        key = (s.student_id, s.viva_id)
        student_viva_groups.setdefault(key, []).append(s)

        q_list = [
            {
                "order": sq.question_order,
                "question_text": sq.question.question_text if sq.question else "",
                "reference_answer": sq.question.reference_answer if sq.question else "",
                "transcript": sq.answer.edited_transcript if sq.answer else None,
                "score": sq.answer.evaluation.ai_score if sq.answer and sq.answer.evaluation else None,
                "reason": sq.answer.evaluation.evaluation_reason if sq.answer and sq.answer.evaluation else None,
            }
            for sq in s.session_questions
        ]

        results_list.append({
            "session_id": s.id,
            "viva_id": s.viva_id,
            "viva_title": s.viva.title if s.viva else "Viva",
            "student_id": s.student_id,
            "student_name": s.student.name if s.student else "Student",
            "student_email": s.student.email if s.student else "",
            "student_reg_no": s.student.registration_number if s.student else "",
            "department": s.student.department if s.student else "",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "status": s.status,
            "final_score": s.result.final_score if s.result else None,
            "max_score": 20.0,
            "q1_score": s.result.q1_score if s.result else None,
            "q2_score": s.result.q2_score if s.result else None,
            "q3_score": s.result.q3_score if s.result else None,
            "questions": q_list,
        })

    # Build canonical student summaries per viva
    student_summaries = []
    for (st_id, v_id), st_sessions in student_viva_groups.items():
        comp_attempts = [
            s for s in st_sessions
            if s.status == SessionStatus.COMPLETED and s.result is not None
        ]
        if comp_attempts:
            best_session = max(comp_attempts, key=lambda s: s.result.final_score)
        else:
            scored = [s for s in st_sessions if s.result is not None]
            if scored:
                best_session = max(scored, key=lambda s: s.result.final_score)
            else:
                best_session = st_sessions[0]

        student = best_session.student
        best_questions = [
            {
                "order": sq.question_order,
                "question_text": sq.question.question_text if sq.question else "",
                "reference_answer": sq.question.reference_answer if sq.question else "",
                "transcript": sq.answer.edited_transcript if sq.answer else None,
                "score": sq.answer.evaluation.ai_score if sq.answer and sq.answer.evaluation else None,
                "reason": sq.answer.evaluation.evaluation_reason if sq.answer and sq.answer.evaluation else None,
            }
            for sq in best_session.session_questions
        ]

        student_summaries.append({
            "student_id": st_id,
            "student_name": student.name if student else "Student",
            "student_email": student.email if student else "",
            "student_reg_no": student.registration_number if student else "",
            "department": student.department if student else "",
            "viva_id": v_id,
            "viva_title": best_session.viva.title if best_session.viva else f"Viva #{v_id}",
            "session_id": best_session.id,
            "status": best_session.status,
            "final_score": best_session.result.final_score if best_session.result else None,
            "max_score": 20.0,
            "q1_score": best_session.result.q1_score if best_session.result else None,
            "q2_score": best_session.result.q2_score if best_session.result else None,
            "q3_score": best_session.result.q3_score if best_session.result else None,
            "started_at": best_session.started_at.isoformat() if best_session.started_at else None,
            "completed_at": best_session.completed_at.isoformat() if best_session.completed_at else None,
            "total_attempts": len(st_sessions),
            "has_completed": len(comp_attempts) > 0,
            "questions": best_questions,
        })

    student_summaries.sort(
        key=lambda item: (
            0 if item["status"] == SessionStatus.COMPLETED else 1,
            -(item["final_score"] or 0),
            item["student_name"],
        )
    )

    completed_students = [item for item in student_summaries if item["status"] == SessionStatus.COMPLETED and item["final_score"] is not None]
    avg_score = round(sum(item["final_score"] for item in completed_students) / len(completed_students), 1) if completed_students else 0.0
    highest_score = max((item["final_score"] for item in completed_students), default=0.0) if completed_students else 0.0

    return jsonify({
        "vivas": viva_options,
        "selected_viva_id": viva_id,
        "student_summaries": student_summaries,
        "results": results_list,
        "stats": {
            "total_attended_students": len(student_summaries),
            "total_completed_students": len(completed_students),
            "average_score": avg_score,
            "highest_score": highest_score,
            "total_sessions": len(results_list),
        },
    }), 200


@faculty_bp.route("/vivas/<int:viva_id>/results/export", methods=["GET"])
@faculty_required
def export_viva_results(viva_id):
    """
    Generate and download student marks report as Excel (.xlsx) file.
    Security: Authenticated faculty must own the viva (or admin).
    Excludes admin-only audit records.
    """
    viva = db.session.get(Viva, viva_id)
    if not viva or viva.faculty_id != g.current_user.id:
        return jsonify({"error": "Viva not found or access denied."}), 404

    sessions = (
        VivaSession.query.filter_by(viva_id=viva.id)
        .options(
            selectinload(VivaSession.student),
            selectinload(VivaSession.result),
        )
        .order_by(VivaSession.started_at.desc())
        .all()
    )

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Student Marks"

        # University Header Banner
        ws.merge_cells("A1:L1")
        title_cell = ws["A1"]
        title_cell.value = f"Kalasalingam Academy of Research and Education — {viva.title} — Marks Sheet"
        title_cell.font = Font(name="Calibri", size=13, bold=True, color="1E3A8A")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.merge_cells("A2:L2")
        sub_cell = ws["A2"]
        sub_cell.value = f"Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | Best 2 of 3 Questions (Maximum 20.0 Marks)"
        sub_cell.font = Font(name="Calibri", size=10, italic=True, color="475569")
        sub_cell.alignment = Alignment(horizontal="center", vertical="center")

        headers = [
            "Viva Name",
            "Student Name",
            "Register Number",
            "Institutional Email",
            "Question 1 Score",
            "Question 2 Score",
            "Question 3 Score",
            "Best 2 Score",
            "Maximum Score",
            "Status",
            "Viva Date",
            "Completed At",
        ]
        ws.append([])  # blank row 3
        ws.append(headers)  # row 4

        header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=4, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        row_idx = 5
        for s in sessions:
            q1 = s.result.q1_score if s.result else 0.0
            q2 = s.result.q2_score if s.result else 0.0
            q3 = s.result.q3_score if s.result else 0.0
            final = s.result.final_score if s.result else 0.0
            viva_date = s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "-"
            comp_date = s.completed_at.strftime("%Y-%m-%d %H:%M") if s.completed_at else "-"

            row_data = [
                viva.title,
                s.student.name if s.student else "Student",
                s.student.registration_number if s.student else "",
                s.student.email if s.student else "",
                q1,
                q2,
                q3,
                final,
                20.0,
                s.status,
                viva_date,
                comp_date,
            ]
            ws.append(row_data)

            for c_idx in range(1, len(row_data) + 1):
                c = ws.cell(row=row_idx, column=c_idx)
                c.border = thin_border
                if c_idx in (5, 6, 7, 8, 9):
                    c.alignment = Alignment(horizontal="center")
            row_idx += 1

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "_", viva.title).strip("_")
        filename = f"{sanitized}_Marks.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        # Fallback to CSV if any openpyxl issue arises
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for s in sessions:
            q1 = s.result.q1_score if s.result else 0.0
            q2 = s.result.q2_score if s.result else 0.0
            q3 = s.result.q3_score if s.result else 0.0
            final = s.result.final_score if s.result else 0.0
            writer.writerow([
                viva.title,
                s.student.name if s.student else "Student",
                s.student.registration_number if s.student else "",
                s.student.email if s.student else "",
                q1, q2, q3, final, 20.0,
                s.status,
                s.started_at.isoformat() if s.started_at else "",
                s.completed_at.isoformat() if s.completed_at else "",
            ])
        mem = io.BytesIO(output.getvalue().encode("utf-8"))
        sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "_", viva.title).strip("_")
        return send_file(
            mem,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{sanitized}_Marks.csv",
        )
