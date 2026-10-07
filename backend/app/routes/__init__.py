from app.routes.auth import auth_bp
from app.routes.student import student_bp
from app.routes.faculty import faculty_bp
from app.routes.admin import admin_bp

__all__ = ["auth_bp", "student_bp", "faculty_bp", "admin_bp"]
