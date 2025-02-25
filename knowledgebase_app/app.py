import os
import requests
from flask import Flask, render_template, redirect, url_for, flash, session, jsonify, request
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from dotenv import load_dotenv
from flask_migrate import Migrate
from forms import LoginForm, RegistrationForm, StudentProfileForm
from models import User, db, Students, Student_Progress, Quizzes, Teachers

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Load configuration from environment variables
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database and migration support
db.init_app(app)
migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = "login"

# User loader function
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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
            return redirect(url_for('login'))
        
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
            db.session.commit()
            
            if user.user_type == 'student':
                registered_user = Students(
                    user_id=user.id,  
                    name=f"{form.fname.data} {form.lname.data}",  
                    progress=None,
                    feedback=None,
                    preferred_topics=None,
                    strengths=None,
                    weaknesses=None,
                    learning_style=None
                )

            elif user.user_type == 'teacher':
                registered_user = Teachers(
                    user_id=user.id,
                    name=f"{form.fname.data} {form.lname.data}",
                    classes=None,
                )

            db.session.add(registered_user)
            db.session.commit()
            flash('Successfully registered.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error occurred: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('register.html', form=form)
        
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
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
    
    
    # Update learning style
    form = StudentProfileForm()
    if form.validate_on_submit():
        try:
            student = Students.query.filter_by(user_id=user_id).first()
            if student:
                student.learning_style = form.learning_style.data
                db.session.commit()
                flash('Learning style updated successfully.', 'success')
            else:
                flash('Student not found.', 'danger')
        except Exception as e:
            db.session.rollback()
            print(f"Error occurred: {e}")
            flash('An error occurred while updating learning style. Please try again.', 'danger')
        return redirect(url_for('profile'))
    else:
        print(form.errors)  # Debugging: Print form errors to the console

    

    
    return render_template('profile.html', user=user, form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user
    student = Students.query.filter_by(user_id=user.id).first()
    if not student:
        flash('Student not found. Please try again.', 'danger')
        return redirect(url_for('profile'))


    # TODO: design Course model and update the query below
    courses = [] #assuming this is where the courses from the database will go
                
    return render_template('dashboard.html', user=user, courses=courses)


@app.route('/survey')
def survey():
    return render_template('survey.html')

@app.route('/courses')
def courses():
    return render_template('courses.html')

# def generate_quiz(topic_text, num_questions=5):
#     """
#     Generate quiz questions from a given topic text using Huggingface API.
    
#     Parameters:
#     topic_text (str): The text from which to generate questions.
#     num_questions (int): The number of questions to generate. Default is 5.
    
#     Returns:
#     list: A list of generated quiz questions.
#     """
#     quiz_questions = []

#     for i in range(num_questions):
#         prompt = f"Generate a question from the following text: {topic_text}"
#         response = requests.post(
#             "https://api-inference.huggingface.co/models/t5-small",
#             headers={"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"},
#             json={"inputs": prompt, "parameters": {"max_length": 100, "do_sample": True}}
#         )
#         if response.status_code != 200:
#             return jsonify({"error": "Quiz generation failed. Please try again later."}), 500

#         generated_text = response.json()[0]['generated_text']

#         quiz_questions.append(generated_text)

#     return quiz_questions


# @app.route("/quiz", methods=["GET", "POST"])
# def quiz():
#     data = request.get_json()
#     topic_text = data.get("topic_text", "")
#     num_questions = int(data.get("num_questions", 5))

#     if not topic_text:
#         return jsonify({"error": "Please provide a topic_text"}), 400

#     quiz_questions = generate_quiz(topic_text, num_questions)
#     return jsonify({"quiz_questions": quiz_questions})

#     return render_template('quiz.html')

@app.route('/generate_quiz', methods=['POST'])
@login_required
def generate_quiz():
    data = request.get_json()
    topic = data.get("topic", "General Knowledge")

    gradio_api_url = "http://127.0.0.1:7860/api/predict"
    payload = {"data": [topic]}

    response = requests.post(gradio_api_url, json=payload)

    print(f"Gradio Response: {response.status_code}, {response.text}")  # Debugging line

    if response.status_code == 200:
        quiz_data = response.json()
        return jsonify({"quiz": quiz_data["data"][0]})
    else:
        return jsonify({"error": "Failed to generate quiz", "details": response.text}), 500


@app.route('/quiz')
@login_required
def quiz():
    return render_template('quiz.html')  

def analyze_strengths_weaknesses(student_id):
    results = (
        db.session.query(Student_Progress.topic, db.func.avg(Student_Progress.score).label('avg_score'))
        .filter(Student_Progress.student_id == student_id)
        .group_by(Student_Progress.topic)
        .all()
    )

    strengths = [topic for topic, avg_score in results if avg_score > 80]
    weaknesses = [topic for topic, avg_score in results if avg_score < 50]

    return {"strengths": strengths, "weaknesses": weaknesses}

def recommend_content(student_id):
    analysis = analyze_strengths_weaknesses(student_id)
    strengths = analysis['strengths']
    weaknesses = analysis['weaknesses']

    # Recommend for weaknesses
    weak_recommendations = (
        db.session.query(Quizzes.id, Quizzes.topic, Quizzes.difficulty, Quizzes.format, Quizzes.content)
        .filter(Quizzes.topic.in_(weaknesses), Quizzes.difficulty == 'Easy')
        .limit(5)
        .all()
    )

    # Recommend for strengths
    strong_recommendations = (
        db.session.query(Quizzes.id, Quizzes.topic, Quizzes.difficulty, Quizzes.format, Quizzes.content)
        .filter(Quizzes.topic.in_(strengths), Quizzes.difficulty == 'Hard')
        .limit(5)
        .all()
    )

    return {"weak_areas": weak_recommendations, "strong_areas": strong_recommendations}


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)