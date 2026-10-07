import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
from app.extensions import db
from app.models.viva import Viva, VivaStatus
from app.models.question import Question
from app.models.viva_session import VivaSession, SessionStatus
from app.models.session_question import SessionQuestion
from app.models.answer import Answer
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.models.mark_audit import MarkAudit
from app.models.violation import Violation
from app.services.llm_service import LLMEvaluationService


class VivaService:
    @staticmethod
    def start_student_session(student_id: int, viva_id: int) -> VivaSession:
        """
        Starts a viva session for a student.
        Selects exactly 3 questions from the stored question bank.
        NEVER generates questions with an LLM.
        """
        viva = db.session.get(Viva, viva_id)
        if not viva:
            raise ValueError("Viva does not exist.")

        if viva.status not in (VivaStatus.PUBLISHED, VivaStatus.ACTIVE):
            raise ValueError("This viva is not currently active for participation.")

        # Check if student already has a completed or in-progress session
        existing_session = VivaSession.query.filter_by(
            viva_id=viva_id,
            student_id=student_id,
        ).order_by(VivaSession.started_at.desc()).first()

        if existing_session and existing_session.status == SessionStatus.IN_PROGRESS:
            if existing_session.expires_at is None:
                duration_sec = viva.duration_seconds if viva.duration_seconds else 120
                st = existing_session.started_at
                if st and st.tzinfo is None:
                    st = st.replace(tzinfo=timezone.utc)
                elif not st:
                    st = datetime.now(timezone.utc)
                existing_session.expires_at = st + timedelta(seconds=duration_sec)
                db.session.commit()
            return existing_session

        if existing_session and existing_session.status == SessionStatus.COMPLETED:
            raise ValueError("You have already completed this viva assessment.")

        # Select exactly 3 questions from the stored question bank
        questions = Question.query.filter_by(viva_id=viva_id).all()
        if len(questions) < 3:
            raise ValueError(f"Insufficient questions in viva question bank ({len(questions)} found, minimum 3 required).")

        # Pick 3 random distinct questions
        selected_questions = random.sample(questions, 3)

        # Create session with authoritative server timer
        duration_sec = viva.duration_seconds if viva.duration_seconds else 120
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=duration_sec)

        session = VivaSession(
            viva_id=viva_id,
            student_id=student_id,
            status=SessionStatus.IN_PROGRESS,
            started_at=now,
            expires_at=expires_at,
        )
        db.session.add(session)
        db.session.flush()

        # Create 3 session questions (orders 1, 2, 3)
        for order, q in enumerate(selected_questions, start=1):
            sq = SessionQuestion(
                session_id=session.id,
                question_id=q.id,
                question_order=order,
            )
            db.session.add(sq)

        db.session.commit()
        return session

    @staticmethod
    def calculate_best_two_of_three(
        q1_score: float,
        q2_score: float,
        q3_score: float,
    ) -> Tuple[float, int, int]:
        """
        Calculates final score using the BEST 2 of 3 questions.
        Maximum final score: 20 marks.
        Never calculates out of 30.
        Calculation strictly in Python code.
        Returns: (final_score, counted_q1, counted_q2)
        """
        # Store (order, score)
        scores = [
            (1, round(float(q1_score), 2)),
            (2, round(float(q2_score), 2)),
            (3, round(float(q3_score), 2)),
        ]

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)

        top1_order, top1_score = scores[0]
        top2_order, top2_score = scores[1]

        final_score = round(top1_score + top2_score, 2)
        # Clamp to max 20.0
        final_score = min(20.0, max(0.0, final_score))

        # Return in sorted order index
        counted_orders = sorted([top1_order, top2_order])
        return final_score, counted_orders[0], counted_orders[1]

    @staticmethod
    def finalize_session(session_id: int, status: str = SessionStatus.COMPLETED) -> Result:
        """
        Finalizes viva session, compiles scores of all 3 questions,
        calculates best 2 of 3, and creates the Result.
        Can mark session as COMPLETED or TIME_EXPIRED.
        """
        session = db.session.get(VivaSession, session_id)
        if not session:
            raise ValueError("Session not found.")

        # Ensure session questions exist
        sqs = SessionQuestion.query.filter_by(session_id=session_id).order_by(SessionQuestion.question_order).all()
        if len(sqs) != 3:
            raise ValueError(f"Session does not have exactly 3 questions ({len(sqs)} found).")

        scores_by_order = {}
        for sq in sqs:
            if not sq.answer:
                # Unanswered question awards 0.0 marks
                scores_by_order[sq.question_order] = 0.0
            elif not sq.answer.evaluation:
                scores_by_order[sq.question_order] = 0.0
            else:
                scores_by_order[sq.question_order] = sq.answer.evaluation.ai_score

        q1_score = scores_by_order.get(1, 0.0)
        q2_score = scores_by_order.get(2, 0.0)
        q3_score = scores_by_order.get(3, 0.0)

        final_score, counted_1, counted_2 = VivaService.calculate_best_two_of_three(
            q1_score, q2_score, q3_score
        )

        existing_result = Result.query.filter_by(session_id=session_id).first()
        if existing_result:
            result = existing_result
            result.q1_score = q1_score
            result.q2_score = q2_score
            result.q3_score = q3_score
            result.counted_question_1 = counted_1
            result.counted_question_2 = counted_2
            result.final_score = final_score
            result.finalized_at = datetime.now(timezone.utc)
        else:
            result = Result(
                session_id=session_id,
                q1_score=q1_score,
                q2_score=q2_score,
                q3_score=q3_score,
                counted_question_1=counted_1,
                counted_question_2=counted_2,
                final_score=final_score,
                max_score=20.0,
                finalized_at=datetime.now(timezone.utc),
            )
            db.session.add(result)

        session.status = status
        session.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return result

    @staticmethod
    def admin_edit_mark(result_id: int, new_score: float, admin_id: int, reason: str) -> MarkAudit:
        """
        ADMIN ONLY. Modifies a student's final score and records an immutable audit log.
        """
        if not reason or not reason.strip():
            raise ValueError("A clear reason is mandatory when modifying student marks.")

        new_score = round(float(new_score), 2)
        if new_score < 0.0 or new_score > 20.0:
            raise ValueError("Mark must be between 0.0 and 20.0.")

        result = db.session.get(Result, result_id)
        if not result:
            raise ValueError("Result not found.")

        session = result.session
        original_score = result.final_score

        # Create immutable audit record
        audit = MarkAudit(
            result_id=result.id,
            student_id=session.student_id,
            original_score=original_score,
            edited_score=new_score,
            edited_by=admin_id,
            reason=reason.strip(),
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(audit)

        # Update final score
        result.final_score = new_score
        db.session.commit()

        return audit

    @staticmethod
    def admin_delete_viva_record(result_id: int, admin_id: int, reason: str = "") -> dict:
        """
        ADMIN ONLY.
        Transactionally deletes a student's viva attempt and result record so that the student
        becomes eligible to re-attend the viva assessment.
        Records an immutable audit log entry in MarkAudit before deletion.
        Preserves student account, viva container, PDF question bank, and all other student records.
        """
        result = db.session.get(Result, result_id)
        if not result:
            raise ValueError("Result record not found.")

        session = result.session
        if not session:
            raise ValueError("Associated viva session not found.")

        student = session.student
        viva = session.viva
        student_name = student.name if student else f"Student #{session.student_id}"
        viva_title = viva.title if viva else "Viva Assessment"

        try:
            # 1. Log immutable deletion audit entry in MarkAudit
            audit = MarkAudit(
                result_id=None,
                action="DELETE_VIVA_RECORD",
                viva_title=viva_title,
                student_id=session.student_id,
                original_score=result.final_score,
                edited_score=0.0,
                edited_by=admin_id,
                reason=reason.strip() if reason and reason.strip() else "Admin deleted viva record to enable student reattempt.",
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(audit)

            # 2. Delete evaluations and answers for all questions in this session
            for sq in session.session_questions:
                if sq.answer:
                    if sq.answer.evaluation:
                        db.session.delete(sq.answer.evaluation)
                    db.session.delete(sq.answer)
                db.session.delete(sq)

            # 3. Delete anti-cheat violations associated with this session
            Violation.query.filter_by(session_id=session.id).delete()

            # 4. Delete Result and VivaSession
            db.session.delete(result)
            db.session.delete(session)

            # Commit transaction atomically
            db.session.commit()

            return {
                "deleted_session_id": session.id,
                "deleted_result_id": result.id,
                "student_name": student_name,
                "viva_title": viva_title,
            }
        except Exception as e:
            db.session.rollback()
            raise e
