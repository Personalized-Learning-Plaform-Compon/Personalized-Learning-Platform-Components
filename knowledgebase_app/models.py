from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

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
        self.password = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def set_profile(self, form):
        self.fname = form.fname.data
        self.lname = form.lname.data
        self.email = form.email.data
        self.school = form.school.data
        self.user_type = form.user_type.data

class Students(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Match the table name specified in User
    name = db.Column(db.String(255), nullable=False)
    progress = db.Column(db.JSON, default={})
    feedback = db.Column(db.Text, default=None)
    preferred_topics = db.Column(db.JSON, default={})
    strengths = db.Column(db.JSON, default={})
    weaknesses = db.Column(db.JSON, default={})
    learning_style = db.Column(db.JSON, default={})
    user = db.relationship('User', backref=db.backref('students', lazy=True))

class Teachers(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    classes = db.Column(db.JSON, default={})

class Courses(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)

class CourseEnrollment(db.Model):
    __tablename__ = 'course_enrollment'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)

class Quizzes(db.Model):
    __tablename__ = 'quizzes'
    courses_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    quiz_id = db.Column(db.Integer, primary_key=True, nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.Enum('Easy', 'Medium', 'Hard', name="difficulty_enum"), nullable=False)
    format = db.Column(db.Enum('MCQ', 'Essay', 'True/False', 'Fill-in-the-blank', name="quiz_format_enum"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.JSON, default={})
    
class Student_Progress(db.Model):
    __tablename__ = 'student_progress'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.quiz_id'), nullable=False)
    score = db.Column(db.Numeric(5, 2), nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    time_spent = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(255)) #complete, review, start
    attempt_date = db.Column(db.DateTime, nullable=False)

class Folder(db.Model):
    __tablename__ = 'folders'
    
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    course = db.relationship('Courses', backref=db.backref('folders', lazy=True))

class CourseContent(db.Model):
    __tablename__ = 'course_content'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(512), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    category = db.Column(db.String(255), nullable=True)
    
    
    course = db.relationship('Courses', backref=db.backref('content', lazy=True))
    folder = db.relationship('Folder', backref=db.backref('files', lazy=True))

    file_extension = db.Column(db.String(255), nullable=True)


