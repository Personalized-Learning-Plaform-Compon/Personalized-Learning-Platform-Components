from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegistrationForm


db = SQLAlchemy()

# User ORM for SQLAlchemy
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    fname = db.Column(db.String(50), nullable=False)
    lname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    school = db.Column(db.String(50), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

    def set_profile(self, form: RegistrationForm):
        self.fname = form.fname.data
        self.lname = form.lname.data
        self.email = form.email.data
        self.school = form.school.data
        self.user_type = form.user_type.data


class Students(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    progress = db.Column(db.JSON, default=None)
    feedback = db.Column(db.Text, default=None)
    preferred_topics = db.Column(db.JSON, default=None)
    strengths = db.Column(db.JSON, default=None)
    weaknesses = db.Column(db.JSON, default=None)
    learning_style = db.Column(db.JSON, default=None)
    
class Teachers(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    classes = db.Column(db.String(255), nullable=False)

class Quizzes(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.Enum('Easy', 'Medium', 'Hard'), nullable=False)
    format = db.Column(db.Enum('MCQ', 'Essay', 'True/False', 'Fill-in-the-blank'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.JSON, default=None)

class Student_Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.DECIMAL(5, 2), nullable=False)
    time_spent = db.Column(db.Integer, nullable=False)
    attempt_date = db.Column(db.DateTime, nullable=False)
