import os
from unittest.mock import MagicMock, patch

# Set the environment variable for testing BEFORE importing app.py
os.environ["FLASK_ENV"] = "testing"
os.environ["OPENAI_API_KEY"] = "testing"

import pytest, pprint
from app import app, Student_Progress, Quizzes
from sqlalchemy import text
from models import db
from models import Students, User
from datetime import datetime
from werkzeug.security import generate_password_hash


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Use an in-memory test DB
    app.config["SECRET_KEY"] = "testing"  # Set a secret key for the session
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection in tests
    app.config["OPENAI_API_KEY"] = "testing"  
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
    

# def test_successful_registration(client):
#     # Simulate the registration request 
#     response = client.post('/register', data=dict(
#         email='testuser@example.com',
#         fname='Test',
#         lname='User',
#         password='password',
#         password2='password',
#         school='Test School',
#         user_type='student'
#     ), follow_redirects=True)
#     # Check that the response status is 200
#     assert response.status_code == 200

#     # Check that the success message is present in the response data
#     assert b'Successfully registered' in response.data

#     # Check that the user was created in the database
#     with app.app_context():
#         user = User.query.filter_by(email='testuser@example.com').first()
#         assert user is not None
#         assert user.fname == 'Test'
#         assert user.lname == 'User'
#         assert user.school == 'Test School'
#         assert user.user_type == 'student'

#         # Check that the associated Students record was created
#         student = Students.query.filter_by(user_id=user.id).first()
#         assert student is not None
#         assert student.name == 'Test User'


# def test_email_already_registered(client):
#     # Define registration data
#     reg_data = dict(
#         email='testuser2@example.com',
#         fname='Test',
#         lname='User',
#         password='password',
#         password2='password',
#         school='Test School',
#         user_type='student'
#     )
    
#     # First registration should succeed
#     response1 = client.post('/register', data=reg_data, follow_redirects=True)
#     assert response1.status_code == 200
#     assert b'Successfully registered' in response1.data

#     # Second attempt using the same email should be rejected
#     response2 = client.post('/register', data=reg_data, follow_redirects=True)
#     assert response2.status_code == 200
#     assert b'Email already registered. Please log in.' in response2.data


# def test_registration_passwords_not_matched(client):
#     # Define registration data
#     reg_data = dict(
#         email='testuser3@example.com',
#         fname='Test',
#         lname='User',
#         password='password',
#         password2='password2',
#         school='Test School',
#         user_type='student'
#     )
    
#     # First registration should succeed
#     response = client.post('/register', data=reg_data, follow_redirects=True)
#     assert response.status_code == 200
#     assert b'Passwords do not match!' in response.data


# def test_successful_login(client):
#     # Log in with an existing user
#     response = client.post('/login', data=dict(
#         email='testuser2@example.com',
#         password='password'
#     ))
#     assert response.status_code == 302
#     assert b'You should be redirected' in response.data

# def test_unsuccessful_login(client):
#     # Log in with an existing user
#     response = client.post('/login', data=dict(
#         email='testuser2@example.com2',
#         password='password'
#     ))
#     assert response.status_code == 200
#     assert b'Login Failed! Please check your credentials' in response.data


# def test_update_learning_style(client):
#     # Create a test user
#     user = User(
#         email='student@example.com',
#         fname='Student',
#         lname='Test',
#         school='Test School',
#         user_type='student',
#         password=generate_password_hash('password')
#     )
#     with app.app_context():
#         db.session.add(user)
#         db.session.commit()
#     # Create a corresponding Students record
#         user_id = user.id
#         student = Students(
#             user_id=user_id,
#             name='Student Test',
#             learning_style='Auditory',
#             progress={}, feedback=None, preferred_topics={}, strengths={}, weaknesses={})
                           
#         db.session.add(student)
#         db.session.commit()
        

#     # Simulate a login by setting the user id in the session.
#     # (Adjust the session key name if your login manager uses a different one.)
#     with client.session_transaction() as sess:
#         sess['_user_id'] = str(user_id)

#     # Define new learning style data to update
#     new_learning_style = "Visual"

    # Mock the OpenAI API call
    with patch('app.openai_client') as mock_openai_client:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Mocked learning methods"))]
        mock_openai_client.chat.completions.create.return_value = mock_response  # Mock the create method
    #     # Post new learning style via the update form (endpoint assumed to be '/profile')
    #     response = client.post('/profile', data={
    #         'learning_style': new_learning_style
    #     }, follow_redirects=True)
    
    #     # Check for the success flash message in the response
    #     assert response.status_code == 200
    #     assert b'Learning style updated successfully.' in response.data

#     # Verify that the student's record was updated in the database
#     updated_student = db.session.get(Students, user_id)
#     assert updated_student is not None
#     assert updated_student.learning_style == new_learning_style
