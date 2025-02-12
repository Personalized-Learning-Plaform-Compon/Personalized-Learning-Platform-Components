import pytest, pprint
from app import app, Student_Progress, Quizzes
from sqlalchemy import text
from models import db
from models import Students, User
from datetime import datetime

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Use an in-memory test DB
    app.config["SECRET_KEY"] = "testing"  # Set a secret key for the session
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection in tests
    print("Using database:", app.config["SQLALCHEMY_DATABASE_URI"])
    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # Create test tables
        yield client
        with app.app_context():
            # db.session.execute(text("DROP TABLE Quizzes CASCADE;"))  # Drop dependent table first
            # db.session.execute(text("DROP TABLE Student_Progress CASCADE;"))
            # db.session.commit()
            db.create_all()  # Recreate tables if needed

def test_get_progress(client):
    # Insert test data
    date1 = datetime.strptime("2022-01-01 12:00:00", "%Y-%m-%d %H:%M:%S")
    date2 = datetime.strptime("2022-01-01 12:30:00", "%Y-%m-%d %H:%M:%S")
    with app.app_context():
        quiz_entry = Quizzes(quiz_id = 1, topic="Math", difficulty="Easy", format="MCQ", content="What is 1+1?", tags=list({"addition", "math"}))
        progress_entry = Student_Progress(student_id=1, quiz_id = 1, topic="Math", score=85.0, time_spent = 9, attempt_date = date1)
        progress_entry2 = Student_Progress(student_id=2, quiz_id = 1, topic="Math", score=100.0, time_spent = 9, attempt_date = date2)
        progress_entry3 = Student_Progress(student_id=2, quiz_id = 1, topic="Math", score=34.0, time_spent = 9, attempt_date = date2)

        db.session.add(quiz_entry) 
        db.session.add(progress_entry)        
        db.session.add(progress_entry2)
        db.session.add(progress_entry3)

        db.session.commit()
        

    # Make request
    response = client.get("/progress/2")
    response2 = client.get("/strengths/weakness/2")
    # Check response
    assert response.status_code == 200
    data = response.get_json()
    data2 = response2.get_json()
    with open("test_output.json", "w") as f:
        import json
        json.dump(data, f, indent=4) 
        json.dump(data2, f, indent=4)
    

def test_successful_registration(client):
    # Simulate the registration request 
    response = client.post('/register', data=dict(
        email='testuser@example.com',
        fname='Test',
        lname='User',
        password='password',
        password2='password',
        school='Test School',
        user_type='student'
    ), follow_redirects=True)
    #breakpoint()
    # Check that the response status is 200
    assert response.status_code == 200

    # Check that the success message is present in the response data
    assert b'Successfully registered' in response.data

    # Check that the user was created in the database
    with app.app_context():
        user = User.query.filter_by(email='testuser@example.com').first()
        assert user is not None
        assert user.fname == 'Test'
        assert user.lname == 'User'
        assert user.school == 'Test School'
        assert user.user_type == 'student'

        # Check that the associated Students record was created
        student = Students.query.filter_by(user_id=user.id).first()
        assert student is not None
        assert student.name == 'Test User'