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


