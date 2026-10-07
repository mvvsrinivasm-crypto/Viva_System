from datetime import datetime, timezone
from app.extensions import db


class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    session_question_id = db.Column(
        db.Integer,
        db.ForeignKey("session_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    audio_path = db.Column(db.String(500), nullable=True)
    original_asr_transcript = db.Column(db.Text, nullable=True)
    edited_transcript = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    evaluation = db.relationship("Evaluation", backref="answer", uselist=False, cascade="all, delete-orphan")

    def to_dict(self, include_evaluation: bool = False) -> dict:
        data = {
            "id": self.id,
            "session_question_id": self.session_question_id,
            "has_audio": bool(self.audio_path),
            "original_asr_transcript": self.original_asr_transcript,
            "edited_transcript": self.edited_transcript,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }
        if include_evaluation and self.evaluation:
            data["evaluation"] = self.evaluation.to_dict()
        else:
            data["evaluation"] = None
        return data
