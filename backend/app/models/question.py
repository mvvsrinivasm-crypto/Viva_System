from datetime import datetime, timezone
from app.extensions import db


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    viva_id = db.Column(db.Integer, db.ForeignKey("vivas.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    question_number = db.Column(db.Integer, nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    reference_answer = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session_questions = db.relationship("SessionQuestion", backref="question", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self, include_answer: bool = True) -> dict:
        data = {
            "id": self.id,
            "viva_id": self.viva_id,
            "document_id": self.document_id,
            "question_number": self.question_number,
            "question_text": self.question_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_answer:
            data["reference_answer"] = self.reference_answer
        return data
