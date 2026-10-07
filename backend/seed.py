import os
from pathlib import Path
import pymupdf as fitz
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.viva import Viva, VivaStatus
from app.models.document import Document
from app.models.question import Question
from app.services.pdf_service import PDFService

app = create_app()


def generate_sample_pdf(output_path: Path):
    """Generate a clean academic Q&A PDF using PyMuPDF for faculty testing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()

    sample_content = """KALASALINGAM ACADEMY OF RESEARCH AND EDUCATION
Department of Computer Science and Engineering
Laboratory Viva Assessment Question Bank
Course: CS304 - Machine Learning and Deep Learning Laboratory

1. What is the fundamental difference between supervised and unsupervised learning?
Answer: In supervised learning, the training dataset contains labeled input-output pairs where the model learns an explicit mapping function. In unsupervised learning, the model is provided with unlabeled data and discovers underlying patterns, structures, groupings, or representations autonomously.

2. Explain the purpose and mathematical objective of the Cost Function in linear regression.
Answer: The cost function, typically Mean Squared Error (MSE), quantifies the average squared difference between predicted values and actual ground truth targets. Its objective during optimization is to be minimized by iteratively adjusting model weights and biases via gradient descent.

3. Why is train-test split essential in statistical machine learning models?
Answer: Train-test split partitions data into independent training and validation subsets to assess generalizability on unseen data and detect overfitting or underfitting before model deployment.

4. What is the vanishing gradient problem in deep neural networks and how do ReLU activations mitigate it?
Answer: The vanishing gradient problem occurs when backpropagated gradients shrink exponentially through deep layers with saturating activations like sigmoid or tanh, causing early layers to train very slowly. The Rectified Linear Unit (ReLU) mitigates this by maintaining a constant unit derivative for all positive inputs, ensuring gradients flow without saturation.

