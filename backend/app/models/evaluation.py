from datetime import datetime, timezone
from app.extensions import db


class Evaluation(db.Model):
    __tablename__ = "evaluations"

    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(
        db.Integer,
        db.ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    ai_score = db.Column(db.Float, nullable=False)  # 0.0 to 10.0
    max_score = db.Column(db.Float, default=10.0, nullable=False)
    evaluation_reason = db.Column(db.Text, nullable=True)
    evaluation_json = db.Column(db.JSON, nullable=True)
    evaluated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "answer_id": self.answer_id,
            "ai_score": self.ai_score,
            "max_score": self.max_score,
            "evaluation_reason": self.evaluation_reason,
            "evaluation_json": self.evaluation_json,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }
