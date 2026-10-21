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

    def to_dict(self, include_audits: bool = False, include_questions: bool = True) -> dict:
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

        sess = self.session
        if not sess and self.session_id:
            from app.models.viva_session import VivaSession
            sess = db.session.get(VivaSession, self.session_id)

        if include_questions and sess:
            questions_review = []
            for sq in sorted(sess.session_questions, key=lambda x: x.question_order):
                eval_obj = sq.answer.evaluation if (sq.answer and sq.answer.evaluation) else None
                student_ans = ""
                if sq.answer:
                    student_ans = (sq.answer.edited_transcript or sq.answer.original_asr_transcript or "").strip()
                q_text = sq.question.question_text if sq.question else ""
                ref_ans = sq.question.reference_answer if sq.question else ""
                score = round(eval_obj.ai_score, 2) if eval_obj else 0.0
                reason = eval_obj.evaluation_reason if eval_obj else "No answer submitted."
                improved_ans = (eval_obj.improved_answer if (eval_obj and eval_obj.improved_answer) else ref_ans) or ref_ans

                questions_review.append({
                    "question_order": sq.question_order,
                    "question_text": q_text,
                    "student_answer": student_ans or "No answer provided.",
                    "score": score,
                    "max_score": 10.0,
                    "reason": reason,
                    "improved_answer": improved_ans,
                    "is_counted": sq.question_order in (self.counted_question_1, self.counted_question_2),
                })
            data["questions_review"] = questions_review

        return data
