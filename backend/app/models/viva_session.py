from datetime import datetime, timezone
from app.extensions import db


class SessionStatus:
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    TIME_EXPIRED = "TIME_EXPIRED"
    TERMINATED_FOR_VIOLATION = "TERMINATED_FOR_VIOLATION"
    ABANDONED = "ABANDONED"
    ALL = [IN_PROGRESS, COMPLETED, TIME_EXPIRED, TERMINATED_FOR_VIOLATION, ABANDONED]


class VivaSession(db.Model):
    __tablename__ = "viva_sessions"

    id = db.Column(db.Integer, primary_key=True)
    viva_id = db.Column(db.Integer, db.ForeignKey("vivas.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default=SessionStatus.IN_PROGRESS, nullable=False, index=True)
    active_violation_started_at = db.Column(db.DateTime, nullable=True)
    active_violation_type = db.Column(db.String(50), nullable=True)

    # Relationships
    session_questions = db.relationship(
        "SessionQuestion",
        backref="session",
        lazy="selectin",
        order_by="SessionQuestion.question_order",
        cascade="all, delete-orphan",
    )
    result = db.relationship("Result", backref="session", uselist=False, cascade="all, delete-orphan")
    violations = db.relationship("Violation", backref="session", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        remaining_sec = None
        if self.expires_at:
            now = datetime.now(timezone.utc)
            # handle timezone-aware or naive
            exp = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
            remaining_sec = max(0, int((exp - now).total_seconds()))

        remaining_violation_sec = None
        if self.active_violation_started_at:
            now = datetime.now(timezone.utc)
            v_start = self.active_violation_started_at if self.active_violation_started_at.tzinfo else self.active_violation_started_at.replace(tzinfo=timezone.utc)
            elapsed = (now - v_start).total_seconds()
            remaining_violation_sec = max(0, int(10 - elapsed))

        return {
            "id": self.id,
            "viva_id": self.viva_id,
            "viva_title": self.viva.title if self.viva else None,
            "duration_seconds": self.viva.duration_seconds if self.viva else 120,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "student_email": self.student.email if self.student else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "remaining_seconds": remaining_sec,
            "active_violation_started_at": self.active_violation_started_at.isoformat() if self.active_violation_started_at else None,
            "active_violation_type": self.active_violation_type,
            "remaining_violation_seconds": remaining_violation_sec,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "has_result": self.result is not None,
        }
