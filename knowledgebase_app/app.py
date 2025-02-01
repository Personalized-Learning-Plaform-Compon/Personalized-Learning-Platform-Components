from flask import Flask,render_template, redirect, url_for, flash, session 
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager,UserMixin, login_required, login_user, logout_user
# import logging
# from datetime import datetime
from forms import LoginForm, RegistrationForm
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

# Google Cloud SQL configuration
PASSWORD = "seniorproject"
PUBLIC_IP_ADDRESS = "34.45.162.72"
DBNAME = "test"
PROJECT_ID = "regal-reporter-449223-a4"
INSTANCE_NAME = "knowledgebase"

# configuration
app.config["SECRET_KEY"] = "yoursecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+mysqldb://root:{PASSWORD}@{PUBLIC_IP_ADDRESS}/{DBNAME}?unix_socket=/cloudsql/{PROJECT_ID}:{INSTANCE_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# User ORM for SQLAlchemy
class User(UserMixin, db.Model):
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

# User loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            try:
                login_user(user)
                flash('Login Successful!', 'success')
                return redirect(url_for('profile'))
            except Exception as e:
                print(f"Error occurred: {e}")
        else:
            flash('Login Failed! Please check your credentials', 'danger')
    return render_template('login.html', form=form)
    
@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        user.set_profile(form)
        db.session.add(user)
        db.session.commit()
        flash('Successfully registered.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)
        
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    user_id = session.get('_user_id')
    # print(f"{session=}")
    if user_id is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    if user is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