5. Define Overfitting and describe two common regularization techniques used to prevent it.
Answer: Overfitting occurs when a statistical model memorizes noise and sample-specific idiosyncrasies of training data rather than underlying trends, leading to poor validation performance. Common regularization techniques include L1/L2 weight penalties and Dropout which randomly deactivates neurons during training.
"""

    rect = fitz.Rect(50, 50, 550, 750)
    page.insert_textbox(rect, sample_content, fontsize=10, fontname="helv", align=0)
    doc.save(str(output_path))
    doc.close()
    print(f"Sample PDF created at: {output_path}")


def seed_database():
    with app.app_context():
        print("Creating all tables in Neon PostgreSQL...")
        db.create_all()
        print("Database schema synced with Neon PostgreSQL.")

        # Create or update Admin
        admin = User.query.filter_by(email="srinivas@klu.ac.in").first()
        if not admin:
            admin = User(
                name="System Administrator",
                email="srinivas@klu.ac.in",
                role=Role.ADMIN,
                is_active=True,
            )
            admin.set_password("Sady@2020")
            db.session.add(admin)
            print("Admin user created: srinivas@klu.ac.in / Sady@2020")
        else:
            admin.set_password("Sady@2020")

        # Create or update Faculty
        faculty = User.query.filter_by(email="faculty@klu.ac.in").first()
        if not faculty:
            faculty = User(
                name="Dr. K. Ramasamy",
                email="faculty@klu.ac.in",
                role=Role.FACULTY,
                is_active=True,
            )
            faculty.set_password("faculty123")
            db.session.add(faculty)
            print("Faculty user created: faculty@klu.ac.in / faculty123")
        else:
            faculty.set_password("faculty123")

        # Create or update Demo Student (Arun Kumar S)
        student = User.query.filter_by(email="student@klu.ac.in").first()
        if not student:
            student = User(
                name="Arun Kumar S (9921004123)",
                email="student@klu.ac.in",
                role=Role.STUDENT,
                is_active=True,
            )
            student.set_password("student123")
            db.session.add(student)
            print("Demo student created: student@klu.ac.in / student123")
        else:
            student.set_password("student123")

        # 70 University Enrolled Students
        batch_students = [
            ("99240040212", "CHIDANANDA N"),
            ("99240040273", "LAMBADI RAVITEJA"),
            ("99240040954", "MUPPALA SRISHTA SHREE"),
            ("99240040955", "JUTURU HEMASRI"),
            ("99240040956", "KANAKAM SRIRAM KUMAR"),
            ("99240040957", "KAMULA VENKATA SIVA MAHESH REDDY"),
            ("99240040958", "THOTA YASWANTH"),
            ("99240040959", "KAKARLA THARUN KESHAVA"),
            ("99240040960", "VELUGURI V N S P MADESH KUMAR"),
            ("99240040961", "KAGITHA VEERA VENKATA SAI NAGESH"),
            ("99240040962", "THUMMALA DINESH REDDY"),
            ("99240040963", "KAARVETI HIMA BINDU"),
            ("99240040964", "KAMBHAMPATI VENKATA LAHARI NAIDU"),
            ("99240040965", "KAMBHAM DEVANSUR REDDY"),
            ("99240040966", "KAMALA RISHIK"),
            ("99240040967", "KAKI KUSHAL KUMAR"),
            ("99240040968", "KAMBLE SHYMALESHWAR"),
            ("99240040969", "KAKI HEMANTH"),
            ("99240040970", "KANCHERLA SRI CHARAN"),
            ("99240040971", "KANCHI GRISHNA"),
            ("99240040972", "KANCHI SIMHADRI"),
            ("99240040974", "KAMALINI R"),
            ("99240040975", "TULLURU HARSHA VARDHAN CHOWDARY"),
            ("99240040976", "TUMKUR JABIN TAJ"),
            ("99240040977", "KONDA JAYASRI"),
            ("99240040978", "KONA TEJASWI"),
            ("99240040979", "KONA AYYAPPA AJAY KUMAR"),
            ("99240040980", "KAYALA SAI PAVAN KUMAR"),
            ("99240040981", "TONANGI SIVA"),
            ("99240040982", "THUMMURI DEVAKI PRIYA KRISHNA PRASAD"),
            ("99240040983", "KOLA KIRAN KUMAR"),
            ("99240040985", "TODETI CHAITANYA"),
            ("99240040986", "KAYALA RISHITHA LAKSHMI"),
            ("99240040987", "KAKARLA VENKATA HANUMAN CHANDU"),
            ("99240040988", "KOLLA VENKATA LAKSHMI JANARDHAN RAO"),
            ("99240040989", "DONAPPA EKANTH"),
            ("99240040990", "KEERTHIPATI TEJESWAR RAJU"),
            ("99240040991", "THUMMALA JYOSHNA REDDY"),
            ("99240040992", "KODURI VIGHNESH BABU"),
            ("99240040993", "KOMMU GAYATHRI"),
            ("99240040994", "KOKKILIGADDA LAHAREESH"),
            ("99240040995", "TIRIMAREDDY SIVA GANESH"),
            ("99240040996", "KOMMARAGUNTA DIMPY"),
            ("99240040997", "KATTA HARSHA VARDHAN"),
            ("99240040998", "SRIRAM MANOJ KUMAR"),
            ("99240040999", "GUNDEPOGU EMIL ROHAN WESLY"),
            ("99240041000", "LALITHESH R V"),
            ("99240041001", "MADDELA BHARATH"),
            ("99240041002", "MACHIKA RADHA KRISHNA"),
            ("99240041003", "MADDHA CHANDRA LEKHA"),
            ("99240041004", "KURLI SHIVANANDA REDDY"),
            ("99240041005", "MADAM YOGENDRA"),
            ("99240041006", "D LEPAKSHI REDDY"),
            ("99240041007", "LIKITH RAJ P"),
            ("99240041008", "KURRAM HEMALATHA"),
            ("99240041009", "LAKKARAJU.ANUDEEP"),
            ("99240041010", "LAVANURU ARUNA"),
            ("99240041012", "KURUBA REVANTH KUMAR"),
            ("99240041013", "KURUBA ARAVIND"),
            ("99240041014", "KURRA SANTHOSH"),
            ("99240041015", "LAKKI REDDY HARSHITHA"),
            ("99240041016", "KURUVVA HARSHAVARDHAN"),
            ("99240041018", "KURUBA MOHITH KUMAR"),
            ("99240041019", "DUVADA DHANALAKSHMI"),
            ("99240041020", "MACHAVARAM SAI DEEPIKA"),
            ("99240041021", "MARANAN JAN K"),
            ("99240041022", "MATHI BALAN P"),
            ("99240041023", "MANNEPALLI HARSHA PRIYA"),
            ("99240041024", "MATTAPARTHI VEERA VENKATA SRINIVAS"),
            ("99240041025", "MEKALA KRISHNA KOWSHICK"),
        ]

        created_count = 0
        updated_count = 0
        for reg_no, name in batch_students:
            email = f"{reg_no}@klu.ac.in"
            full_name = f"{name} ({reg_no})"
            st = User.query.filter((User.email == email) | (User.name.like(f"%{reg_no}%"))).first()
            if not st:
                st = User(
                    name=full_name,
                    email=email,
                    role=Role.STUDENT,
                    is_active=True,
                )
                st.set_password(reg_no)
                db.session.add(st)
                created_count += 1
            else:
                st.name = full_name
                st.email = email
                st.role = Role.STUDENT
                st.is_active = True
                st.set_password(reg_no)
                updated_count += 1

        db.session.commit()
        print(f"Batch student seeding completed: {created_count} created, {updated_count} verified/updated.")

        # Generate sample PDF
        sample_pdf_path = Path(app.config["UPLOAD_FOLDER"]) / "sample_viva_ml_questions.pdf"
        generate_sample_pdf(sample_pdf_path)

        # Check if sample viva exists
        viva = Viva.query.filter_by(title="CS304 - Machine Learning Lab Viva 2026").first()
        if not viva:
            viva = Viva(
                title="CS304 - Machine Learning Lab Viva 2026",
                description="Comprehensive viva examination on supervised learning, neural networks, cost functions, and model regularization.",
                faculty_id=faculty.id,
                status=VivaStatus.PUBLISHED,
                question_count=5,
            )
            db.session.add(viva)
            db.session.flush()

            # Read PDF and parse
            pdf_bytes = sample_pdf_path.read_bytes()
            extracted_text = PDFService.extract_text_from_pdf(pdf_bytes)
            parsed = PDFService.parse_qa_pairs(extracted_text)

            doc = Document(
                viva_id=viva.id,
                uploaded_by=faculty.id,
                file_name="sample_viva_ml_questions.pdf",
                file_hash=PDFService.calculate_file_hash(pdf_bytes),
                storage_path=str(sample_pdf_path),
            )
            db.session.add(doc)
            db.session.flush()

            for q_data in parsed["questions"]:
                q = Question(
                    viva_id=viva.id,
                    document_id=doc.id,
                    question_number=q_data["question_number"],
                    question_text=q_data["question_text"],
                    reference_answer=q_data["reference_answer"],
                )
                db.session.add(q)

            db.session.commit()
            print(f"Sample viva created with {len(parsed['questions'])} validated questions extracted strictly from PDF.")

        print("Database seed completed successfully.")


if __name__ == "__main__":
    seed_database()
