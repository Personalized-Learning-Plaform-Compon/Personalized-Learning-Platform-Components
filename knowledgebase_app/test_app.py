import pytest, pprint
from app import app, db, Student_Progress, Quizzes
from sqlalchemy import text

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Use an in-memory test DB
    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # Create test tables
        yield client
        with app.app_context():
            db.session.execute(text("DROP TABLE Quizzes CASCADE;"))  # Drop dependent table first
            db.session.execute(text("DROP TABLE Student_Progress CASCADE;"))
            db.session.commit()
            db.create_all()  # Recreate tables if needed

def test_get_progress(client):
    # Insert test data
    with app.app_context():
        quiz_entry = Quizzes(quiz_id = 1, topic="Math", difficulty="Easy", format="MCQ", content="What is 1+1?", tags=list({"addition", "math"}))
        progress_entry = Student_Progress(student_id=1, quiz_id = 1, topic="Math", score=85.0, time_spent = 9, attempt_date = "2022-01-01 12:00:00")
        progress_entry2 = Student_Progress(student_id=2, quiz_id = 1, topic="Math", score=100.0, time_spent = 9, attempt_date = "2022-01-01 12:30:00")
        progress_entry3 = Student_Progress(student_id=2, quiz_id = 1, topic="Math", score=34.0, time_spent = 9, attempt_date = "2022-01-01 12:30:00")

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
    # print(data)
    # assert isinstance(data, list)
    # assert data[0]["topic"] == "Math"
    # assert data[0]["avg_score"] == 85.0
