from functools import wraps
from flask import request, jsonify, g
from app.extensions import db
from app.utils.security import decode_jwt_token
from app.models.user import User, Role


def jwt_required(optional: bool = False):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                if optional:
                    g.current_user = None
                    return f(*args, **kwargs)
                return jsonify({"error": "Authorization header missing"}), 401

            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify({"error": "Invalid Authorization header format. Expected 'Bearer <token>'"}), 401

            token = parts[1]
            try:
                payload = decode_jwt_token(token)
            except ValueError as e:
                return jsonify({"error": str(e)}), 401

            user_id = payload.get("user_id")
            user = db.session.get(User, int(user_id)) if user_id else None
            if not user:
                return jsonify({"error": "User account no longer exists"}), 401

            if not user.is_active:
                return jsonify({"error": "Account is deactivated. Please contact an administrator."}), 403

            # Store verified user in Flask g context
            g.current_user = user
            g.token_payload = payload
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def role_required(*allowed_roles):
    """
    Enforces RBAC on endpoints.
    User role is ALWAYS derived from the database record attached to the verified JWT,
    never trusted from frontend parameters.
    """
    def decorator(f):
        @wraps(f)
        @jwt_required(optional=False)
        def decorated_function(*args, **kwargs):
            current_user = g.current_user
            if current_user.role not in allowed_roles:
                return jsonify({
                    "error": "Forbidden: You do not have permission to access this resource",
                    "user_role": current_user.role,
                    "allowed_roles": list(allowed_roles),
                }), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Convenience decorators
def student_required(f):
    return role_required(Role.STUDENT)(f)


def faculty_required(f):
    return role_required(Role.FACULTY)(f)


def admin_required(f):
    return role_required(Role.ADMIN)(f)


def faculty_or_admin_required(f):
    return role_required(Role.FACULTY, Role.ADMIN)(f)
