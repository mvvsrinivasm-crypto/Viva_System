from app.extensions import db


class SessionQuestion(db.Model):
    __tablename__ = "session_questions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("viva_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_order = db.Column(db.Integer, nullable=False)  # 1, 2, or 3

    # Relationship to answer (one-to-one per question in session)
    answer = db.relationship("Answer", backref="session_question", uselist=False, cascade="all, delete-orphan")

    def to_dict(self, include_answer: bool = False, include_evaluation: bool = False) -> dict:
        data = {
            "id": self.id,
            "session_id": self.session_id,
            "question_id": self.question_id,
            "question_order": self.question_order,
            "question_text": self.question.question_text if self.question else None,
        }
        if include_answer and self.question:
            data["reference_answer"] = self.question.reference_answer

        if self.answer:
            data["answer"] = self.answer.to_dict(include_evaluation=include_evaluation)
        else:
            data["answer"] = None

        return data
