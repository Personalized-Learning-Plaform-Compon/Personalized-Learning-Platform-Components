import os
from flask import Flask, render_template, redirect, url_for, flash, session, jsonify, request
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from dotenv import load_dotenv
from flask_migrate import Migrate
from forms import LoginForm, RegistrationForm, StudentProfileForm
from models import User, db, Students, Student_Progress, Quizzes, Teachers, Courses, CourseEnrollment

# Automatically set FLASK_ENV to "development" if not explicitly set
if os.getenv("FLASK_ENV") is None:
    os.environ["FLASK_ENV"] = "development"

# Load environment variables from .env file
app = Flask(__name__)
env_file = '..\\.env'
load_dotenv(env_file, override=True)

if os.getenv("FLASK_ENV") == 'testing':
    env_file = '.env.test'
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Use an in-memory test DB
    app.config["SECRET_KEY"] = "testing"  # Set a secret key for the session
else:
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
    return db.session.get(User, user_id)
    #return User.query.get(int(user_id))

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
    if user_id is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    #user = User.query.get(user_id)
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    student = Students.query.filter_by(user_id=user.id).first()
    # Update learning style
    form = StudentProfileForm()
    if form.validate_on_submit():
        try:
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

    

    
    return render_template('profile.html', user=user, student=student, form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user
    student = Students.query.filter_by(user_id=user.id).first()
    if not student:
        flash('Student not found. Please try again.', 'danger')
        return redirect(url_for('profile'))


    # TODO: design Course model and update the query below
    # courses = [] #assuming this is where the courses from the database will go

    enrolled_courses = (
        db.session.query(Courses)
        .join(CourseEnrollment, Courses.id == CourseEnrollment.course_id)
        .filter(CourseEnrollment.student_id == Students.id)
        .all()
    )
                
    return render_template('dashboard.html', user=user, courses=enrolled_courses)


@app.route('/survey')
def survey():
    return render_template('survey.html')

@app.route('/courses', methods=['GET'])
def courses():
    all_courses = db.session.query(Courses, Teachers).join(Teachers, Courses.teacher_id == Teachers.id).all()
    enrolled_courses = [enrollment.course_id for enrollment in CourseEnrollment.query.filter_by(student_id=Students.id).all()]
    return render_template('courses.html', courses=all_courses, enrolled_courses=enrolled_courses)

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    # Ensure the logged-in user is a student
    if current_user.user_type != "student":
        flash("Only students can enroll in courses.", "danger")
        return redirect(url_for("courses"))

    # Retrieve the student's entry based on the logged-in user's ID
    student = Students.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("courses"))

    # Get the student_id from the Students table
    student_id = student.id

    # Check if the student is already enrolled in the course
    enrollment_exists = CourseEnrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if enrollment_exists:
        flash("You are already enrolled in this course.", "info")
        return redirect(url_for("courses"))

    # Create a new enrollment entry
    enrollment = CourseEnrollment(course_id=course_id, student_id=student_id)
    db.session.add(enrollment)
    db.session.commit()
    flash("Successfully enrolled in the course!", "success")
    return redirect(url_for("courses"))

@app.route('/unenroll/<int:course_id>', methods=['POST'])
@login_required
def unenroll(course_id):
    # Ensure the user is a student
    if current_user.user_type != "student":
        flash("Only students can unenroll from courses.", "danger")
        return redirect(url_for('courses'))

    # Get the student's record
    student = Students.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash("Student record not found.", "danger")
        return redirect(url_for('courses'))

    # Find the enrollment record
    enrollment = CourseEnrollment.query.filter_by(course_id=course_id, student_id=student.id).first()
    if not enrollment:
        flash("You are not enrolled in this course.", "warning")
        return redirect(url_for('courses'))

    # Remove the enrollment record
    db.session.delete(enrollment)
    db.session.commit()
    flash("Successfully unenrolled from the course.", "success")
    return redirect(url_for('courses'))

