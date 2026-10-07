from datetime import datetime, timezone
from app.extensions import db


class ViolationType:
    TAB_SWITCH = "TAB_SWITCH"
    WINDOW_BLUR = "WINDOW_BLUR"
    FULLSCREEN_EXIT = "FULLSCREEN_EXIT"
    COPY_ATTEMPT = "COPY_ATTEMPT"
    PASTE_ATTEMPT = "PASTE_ATTEMPT"
    CUT_ATTEMPT = "CUT_ATTEMPT"
    CONTEXT_MENU_ATTEMPT = "CONTEXT_MENU_ATTEMPT"
    ALL = [
        TAB_SWITCH,
        WINDOW_BLUR,
        FULLSCREEN_EXIT,
        COPY_ATTEMPT,
        PASTE_ATTEMPT,
        CUT_ATTEMPT,
        CONTEXT_MENU_ATTEMPT,
    ]


class Violation(db.Model):
    __tablename__ = "violations"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("viva_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    metadata_json = db.Column("metadata", db.JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "type": self.type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata_json,
        }
