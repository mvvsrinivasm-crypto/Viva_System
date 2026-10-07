import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models.user import User, Role
from app.models.viva import Viva
from app.models.viva_session import VivaSession, SessionStatus
from app.models.result import Result
from app.models.violation import Violation
from app.models.mark_audit import MarkAudit
from app.middleware.auth import admin_required
from app.services.viva_service import VivaService

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_all_users():
    """List all registered users with role and status filtering."""
    role_filter = request.args.get("role")
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter.upper())

    users = query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [u.to_dict() for u in users]}), 200


@admin_bp.route("/users/<int:user_id>/status", methods=["PATCH"])
@admin_required
def toggle_user_status(user_id):
    """Activate or deactivate user account."""
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    # Prevent deactivating self
    if user.id == g.current_user.id:
        return jsonify({"error": "Cannot deactivate your own administrator account."}), 400

    data = request.get_json() or {}
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    else:
        user.is_active = not user.is_active

    db.session.commit()
    return jsonify({
        "message": f"User account {'activated' if user.is_active else 'deactivated'} successfully.",
        "user": user.to_dict(),
    }), 200


@admin_bp.route("/vivas", methods=["GET"])
@admin_required
def get_all_vivas():
    """List all vivas in the system."""
    vivas = Viva.query.order_by(Viva.created_at.desc()).all()
    return jsonify({"vivas": [v.to_dict() for v in vivas]}), 200


@admin_bp.route("/vivas/<int:viva_id>", methods=["PUT"])
@admin_required
def update_viva(viva_id):
    """Admin endpoint to update viva duration and details."""
    viva = db.session.get(Viva, viva_id)
    if not viva:
        return jsonify({"error": "Viva not found."}), 404

    data = request.get_json() or {}
    if "title" in data and data["title"].strip():
        viva.title = data["title"].strip()
    if "description" in data:
        viva.description = data["description"].strip()
    if "status" in data and data["status"] in VivaStatus.ALL:
        viva.status = data["status"]

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


@admin_bp.route("/results", methods=["GET"])
@admin_required
def get_all_results():
    """
    List all student viva results with complete details and audit indicators.
    ADMIN ONLY.
    """
    results = Result.query.join(VivaSession).order_by(Result.finalized_at.desc()).all()

    items = []
    for r in results:
        session = r.session
        audit_count = r.audits.count()
        item = {
            "result_id": r.id,
            "session_id": session.id,
            "student_id": session.student_id,
            "student_name": session.student.name if session.student else "Student",
            "student_email": session.student.email if session.student else "",
            "student_reg_no": session.student.registration_number if session.student else "",
            "viva_id": session.viva_id,
            "viva_title": session.viva.title if session.viva else "Viva",
            "status": session.status,
            "q1_score": round(r.q1_score, 2),
            "q2_score": round(r.q2_score, 2),
            "q3_score": round(r.q3_score, 2),
            "counted_question_1": r.counted_question_1,
            "counted_question_2": r.counted_question_2,
            "final_score": round(r.final_score, 2),
            "max_score": r.max_score,
            "finalized_at": r.finalized_at.isoformat() if r.finalized_at else None,
            "has_been_edited": audit_count > 0,
            "audit_count": audit_count,
        }
        items.append(item)

    return jsonify({"results": items}), 200


@admin_bp.route("/results/<int:result_id>", methods=["PATCH"])
@admin_required
def edit_student_mark(result_id):
    """
    ADMIN ONLY. Edit a student's final score.
    Creates an immutable MarkAudit entry.
    Requires new_score and reason.
    """
    data = request.get_json() or {}
    new_score = data.get("new_score")
    reason = (data.get("reason") or "").strip()

    if new_score is None:
        return jsonify({"error": "new_score is required."}), 400

    if not reason:
        return jsonify({"error": "A mandatory reason must be provided when modifying student marks."}), 400

    try:
        new_score_float = float(new_score)
    except (ValueError, TypeError):
        return jsonify({"error": "new_score must be a valid number between 0 and 20."}), 400

    try:
        audit = VivaService.admin_edit_mark(
            result_id=result_id,
            new_score=new_score_float,
            admin_id=g.current_user.id,
            reason=reason,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    result = db.session.get(Result, result_id)
    return jsonify({
        "message": "Student mark modified successfully. Immutable audit log recorded.",
        "result": result.to_dict(include_audits=True),
        "audit": audit.to_dict(),
    }), 200


@admin_bp.route("/results/<int:result_id>", methods=["DELETE"])
@admin_required
def delete_student_viva_record(result_id):
    """
    ADMIN ONLY.
    Transactionally deletes a student's viva attempt and result record so that the student
    can re-attend the viva assessment.
    Logs an immutable audit log entry in MarkAudit.
    """
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()

    try:
        details = VivaService.admin_delete_viva_record(
            result_id=result_id,
            admin_id=g.current_user.id,
            reason=reason,
        )
        return jsonify({
            "message": "Viva record deleted successfully. The student can attend this viva again.",
            "details": details,
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error("Error deleting viva record: %s", e)
        return jsonify({"error": "Failed to delete viva record."}), 500


@admin_bp.route("/audits", methods=["GET"])
@admin_required
def get_mark_audits():
    """
    ADMIN ONLY. Complete audit history of all mark edits.
    Returns: original score, edited score, edited by, reason, timestamp.
    """
    audits = MarkAudit.query.order_by(MarkAudit.created_at.desc()).all()
    return jsonify({"audits": [a.to_dict() for a in audits]}), 200


@admin_bp.route("/violations", methods=["GET"])
@admin_required
def get_all_violations():
    """View anti-cheating violations across all sessions."""
    violations = Violation.query.order_by(Violation.timestamp.desc()).limit(100).all()
    return jsonify({"violations": [v.to_dict() for v in violations]}), 200


@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_system_stats():
    """Overall statistics for Admin Dashboard."""
    total_users = User.query.count()
    total_students = User.query.filter_by(role=Role.STUDENT).count()
    total_faculty = User.query.filter_by(role=Role.FACULTY).count()
    total_vivas = Viva.query.count()
    total_sessions = VivaSession.query.count()
    completed_sessions = VivaSession.query.filter_by(status=SessionStatus.COMPLETED).count()
    total_audits = MarkAudit.query.count()
    total_violations = Violation.query.count()

    return jsonify({
        "total_users": total_users,
        "total_students": total_students,
        "total_faculty": total_faculty,
        "total_vivas": total_vivas,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "total_audits": total_audits,
        "total_violations": total_violations,
    }), 200
