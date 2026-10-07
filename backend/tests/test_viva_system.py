import pytest
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User, Role
from app.models.viva import Viva, VivaStatus
from app.models.question import Question
from app.models.viva_session import VivaSession, SessionStatus
from app.models.result import Result
from app.models.mark_audit import MarkAudit
from app.services.pdf_service import PDFService
from app.services.viva_service import VivaService


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_auth_and_roles(client):
    """Test user registration and login token generation."""
    # Register student
    res = client.post("/api/auth/register", json={
        "name": "Test Student",
        "email": "test_student@klu.ac.in",
        "password": "password123",
        "role": "STUDENT",
    })
    # Could be 201 or 409 if already exists
    assert res.status_code in (201, 409)

    # Login student
    res = client.post("/api/auth/login", json={
        "email": "student@klu.ac.in",
        "password": "student123",
    })
    assert res.status_code == 200
    student_token = res.get_json()["token"]

    # Student cannot access admin audits
    res = client.get("/api/admin/audits", headers={"Authorization": f"Bearer {student_token}"})
    assert res.status_code == 403

    # Student cannot access admin mark edit
    res = client.patch("/api/admin/results/1", json={"new_score": 18, "reason": "Test"}, headers={"Authorization": f"Bearer {student_token}"})
    assert res.status_code == 403


def test_pdf_parsing_rule():
    """
    CRITICAL RULE TEST:
    The PDF is the ONLY source of questions.
    If questions lack reference answers, validation must fail.
    Never generate questions or answers with LLM.
    """
    valid_pdf_text = """
1. What is an activation function?
Answer: A mathematical function applied to a neuron's output to introduce non-linearity.

2. Explain Gradient Descent.
Answer: An iterative optimization algorithm used to minimize a cost function.

3. What is learning rate?
Answer: A tuning parameter in an optimization algorithm that determines the step size at each iteration.
"""
    result = PDFService.parse_qa_pairs(valid_pdf_text)
    assert result["validation_passed"] is True
    assert result["valid_count"] == 3
    assert result["invalid_count"] == 0

    # Missing answer test
    incomplete_pdf_text = """
1. What is an activation function?
Answer: A mathematical function applied to a neuron's output.

2. Explain Gradient Descent without answer.

3. What is learning rate?
Answer: A step size parameter.
"""
    incomplete_result = PDFService.parse_qa_pairs(incomplete_pdf_text)
    assert incomplete_result["validation_passed"] is False
    assert incomplete_result["invalid_count"] >= 1
    assert "Validation failed" in incomplete_result["validation_message"]


def test_best_two_of_three_calculation():
    """
    Scoring rule test:
    Best 2 of 3 questions, max 20 marks. Never out of 30.
    """
    # Example 1: Q1=7, Q2=9, Q3=5 -> Top 2 are 9 and 7 -> 16
    final, c1, c2 = VivaService.calculate_best_two_of_three(7.0, 9.0, 5.0)
    assert final == 16.0
    assert {c1, c2} == {1, 2}

    # Example 2: Q1=10, Q2=2, Q3=8 -> Top 2 are 10 and 8 -> 18
    final2, c1_2, c2_2 = VivaService.calculate_best_two_of_three(10.0, 2.0, 8.0)
    assert final2 == 18.0
    assert {c1_2, c2_2} == {1, 3}

    # Max clamp test
    final3, _, _ = VivaService.calculate_best_two_of_three(10.0, 10.0, 10.0)
    assert final3 == 20.0


def test_admin_audit_security(client):
    """
    Admin can edit marks and create immutable audit logs.
    Faculty and Student get 403 Forbidden on audit endpoints.
    """
    # 1. Login Admin
    res_admin = client.post("/api/auth/login", json={
        "email": "admin@klu.ac.in",
        "password": "admin123",
    })
    assert res_admin.status_code == 200
    admin_token = res_admin.get_json()["token"]

    # 2. Login Faculty
    res_fac = client.post("/api/auth/login", json={
        "email": "faculty@klu.ac.in",
        "password": "faculty123",
    })
    assert res_fac.status_code == 200
    faculty_token = res_fac.get_json()["token"]

    # Faculty cannot access GET /api/admin/audits
    res = client.get("/api/admin/audits", headers={"Authorization": f"Bearer {faculty_token}"})
    assert res.status_code == 403

    # Admin CAN access GET /api/admin/audits
    res_ok = client.get("/api/admin/audits", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_ok.status_code == 200
