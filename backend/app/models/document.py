from datetime import datetime, timezone
from app.extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    viva_id = db.Column(db.Integer, db.ForeignKey("vivas.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_hash = db.Column(db.String(64), nullable=True)
    storage_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    questions = db.relationship("Question", backref="document", lazy="dynamic", cascade="all, delete-orphan")
    uploader = db.relationship("User", foreign_keys=[uploaded_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "viva_id": self.viva_id,
            "uploaded_by": self.uploaded_by,
            "file_name": self.file_name,
            "file_hash": self.file_hash,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
