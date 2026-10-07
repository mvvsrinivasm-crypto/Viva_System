import re
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models.user import User, Role
from app.utils.security import create_jwt_token
from app.middleware.auth import jwt_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().upper()

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400

    # Basic email format check
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Please provide a valid email address."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    # Allow registration as STUDENT or FACULTY. ADMIN accounts are reserved.
    if role not in (Role.STUDENT, Role.FACULTY):
        role = Role.STUDENT

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    user = User(
        name=name,
        email=email,
        role=role,
        is_active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_jwt_token(user.id, user.role, user.name, user.email)

    return jsonify({
        "message": "Registration successful.",
        "token": token,
        "user": user.to_dict(),
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    identifier = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "Email and password are required."}), 400

    # Allow login with either full email or registration number
    search_email = f"{identifier}@klu.ac.in" if "@" not in identifier else identifier
    user = User.query.filter(
        (User.email == identifier) | (User.email == search_email)
    ).first()
    if not user and "@" not in identifier:
        user = User.query.filter(User.name.ilike(f"%({identifier})%")).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    if not user.is_active:
        return jsonify({"error": "Your account has been deactivated. Contact an administrator."}), 403

    token = create_jwt_token(user.id, user.role, user.name, user.email)

    return jsonify({
        "message": "Login successful.",
        "token": token,
        "user": user.to_dict(),
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    return jsonify({
        "user": g.current_user.to_dict(),
    }), 200
