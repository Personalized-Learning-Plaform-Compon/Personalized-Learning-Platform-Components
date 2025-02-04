from flask import Flask, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, login_required, login_user, logout_user
from flask_migrate import Migrate
from forms import LoginForm, RegistrationForm
from models import User, db, Students

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

login_manager = LoginManager(app)
login_manager.login_view = "login"

# binding app with db
db.init_app(app)
migrate = Migrate(app, db)

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
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'warning')
            return redirect(url_for('register'))
        
        try:
            user = User(
                email=form.email.data,
                fname=form.fname.data,
                lname=form.lname.data,
                school=form.school.data,
                user_type=form.user_type.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            
            student = Students(
                id=user.id,  
                name=f"{form.fname.data} {form.lname.data}",  
                progress=None,
                feedback=None,
                preferred_topics=None,
                strengths=None,
                weaknesses=None,
                learning_style=None
            )
            db.session.add(student)
            
            db.session.commit()
            flash('Successfully registered.', 'success')
            return redirect(url_for('register'))
        except Exception as e:
            db.session.rollback()
            print(f"Error occurred: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')
    
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

@app.route('/survey')
def survey():
    return render_template('survey.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
