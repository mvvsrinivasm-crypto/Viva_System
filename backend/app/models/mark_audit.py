from datetime import datetime, timezone
from app.extensions import db


class MarkAudit(db.Model):
    __tablename__ = "mark_audits"

    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey("results.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(50), default="EDIT_MARK", nullable=False)
    viva_title = db.Column(db.String(255), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_score = db.Column(db.Float, nullable=False)
    edited_score = db.Column(db.Float, nullable=False)
    edited_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship("User", foreign_keys=[student_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "result_id": self.result_id,
            "action": self.action,
            "viva_title": self.viva_title or (self.result.session.viva.title if self.result and self.result.session and self.result.session.viva else "Viva Assessment"),
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "original_score": round(self.original_score, 2),
            "edited_score": round(self.edited_score, 2),
            "edited_by_id": self.edited_by,
            "edited_by_name": self.editor.name if self.editor else "Admin",
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