@app.route('/my_courses', methods=['GET', 'POST'])
@login_required
def my_courses():
    # Ensure the user is a teacher
    if current_user.user_type != "teacher":
        flash("Only teachers can manage their courses.", "danger")
        return redirect(url_for('courses'))

    # Get the teacher's record
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash("Teacher record not found.", "danger")
        return redirect(url_for('courses'))
    
    # Handle deleting a course
    if request.method == 'POST' and 'delete_course' in request.form:
        course_id = int(request.form.get('delete_course'))
        course = Courses.query.get(course_id)
        if course and course.teacher_id == teacher.id:
            # Delete the course and related enrollments
            CourseEnrollment.query.filter_by(course_id=course_id).delete()
            db.session.delete(course)
            db.session.commit()
            flash("Course deleted successfully.", "success")
        else:
            flash("You can only delete your own courses.", "danger")
        return redirect(url_for('my_courses'))

    # Fetch all courses owned by the teacher
    teacher_courses = Courses.query.filter_by(teacher_id=teacher.id).all()

    return render_template('my_courses.html', teacher=teacher, teacher_courses=teacher_courses)

@app.route('/add_course', methods=['GET', 'POST'])
@login_required
def add_course():
    # Ensure the user is a teacher
    if current_user.user_type != "teacher":
        flash("Only teachers can add courses.", "danger")
        return redirect(url_for('courses'))

    # Get the teacher's record
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash("Teacher record not found.", "danger")
        return redirect(url_for('courses'))

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        if not course_name:
            flash("Course name cannot be empty.", "danger")
        else:
            new_course = Courses(name=course_name, teacher_id=teacher.id)
            db.session.add(new_course)
            db.session.commit()
            flash("Course added successfully.", "success")
            return redirect(url_for('my_courses'))

    return render_template('add_course.html')

@app.route('/course/<int:course_id>', methods=['GET'])
@login_required
def course_page(course_id):
    # Query the course by ID
    course = Courses.query.get(course_id)
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for('courses'))

    # Check if the current user is enrolled in the course
    student = Students.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash("Only students can access this page.", "danger")
        return redirect(url_for('courses'))

    enrollment = CourseEnrollment.query.filter_by(course_id=course.id, student_id=student.id).first()
    if not enrollment:
        flash("You are not enrolled in this course.", "danger")
        return redirect(url_for('courses'))

    # Pass the course to the template
    return render_template('course_page.html', course=course)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

def generate_quiz(topic_text, num_questions=5):
    """Generate quiz questions from a given topic text using Huggingface API."""
    quiz_questions = []
    
    for i in range(num_questions):
        prompt = f"Generate a question from the following text: {topic_text}"
        response = requests.post(
            "https://api-inference.huggingface.co/models/t5-small",
            headers={"Authorization": f"Bearer {os.getenv('huggingface-api-key')}"},
            json={"inputs": prompt, "parameters": {"max_length": 100, "do_sample": True}}
        )
        generated_text = response.json()[0]['generated_text']
        
        quiz_questions.append(generated_text)
    
    return quiz_questions

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz_endpoint():
    data = request.get_json()
    topic_text = data.get("topic_text", "")
    num_questions = data.get("num_questions", 5)

    if not topic_text:
        return jsonify({"error": "Please provide a topic_text"}), 400

    quiz_questions = generate_quiz(topic_text, num_questions)
    
    return jsonify({"quiz_questions": quiz_questions})

@app.route('/progress/<int:student_id>')
def get_progress(student_id):
    # Query to calculate the average score for each topic for the given student
    results = (
        db.session.query(Student_Progress.topic, db.func.avg(Student_Progress.score).label('avg_score'))
        .filter(Student_Progress.student_id == student_id)
        .group_by(Student_Progress.topic)
        .all()
    )
    # Format the result as a list of dictionaries
    progress = [{'student_id': student_id, 'topic': topic, 'avg_score': avg_score} for topic, avg_score in results]

    return jsonify(progress)
@app.route('/strengths/weakness/<int:student_id>')
def analyze_strengths_weaknesses(student_id):
    results = (
        db.session.query(Student_Progress.topic, db.func.avg(Student_Progress.score).label('avg_score'))
        .filter(Student_Progress.student_id == student_id)
        .group_by(Student_Progress.topic)
        .all()
    )

    strengths = [topic for topic, avg_score in results if avg_score >= 75]
    weaknesses = [topic for topic, avg_score in results if avg_score < 75]

    return {"student_id": student_id, "strengths": strengths, "weaknesses": weaknesses}

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


