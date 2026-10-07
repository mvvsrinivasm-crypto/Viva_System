from datetime import datetime, timezone
from app.extensions import db


class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("viva_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    q1_score = db.Column(db.Float, default=0.0, nullable=False)
    q2_score = db.Column(db.Float, default=0.0, nullable=False)
    q3_score = db.Column(db.Float, default=0.0, nullable=False)
    counted_question_1 = db.Column(db.Integer, nullable=True)  # Order of first best question (1, 2, or 3)
    counted_question_2 = db.Column(db.Integer, nullable=True)  # Order of second best question (1, 2, or 3)
    final_score = db.Column(db.Float, nullable=False)  # Best 2 of 3 (Max 20.0)
    max_score = db.Column(db.Float, default=20.0, nullable=False)  # Fixed at 20.0
    finalized_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    audits = db.relationship("MarkAudit", backref="result", lazy="dynamic", order_by="MarkAudit.created_at.desc()")

    def to_dict(self, include_audits: bool = False) -> dict:
        data = {
            "id": self.id,
            "session_id": self.session_id,
            "q1_score": round(self.q1_score, 2),
            "q2_score": round(self.q2_score, 2),
            "q3_score": round(self.q3_score, 2),
            "counted_question_1": self.counted_question_1,
            "counted_question_2": self.counted_question_2,
            "final_score": round(self.final_score, 2),
            "max_score": self.max_score,
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
        }
        if include_audits:
            data["audits"] = [audit.to_dict() for audit in self.audits.all()]
        return data
