from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Role:
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    ADMIN = "ADMIN"
    ALL = [STUDENT, FACULTY, ADMIN]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    vivas = db.relationship("Viva", backref="faculty", lazy="dynamic", foreign_keys="Viva.faculty_id")
    sessions = db.relationship("VivaSession", backref="student", lazy="dynamic", foreign_keys="VivaSession.student_id")
    violations = db.relationship("Violation", backref="student", lazy="dynamic")
    audits_edited = db.relationship("MarkAudit", backref="editor", lazy="dynamic", foreign_keys="MarkAudit.edited_by")

    @property
    def registration_number(self) -> str:
        import re
        if self.name:
            m = re.search(r'\((\d+)\)', self.name)
            if m:
                return m.group(1)
            m = re.search(r'\b(\d{6,12})\b', self.name)
            if m:
                return m.group(1)
        if self.email:
            m = re.search(r'(\d{6,12})', self.email)
            if m:
                return m.group(1)
        return f"992100{self.id:04d}" if self.role == Role.STUDENT else "FACULTY"

    @property
    def department(self) -> str:
        if "cs" in (self.email or "").lower() or "cs" in (self.name or "").lower():
            return "Computer Science & Engineering"
        if "ee" in (self.email or "").lower() or "ee" in (self.name or "").lower():
            return "Electrical & Electronics Engineering"
        return "School of Computing"

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "registration_number": self.registration_number,
            "department": self.department,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
