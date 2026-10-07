from datetime import datetime, timezone
from app.extensions import db


class VivaStatus:
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ALL = [DRAFT, PUBLISHED, ACTIVE, INACTIVE]


class Viva(db.Model):
    __tablename__ = "vivas"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(50), default=VivaStatus.DRAFT, nullable=False, index=True)
    question_count = db.Column(db.Integer, default=0, nullable=False)
    duration_seconds = db.Column(db.Integer, default=120, nullable=False)  # Total viva session timer in seconds
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    documents = db.relationship("Document", backref="viva", lazy="dynamic", cascade="all, delete-orphan")
    questions = db.relationship("Question", backref="viva", lazy="dynamic", cascade="all, delete-orphan")
    sessions = db.relationship("VivaSession", backref="viva", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "faculty_id": self.faculty_id,
            "faculty_name": self.faculty.name if self.faculty else None,
            "status": self.status,
            "question_count": self.question_count,
            "duration_seconds": self.duration_seconds,
            "duration_minutes": max(1, round(self.duration_seconds / 60)) if self.duration_seconds else 2,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
