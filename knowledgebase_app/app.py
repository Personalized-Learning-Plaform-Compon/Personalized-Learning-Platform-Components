from datetime import datetime, timedelta
import os
import requests
import re
import json
from io import BytesIO
from flask import Flask, render_template, redirect, url_for, flash, session, jsonify, request, send_from_directory, send_file
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_socketio import SocketIO, emit
import time
from dotenv import load_dotenv
from werkzeug.utils import secure_filename, safe_join
import markdown
from flask_migrate import Migrate
from sqlalchemy import func, distinct
import openai 
from openai import OpenAI
from forms import LoginForm, RegistrationForm, StudentProfileForm
from models import User, db, Students, Student_Progress, Quizzes, Teachers, Courses, CourseEnrollment, Folder, CourseContent, CourseFeedback
from recommendations import fetch_youtube_videos, fetch_google_sites
from supabase import create_client, Client
from sqlalchemy.orm.attributes import flag_modified


from generate_quiz import generate_quiz_from_openai

# Automatically set FLASK_ENV to "development" if not explicitly set
if os.getenv("FLASK_ENV") is None:
    os.environ["FLASK_ENV"] = "development"

# Load environment variables from .env file
app = Flask(__name__)
socketio = SocketIO(app)
env_file = os.path.join('..', '.env')
load_dotenv(env_file, override=True)
openai.api_key = os.getenv("OPENAI_API_KEY")
if os.getenv("FLASK_ENV") == 'testing':
    env_file = '.env.test'
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"  # Use an in-memory test DB
    app.config["SECRET_KEY"] = "testing"  # Set a secret key for the session
else:
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {"pdf", "txt", "doc", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize database and migration support
db.init_app(app)
migrate = Migrate(app, db)
openai_client = openai.OpenAI()

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Function to create files storable into AI agent
def create_file(openai_client, file_path):
    if file_path.startswith("http://") or file_path.startswith("https://"):
        # Download the file content from the URL
        response = requests.get(file_path)
        file_content = BytesIO(response.content)
        file_name = file_path.split("/")[-1]
        file_tuple = (file_name, file_content)
        result = openai_client.files.create(
            file=file_tuple,
            purpose="assistants"
        )
    else:
        # Handle local file path
        with open(file_path, "rb") as file_content:
            result = openai_client.files.create(
                file=file_content,
                purpose="assistants"
            )
    return result.id

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
            flash('Login Failed! Please check your credentials.', 'danger')
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
    
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    student = Students.query.filter_by(user_id=user.id).first()
    formatted_learning_methods = session.get('formatted_learning_methods', None)
    
    form = StudentProfileForm()
    
    return render_template('profile.html', user=user, student=student, form=form, formatted_learning_methods=formatted_learning_methods)
@app.route('/update_learning_style', methods=['POST'])
@login_required
def update_learning_style():
    user_id = session.get('_user_id')
    if user_id is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    student = Students.query.filter_by(user_id=user.id).first()
    if student is None:
        flash('Student not found.', 'danger')
        return redirect(url_for('profile'))
    
    form = StudentProfileForm()
    if form.validate_on_submit():
        try:
            student.learning_style = form.learning_style.data
            db.session.commit()
            prompt = f"Generate ways to learn based on the {student.learning_style} learning style. (brief)"
            response = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{"role": "system", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            learning_methods = response.choices[0].message.content
            formatted_learning_methods = format_learning_methods(learning_methods)
            session['formatted_learning_methods'] = formatted_learning_methods
            flash('Learning style updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"Error occurred: {e}")
            flash('An error occurred while updating learning style. Please try again.', 'danger')
    else:
        print(form.errors)  # Debugging: Print form errors to the console
    
    return redirect(url_for('profile'))

@app.route('/update_learning_pace', methods=['POST'])
@login_required
def update_learning_pace():
    user_id = session.get('_user_id')
    if user_id is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found. Please try again.", 'danger')
        return redirect(url_for('login'))
    
    student = Students.query.filter_by(user_id=user.id).first()
    if student is None:
        flash('Student not found.', 'danger')
        return redirect(url_for('profile'))
    
    form = StudentProfileForm()
    if form.validate_on_submit():
        try:
            student.learning_pace = form.learning_pace.data
            db.session.commit()
            flash('Learning pace updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"Error occurred: {e}")
            flash('An error occurred while updating learning pace. Please try again.', 'danger')
    else:
        print(form.errors)  # Debugging: Print form errors to the console
    
    return redirect(url_for('profile'))

def format_learning_methods(text):
    # Split text into individual points based on numbering
    items = re.split(r'\d+\.\s\*\*(.*?)\*\*:\s', text)[1:]  # Extract headers & descriptions
    
    formatted_list = []
    for i in range(0, len(items), 2):  # Process in pairs (title, description)
        title = items[i].strip()
        description = items[i + 1].strip()
        formatted_list.append(f"<li><strong>{title}</strong>: {description}</li>")
    
    return "<ul>" + "".join(formatted_list) + "</ul>"

@app.route('/course/<int:course_id>/progress')
@login_required
def course_progress(course_id):
    course = Courses.query.get_or_404(course_id)
    # Get the current student instance
    student = Students.query.filter_by(user_id=current_user.id).first()
    # Check if progress exists
    progress = Student_Progress.query.filter_by(student_id=student.id, course_id=course_id).first()
    if not progress:
        progress = Student_Progress(
            student_id=student.id,
            quiz_id=1,
            score=0,
            topic="initial progress",
            time_spent=0,
            action="",
            attempt_date=datetime.now(),
            course_id=course_id
        )
        db.session.add(progress)
        db.session.commit() 

    competencies = progress.python_intro_competencies
    topics = [i.lower() for i in competencies.keys()]
    for topic in topics:
        update_progress(student, topic, progress)

    
    # Add any additional logic or data to pass to the template
    return render_template('course_progress.html', course=course, student=student, progress=progress, competencies=competencies)

def capitalize_important_words(text):
    # List of words to exclude from capitalization
    unimportant_words = {"and", "of", "in", "on", "at", "to", "for", "with", "a", "an", "the", "by", "from"}
    
    # Split the text into words
    words = text.split()
    
    # Capitalize the first and last word, and important words
    capitalized_words = [
        word.capitalize() if i == 0 or i == len(words) - 1 or word.lower() not in unimportant_words else word.lower()
        for i, word in enumerate(words)
    ]
    
    # Join the words back into a single string
    return " ".join(capitalized_words)

@app.template_filter('title_case')
def title_case_filter(text):
    return capitalize_important_words(text)

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user
    student = Students.query.filter_by(user_id=user.id).first()
    

    if not student:
        flash('Student not found. Please try again.', 'danger')
        return redirect(url_for('profile'))

    # Retrieve courses along with teacher information
    enrolled_courses = (
        db.session.query(Courses, Teachers)
        .join(CourseEnrollment, Courses.id == CourseEnrollment.course_id)
        .join(Teachers, Courses.teacher_id == Teachers.id)
        .filter(CourseEnrollment.student_id == student.id)
        .all()
    )

    return render_template('dashboard.html', user=user, courses=enrolled_courses)



@app.route('/survey')
def survey():
    return render_template('survey.html')

@app.route('/courses', methods=['GET'])
@login_required
def courses():
    all_courses = db.session.query(Courses, Teachers).join(Teachers, Courses.teacher_id == Teachers.id).all()

    # Get the current student instance
    student = Students.query.filter_by(user_id=current_user.id).first()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("dashboard"))

    # Get list of enrolled course IDs for the current student
    enrolled_courses = [enrollment.course_id for enrollment in CourseEnrollment.query.filter_by(student_id=student.id).all()]

    return render_template('courses.html', courses=all_courses, enrolled_courses=enrolled_courses)


@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    # Ensure the logged-in user is a student
    if current_user.user_type != "student":
        flash("Only students can enroll in courses.", "danger")
        return redirect(url_for("profile"))

    # Retrieve the student's entry based on the logged-in user's ID
    student = Students.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("profile"))

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
        return redirect(url_for('profile'))

    # Get the student's record
    student = Students.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash("Student record not found.", "danger")
        return redirect(url_for('profile'))

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
        return redirect(url_for('profile'))

    # Get the teacher's record
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash("Teacher record not found.", "danger")
        return redirect(url_for('profile'))
    
    # Handle deleting a course
    if request.method == 'POST' and 'delete_course' in request.form:
        course_id = int(request.form.get('delete_course'))
        course = Courses.query.get(course_id)
        if course and course.teacher_id == teacher.id:

            # Remove course vector store
            if course.vector_store_id:
                try:
                    openai_client.vector_stores.delete(course.vector_store_id)
                except openai.OpenAIError as e:
                    flash(f"Error deleting vector store: {str(e)}", "danger")

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
        return redirect(url_for('profile'))

    # Get the teacher's record
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash("Teacher record not found.", "danger")
        return redirect(url_for('profile'))

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        if not course_name:
            flash("Course name cannot be empty.", "danger")
        else:
            # Create new vector store for new course
            try:
                vector_store = openai_client.vector_stores.create(
                    name=f"{course_name} by {teacher.name} "
                )
            except openai.OpenAIError as e:
                flash(f"Error creating vector store: {str(e)}", "danger")
                return redirect(url_for('add_course'))

            # Add course to database
            new_course = Courses(name=course_name, teacher_id=teacher.id, vector_store_id=vector_store.id)
            db.session.add(new_course)
            db.session.commit()

            flash("Course added successfully.", "success")
            return redirect(url_for('my_courses'))

    return render_template('add_course.html')

@app.route('/course/<int:course_id>', methods=['GET'])
@login_required
def course_page(course_id):
    # Query the course by ID
    course = Courses.query.get_or_404(course_id)
    student = Students.query.filter_by(user_id=current_user.id).first()
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for('dashboard'))

    # Check if the current user is enrolled in the course
    student = Students.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash("Only students can access this page.", "danger")
        return redirect(url_for('profile'))

    enrollment = CourseEnrollment.query.filter_by(course_id=course.id, student_id=student.id).first()
    if not enrollment:
        flash("You are not enrolled in this course.", "danger")
        return redirect(url_for('courses'))
    # Get all content related to the student's learning style
    content = course.content
    #suggested_content = [file for file in content if file.category in student.learning_style.lower()]
    suggested_content = []
    for file in content:
        if file.category:
            categories = file.category.split(",")
            for category in categories:
                if category.strip().lower() in student.learning_style.lower():
                    suggested_content.append(file)
    yt_links = None
    google_links = None
    if student.learning_style == 'Visual' or student.learning_style == 'Auditory':
        recs = fetch_youtube_videos('python')
        yt_links = [i['url'] for i in recs]
    elif student.learning_style == 'Reading/Writing':
        recs = fetch_google_sites('python')
        google_links = [(i['url'], i['title']) for i in recs]
    else:
        recs = fetch_google_sites('python challenges')
        google_links = [(i['url'], i['title']) for i in recs]

    progress = Student_Progress.query.filter_by(student_id=student.id, course_id=course_id).first()
    if not progress:
        progress = Student_Progress(
            student_id=student.id,
            quiz_id=1,
            score=0,
            topic="initial progress",
            time_spent=0,
            action="",
            attempt_date=datetime.now(),
            course_id=course_id
        )
        db.session.add(progress)
        db.session.commit() 
    competencies = [capitalize_important_words(i[0]) for i in progress.python_intro_competencies.items()]
    # Pass the course to the template
    return render_template('course_page.html', course=course, suggested_content=suggested_content, student=student, recs=recs, yt_links=yt_links, google_links=google_links, competencies=competencies)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/course/<int:course_id>/upload', methods=['POST'])
@login_required
def upload_content(course_id):
    if current_user.user_type != "teacher":
        flash("Only instructors can upload files.", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    if "file" not in request.files:
        flash("No file part", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    file = request.files["file"]
    file_name = request.form.get("file_name")
    folder_id = request.form.get("folder_id")
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()
    content_types = ','.join(request.form.getlist('category'))

    if not file or file.filename == "":
        flash("No selected file", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    if not allowed_file(file.filename):
        flash("File type not allowed.", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    file_extension = file.filename.rsplit('.', 1)[1].lower()
    bucket_name = "course-content"

    # Ensure folder exists
    if not folder_id:
        flash("No folder selected.", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    folder = Folder.query.get(folder_id)
    if not folder or folder.course_id != course_id:
        flash("Invalid folder selected.", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    folder_name = folder.name

    # Define paths
    local_folder_path = os.path.join(app.config["UPLOAD_FOLDER"], f"course_{course_id}", folder_name)
    local_file_path = os.path.join(local_folder_path, secure_filename(file_name + '.' + file_extension))
    supabase_file_path = f"course_{course_id}/{folder_name}/{file_name}.{file_extension}"

    try:
        # Ensure local folder exists
        os.makedirs(local_folder_path, exist_ok=True)

        # Save locally first
        file.save(local_file_path)

        # Determine the MIME type based on the file extension
        mime_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        content_type = mime_types.get(file_extension, "application/octet-stream")

        # Upload to Supabase
        with open(local_file_path, "rb") as file_data:
            res = supabase.storage.from_(bucket_name).upload(supabase_file_path, file_data, {'content-type': content_type})

        if not res:
            flash("Error uploading file to Supabase Storage.", "danger")
            os.remove(local_file_path)  # Cleanup
            return redirect(url_for('manage_course', course_id=course_id))

        # Get course vector store
        course = db.session.get(Courses, course_id)
        if not course or not course.vector_store_id:
            flash("Error: Course not found or vector store not initialized.", "danger")
            os.remove(local_file_path)
            return redirect(url_for('manage_course', course_id=course_id))

        vector_store_id = course.vector_store_id

        # Upload to Vector Store
        try:
            vector_store_file_id = create_file(openai_client, local_file_path)
            if vector_store_file_id:
                openai_client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=vector_store_file_id
                )
            else:
                flash("Error uploading file to vector store.", "danger")
        except openai.OpenAIError as e:
            flash(f"Vector store upload failed: {str(e)}", "danger")

        # Remove local file
        os.remove(local_file_path)

        # Save to Database
        content = CourseContent.query.filter_by(
            course_id=course_id, folder_id=folder_id, filename=file_name
        ).first()

        if content:
            content.file_url = supabase_file_path
            content.category = content_types
        else:
            content = CourseContent(
                filename=file_name,
                file_url=supabase_file_path,
                course_id=course_id,
                folder_id=folder_id,
                teacher_id=teacher.id,
                category=content_types,
                file_extension=file_extension,
                vector_store_file_id=vector_store_file_id
            )
            db.session.add(content)

        db.session.commit()
        flash("File uploaded successfully!", "success")

    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "danger")

    return redirect(url_for('manage_course', course_id=course_id))

@app.route('/upload_youtube/<int:course_id>', methods=['POST'])
@login_required
def upload_youtube(course_id):
    youtube_url = request.form.get('youtube_url')
    youtube_title = request.form.get('youtube_title')
    folder_id = request.form.get('folder_id')
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()
    categories = request.form.getlist('category')

    if not youtube_url or not youtube_title:
        flash("Please provide both a YouTube URL and a title.", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    youtube_id = extract_youtube_id(youtube_url)
    if not youtube_id:
        flash("Invalid YouTube URL.", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    # Save YouTube link as a 'course_content' entry with 'youtube' extension
    new_content = CourseContent(
        filename=youtube_title,
        file_url=f"https://www.youtube.com/embed/{youtube_id}",
        file_extension="youtube",
        course_id=course_id,
        folder_id=folder_id,
        teacher_id=teacher.id,
        category=",".join(categories)
    )
    db.session.add(new_content)
    db.session.commit()
    

    flash("YouTube video added successfully!", "success")
    return redirect(url_for('manage_course', course_id=course_id))

@app.route('/view_file/<int:content_id>')
@login_required
def view_file(content_id):
    content = CourseContent.query.get(content_id)
    if not content:
        flash("File not found.", "danger")
        return redirect(url_for('profile'))

    # If it's a YouTube video, don't generate a signed URL
    if content.file_extension == "youtube":
        return render_template('view_file.html', 
                               file_url=content.file_url, 
                               file_extension=content.file_extension, 
                               filename=content.filename, 
                               youtube=True)  # Pass 'youtube' flag

    bucket_name = "course-content"
    file_path = content.file_url  # This is the stored file path in Supabase

    # Generate a signed URL (valid for 1 hour)
    try:
        signed_url_data = supabase.storage.from_(bucket_name).create_signed_url(file_path, 3600)
        signed_url = signed_url_data.get('signedURL') or signed_url_data.get('signedUrl')  # Extract the actual URL
    except Exception as e:
        flash(f"Error generating file link: {str(e)}", "danger")
        return redirect(url_for('profile'))

    return render_template('view_file.html', file_url=signed_url, file_extension=content.file_extension, filename=content.filename)

# Helper function to extract YouTube video ID
def extract_youtube_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None

@app.route("/create_folder", methods=["POST"])
@login_required
def create_folder():
    course_id = request.form.get("course_id")
    folder_name = request.form.get("folder_name")

    # Ensure the teacher owns this course
    course = Courses.query.get(course_id)
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()

    if not course or course.teacher_id != teacher.id:
        flash("You do not have permission to manage this course.", "danger")
        return redirect(url_for("my_courses"))

    # Check if folder already exists in DB
    existing_folder = Folder.query.filter_by(name=folder_name, course_id=course_id).first()
    if existing_folder:
        flash("Folder already exists in this course.", "warning")
        return redirect(url_for("manage_course", course_id=course_id))

    # Save folder in DB, including teacher_id
    new_folder = Folder(name=folder_name, course_id=course_id, teacher_id=teacher.id)
    db.session.add(new_folder)
    db.session.commit()

    flash("Folder created successfully!", "success")
    return redirect(url_for("manage_course", course_id=course_id))

@app.route('/folder/<int:folder_id>')
@login_required
def view_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    course = Courses.query.get(folder.course_id)
    content = CourseContent.query.filter_by(folder_id=folder.id).all()  # Fetch files

    # Check if the user has permission to access this folder
    if current_user.user_type == "teacher":
        teacher = Teachers.query.filter_by(user_id=current_user.id).first()
        if folder.teacher_id != teacher.id:
            flash("You do not have permission to view this folder.", "danger")
            return redirect(url_for("my_courses"))

    elif current_user.user_type == "student":
        student = Students.query.filter_by(user_id=current_user.id).first()
        enrollment = CourseEnrollment.query.filter_by(student_id=student.id, course_id=course.id).first()
        if not enrollment:
            flash("You do not have access to this folder.", "danger")
            return redirect(url_for("courses"))

    return render_template("folder_page.html", folder=folder, course=course, user=current_user, content=content)


@app.route('/course/<int:course_id>/manage', methods=['GET', 'POST'])
@login_required
def manage_course(course_id):
    course = Courses.query.get_or_404(course_id)

    # Retrieve the teacher entry linked to the current user
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()

    if not teacher or course.teacher_id != teacher.id:
        flash("You do not have permission to manage this course.", "danger")
        return redirect(url_for("my_courses"))

    # Fetch all folders and content related to the course
    folders = Folder.query.filter_by(course_id=course_id).all()
    content = CourseContent.query.filter_by(course_id=course_id, folder_id=None).all()  # Files not in folders

    return render_template("manage_course.html", course=course, folders=folders, content=content)

@app.route("/delete_file", methods=["POST"])
@login_required
def delete_file():
    file_id = request.form.get("file_id")
    content = CourseContent.query.get(file_id)

    if not content:
        flash("File not found.", "danger")
        return redirect(url_for("manage_course", course_id=content.course_id))

    course = Courses.query.get(content.course_id)
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()

    if course.teacher_id != teacher.id:
        flash("You do not have permission to delete this file.", "danger")
        return redirect(url_for("manage_course", course_id=content.course_id))

    # If it's not a YouTube video, delete it from cloud storage
    if content.file_extension != "youtube":
        bucket_name = "course-content"
        try:
            response = supabase.storage.from_(bucket_name).remove([content.file_url])
        except Exception as e:
            flash(f"Error deleting file from cloud storage: {str(e)}", "danger")
            return redirect(url_for("manage_course", course_id=content.course_id))

        # Remove file from vector store if applicable
        if content.vector_store_file_id:
            try:
                openai_client.vector_stores.files.delete(
                    vector_store_id=course.vector_store_id,
                    file_id=content.vector_store_file_id
                )
                openai_client.files.delete(content.vector_store_file_id)
            except openai.OpenAIError as e:
                flash(f"Warning: Could not remove file from vector store. Error: {str(e)}", "warning")

    # Remove the file from the database
    db.session.delete(content)
    db.session.commit()

    flash("File deleted successfully!", "success")
    return redirect(url_for("manage_course", course_id=content.course_id))

@app.route("/delete_folder", methods=["POST"])
@login_required
def delete_folder():
    folder_id = request.form.get("folder_id")
    folder = Folder.query.get(folder_id)

    if not folder:
        flash("Folder not found.", "danger")
        return redirect(url_for("manage_course", course_id=folder.course_id))

    course = Courses.query.get(folder.course_id)
    teacher = Teachers.query.filter_by(user_id=current_user.id).first()

    if course.teacher_id != teacher.id:
        flash("You do not have permission to delete this folder.", "danger")
        return redirect(url_for("manage_course", course_id=folder.course_id))

    # Define bucket name
    bucket_name = "course-content"

    # Get all files in the folder
    files_in_folder = CourseContent.query.filter_by(folder_id=folder_id).all()

    # Separate YouTube videos from actual files
    file_paths = [file.file_url for file in files_in_folder if file.file_extension != "youtube"]

    # Delete actual files from cloud storage
    if file_paths:
        try:
            response = supabase.storage.from_(bucket_name).remove(file_paths)
        except Exception as e:
            flash(f"Error deleting files from cloud storage: {str(e)}", "danger")
            return redirect(url_for("manage_course", course_id=folder.course_id))

    # Delete all files (including YouTube videos) from the database
    for file in files_in_folder:
        db.session.delete(file)

        # Remove from vector store if applicable (not for YouTube)
        if file.file_extension != "youtube" and file.vector_store_file_id:
            try:
                openai_client.vector_stores.files.delete(
                    vector_store_id=course.vector_store_id,
                    file_id=file.vector_store_file_id
                )
                openai_client.files.delete(file.vector_store_file_id)
            except openai.OpenAIError as e:
                flash(f"Warning: Could not remove file from vector store. Error: {str(e)}", "warning")

    # Delete the folder itself from the database
    db.session.delete(folder)
    db.session.commit()

    flash("Folder and its files deleted successfully!", "success")
    return redirect(url_for("manage_course", course_id=folder.course_id))


@app.route('/chat/<int:course_id>')
@login_required
def chat(course_id):
    user_id = session.get('_user_id')
    user = db.session.get(User, user_id)

    course = Courses.query.get_or_404(course_id)  # Fetch the course from the database
    student = Students.query.filter_by(user_id=user.id).first()
    return render_template('chat.html', course=course, student=student)

# Store previous response IDs per user session
user_sessions = {}

@socketio.on('send_message')
def handle_message(data):
    user_message = data.get("message", "")
    courseName = data.get("courseName", "")
    learningStyle = data.get("learningStyle", "")
    learningPace = data.get("learningPace", "")
    vectorStoreId = data.get("vectorStoreId", "").strip()

    # Identify user session (assuming they have a unique session ID)
    user_id = session.get("user_id")  # Use request.sid if user_id isn't stored in session

    # Retrieve previous response ID for context (if exists)
    previous_response_id = user_sessions.get(user_id)

    try:
        # Prepare OpenAI API call
        request_params = {
            "model": "gpt-4o-mini",
            "instructions": f"You are a tutor specializing in {courseName}. "
                            f"Adapt to the student's learning style: {learningStyle} and pace: {learningPace}. "
                            f"Do not answer questions unrelated to the course material. "
                            f"Give your responses in HTML format, and don't include <html>, <meta>, <DOCTYPE>, <title>, <head>, or <body> tags, however, <h> tags are fine.",
            "input": user_message,
            "tools": [{
                "type": "file_search",
                "vector_store_ids": [vectorStoreId],
                "max_num_results": 1
            }],
            "max_output_tokens": 1000,
            "temperature": 0.4
        }

        # Include previous_response_id for follow-ups
        if previous_response_id:
            request_params["previous_response_id"] = previous_response_id

        response = openai_client.responses.create(**request_params)

        # Extract response text
        ai_response = response.output[-1].content[0].text

        # Store the latest response ID for this user session
        user_sessions[user_id] = response.id

        # Emit response back to the client
        emit("receive_message", {"message": ai_response}, broadcast=True)

    except Exception as e:
        emit("receive_message", {"message": f"Error: {str(e)}"})


    # Simulated AI response (Replace this with OpenAI API call)
    # ai_response = """
    #     <h2>Defining a Function in Python</h2>
    #     <p>To define a user-defined function (UDF) in Python, follow these rules:</p>
    #     <ol>
    #         <li><strong>Use the <code>def</code> Keyword:</strong> Start with the keyword <code>def</code>, followed by the function name and parentheses <code>()</code>.</li>
    #         <li><strong>Parameters:</strong> Any parameters or arguments should be placed <br> <br> within the parentheses.</li>
    #         <li><strong>Docstring:</strong> Optionally, the first statement can be a documentation string (docstring) that describes the function.</li>
    #         <li><strong>Colon and Indentation:</strong> The function block starts with a colon <code>:</code> and must be indented.</li>
    #         <li><strong>Return Statement:</strong> Use <code>return [expression]</code> to exit the function, optionally passing back an expression.</li>
    #     </ol>
    #     <h3>Example Function:</h3>
    #     <pre><code>def greet(name):
    #         return f"Hello, {name}!"
    #     </code></pre>
    # """

    # time.sleep(5)  # Simulate processing delay
    # emit('receive_message', {'message': ai_response}, broadcast=True)


@app.route('/generate_quiz', methods=['POST'])
@login_required
def generate_quiz():
    """Generate quiz questions with adaptive difficulty"""
    try:
        data = request.get_json()
        quiz_topic = data.get('quiz_topic')
        
        # Get the current student
        student = Students.query.filter_by(user_id=current_user.id).first()
        if not student:
            return jsonify({"error": "Student record not found"}), 404
        
        # Generate initial questions for the topic
        questions = generate_initial_questions(quiz_topic)
        
        # Add topic to each question for tracking
        for q in questions:
            q['topic'] = quiz_topic
        
        return jsonify({"quiz_questions": questions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


def update_progress(student, topic, progress, quiz=False):
    """Update student progress based on quiz results"""
    competencies = progress.python_intro_competencies
    if quiz:
        topic = topic.lower()
        competencies[topic][1] += 1
        if not student.learning_pace:
            student.learning_pace = 'Normal'
            db.session.commit()
    
    if student.learning_pace == 'Normal':
        if competencies[topic][1] >= 3 and competencies[topic][1] < 6:
            competencies[topic][0] = 'Familiarity'
        elif competencies[topic][1] >= 6 and competencies[topic][1] < 9:
            competencies[topic][0] = 'Competent'
        elif competencies[topic][1] >= 9:
            competencies[topic][0] = 'Mastery'
    elif student.learning_pace == 'Fast':
        if competencies[topic][1] >= 2 and competencies[topic][1] < 4:
            competencies[topic][0] = 'Familiarity'
        elif competencies[topic][1] >= 4 and competencies[topic][1] < 6:
            competencies[topic][0] = 'Competent'
        elif competencies[topic][1] >= 6:
            competencies[topic][0] = 'Mastery'
    else:
        if competencies[topic][1] >= 4 and competencies[topic][1] < 8:
            competencies[topic][0] = 'Familiarity'
        elif competencies[topic][1] >= 8 and competencies[topic][1] < 12:
            competencies[topic][0] = 'Competent'
        elif competencies[topic][1] >= 12:
            competencies[topic][0] = 'Mastery'
    progress.python_intro_competencies = competencies
    flag_modified(progress, "python_intro_competencies")
    db.session.commit()
   




@app.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    """Submit quiz results and update student performance"""
    try:
        data = request.get_json()
        topic = data.get('topic')
        score = data.get('score')
        questions = data.get('questions')
        course_id = data.get('course_id')
        user_answers = data.get('user_answers')
        duration = data.get('duration')
        
        # Get the current student
        student = Students.query.filter_by(user_id=current_user.id).first()
        if not student:
            return jsonify({"error": "Student record not found"}), 404
        
        quiz_result = Quizzes(
            topic=topic,
            score=score,
            difficulty='Medium',
            format='MCQ',
            content=questions,
            courses_id=course_id,
            attempt_date=datetime.now(),
            time_spent=duration,
            student_id=student.id,
        )
        db.session.add(quiz_result)
        db.session.commit()
        progress = Student_Progress.query.filter_by(student_id=student.id, course_id=course_id).first()
        # Update student progress
        if score >= 60:
            update_progress(student, topic, progress, True)
            db.session.commit()
        
        
        # Create a quiz result record
        # quiz_result = QuizResult(
        #     student_id=student.id,
        #     topic=topic,
        #     score=score,
        #     total_questions=len(questions)
        # )
        # db.session.add(quiz_result)
        
        # Optionally, update student's performance metrics
        # This is a placeholder - implement your own logic
        #student.update_performance(topic, score)
        
        #db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Quiz submitted successfully",
            "score": score
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def adjust_difficulty(current_difficulty, was_correct):
    """Adjust difficulty based on whether the previous answer was correct"""
    difficulty_levels = ['Easy', 'Medium', 'Hard', 'Expert']
    
    # Find current index
    try:
        current_index = difficulty_levels.index(current_difficulty)
    except ValueError:
        # Default to Medium if invalid difficulty provided
        current_index = 1
    
    if was_correct:
        # Move up one difficulty level if correct (max at Expert)
        new_index = min(current_index + 1, len(difficulty_levels) - 1)
    else:
        # Move down one difficulty level if incorrect (min at Easy)
        new_index = max(current_index - 1, 0)
    
    return difficulty_levels[new_index]

def generate_initial_questions(quiz_topic, count=5):
    """Generate initial quiz questions at medium difficulty"""
    # For first-time quiz takers, generate questions at medium difficulty
    questions = []
    
    # Use OpenAI to generate questions with difficulty parameter
    openai_questions = generate_quiz_from_openai_with_difficulty(quiz_topic, 'Medium', count)
    
    # Add difficulty metadata to each question
    for i, q in enumerate(openai_questions):
        q['difficulty'] = 'Medium'
        q['question_id'] = f"q_{i}_initial"
        questions.append(q)
    
    return questions

def generate_adaptive_questions(quiz_topic, questions_with_difficulty):
    """Generate new questions based on previous performance"""
    questions = []
    
    # Group questions by difficulty to minimize API calls
    difficulty_groups = {}
    for q in questions_with_difficulty:
        difficulty = q['next_difficulty']
        if difficulty not in difficulty_groups:
            difficulty_groups[difficulty] = 0
        difficulty_groups[difficulty] += 1
    
    # Generate questions for each difficulty level
    question_id_counter = 0
    for difficulty, count in difficulty_groups.items():
        # Generate questions at this difficulty level
        openai_questions = generate_quiz_from_openai_with_difficulty(quiz_topic, difficulty, count)
        
        # Add metadata
        for q in openai_questions:
            q['difficulty'] = difficulty
            q['question_id'] = f"q_{question_id_counter}_adaptive"
            question_id_counter += 1
            questions.append(q)
    
    return questions

def generate_quiz_from_openai_with_difficulty(quiz_topic, difficulty, count=5):
    """Enhanced version of generate_quiz_from_openai that includes difficulty"""
    load_dotenv()
    
    difficulty_descriptions = {
        'Easy': "basic recall and simple application questions suitable for beginners",
        'Medium': "moderate application and analysis questions requiring good understanding",
        'Hard': "challenging questions requiring deep understanding and complex problem-solving",
        'Expert': "very challenging questions requiring mastery and advanced problem-solving skills"
    }
    
    difficulty_desc = difficulty_descriptions.get(difficulty, difficulty_descriptions['Medium'])
    
    CONTENT_PROMPT = f"""
    Hello! You are a Tutor. You are helping a student who wants to improve their understanding in intro to computer science topics.
    Generate {count} {difficulty.lower()} difficulty questions about "{quiz_topic}" in JSON format but not JSON related. 
    
    These should be {difficulty_desc}.
    
    Format as follows: """ + """
    [
        {
            "question":"question text goes here",
            "choices": ["choice 1", "choice 2", "choice 3", "choice 4"],
            "correct_answer":<correct answer index>
        }
    ]
    
    Please only return the JSON object with the questions and choices. Do not include this prompt or any other text.
    Also, please don't include the ```json``` tag in the response. Thank you!
    """
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": CONTENT_PROMPT,
            }
        ],
        model="gpt-4o",
    )
    
    try:
        questions = json.loads(chat_completion.choices[0].message.content)
        return questions
    except Exception as e:
        print(f"Error parsing OpenAI response: {str(e)}")
        # Return empty list in case of error
        return []

@app.route('/quiz')
@login_required
def quiz():
    return render_template('quiz.html')  

@app.route('/milestones/<int:user_id>/<int:course_id>')
def get_course_milestones(user_id, course_id):
    """Calculate course progress based on competencies instead of completed quizzes."""
    
    # Get student
    student = Students.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    # Get student progress for the course
    progress = Student_Progress.query.filter_by(student_id=student.id, course_id=course_id).first()
    if not progress:
        return jsonify({
            "student_id": user_id,
            "course_id": course_id,
            "completed_competencies": 0,
            "total_competencies": 0,
            "completion_percentage": 0
        })

    # Extract competencies (assuming `python_intro_competencies` is a dictionary field)
    competencies = progress.python_intro_competencies
    # Count total and completed competencies
    total_competencies = len(competencies)
    completed_competencies = sum(1 for level, _ in competencies.values() if level in ["Competent", "Mastery"])

    # Calculate percentage progress
    completion_percentage = (completed_competencies / total_competencies * 100) if total_competencies > 0 else 0

    return jsonify({
        "student_id": user_id,
        "course_id": course_id,
        "completed_competencies": completed_competencies,
        "total_competencies": total_competencies,
        "completion_percentage": round(completion_percentage, 1)
    })




@app.route('/strengths/weakness/<int:user_id>')
def analyze_strengths_weaknesses(user_id):
    student = Students.query.filter_by(user_id=user_id).first()
    results = (
        db.session.query(Student_Progress.topic, db.func.avg(Student_Progress.score).label('avg_score'))
        .filter(Student_Progress.student_id == student.id)
        .group_by(Student_Progress.topic)
        .all()
    )
    strengths = [topic for topic, avg_score in results if avg_score >= 75]
    weaknesses = [topic for topic, avg_score in results if avg_score < 75]

    return {"strengths/weaknesses": "strengths/weaknesses", "student_id": user_id, "strengths": strengths, "weaknesses": weaknesses}

@app.route('/recommendations/<int:user_id>')
def recommend_content(user_id):
    from sqlalchemy.orm import aliased

    analysis = analyze_strengths_weaknesses(user_id)
    strengths = analysis['strengths']
    weaknesses = analysis['weaknesses']
   
    student = Students.query.filter_by(user_id=user_id).first()
    # Query quizzes for weak areas
    weak_recommendations = db.session.query(
        Quizzes.quiz_id, Quizzes.topic, Quizzes.difficulty, Student_Progress.score
    ).join(Student_Progress, Student_Progress.quiz_id == Quizzes.quiz_id).filter(
        Quizzes.topic.in_(weaknesses),
        Quizzes.difficulty.in_(['Easy', 'Medium'])  # Recommend easier quizzes for weak areas
    ).all()

    # Query quizzes where the student scored high (e.g., above 80%)
    strong_recommendations = db.session.query(
        Quizzes.quiz_id, Quizzes.topic, Quizzes.difficulty, Student_Progress.score
    ).join(Student_Progress, Student_Progress.quiz_id == Quizzes.quiz_id).filter(
        Student_Progress.student_id == student.id,
        Student_Progress.score > 75  # Threshold for strong performance
    ).all()

    # Separate quizzes into weak and strong areas
    weak_areas_quizzes = set()
    strong_areas_quizzes = set()

    for quiz_id, topic, difficulty, score in weak_recommendations:
        # If student scored high on a "weak topic," move it to strong area instead
        if (quiz_id, topic, difficulty, score) in strong_recommendations:
            strong_areas_quizzes.add((quiz_id, topic, difficulty))
        else:
            weak_areas_quizzes.add((quiz_id, topic, difficulty))

    for quiz_id, topic, difficulty, score in strong_recommendations:
        if {"quiz_id": quiz_id, "topic": topic, "difficulty": difficulty} not in strong_areas_quizzes:
            strong_areas_quizzes.add((quiz_id, topic, difficulty))
            
    weak_areas_quizzes = [{"quiz_id": q[0], "topic": q[1], "difficulty": q[2]} for q in weak_areas_quizzes]
    strong_areas_quizzes = [{"quiz_id": q[0], "topic": q[1], "difficulty": q[2]} for q in strong_areas_quizzes]
    return jsonify({
        "student_id": user_id,
        "weak_areas_quizzes": weak_areas_quizzes,
        "strong_areas_quizzes": strong_areas_quizzes
    })

@app.route('/balanced_recommendations/<int:student_id>')
def balanced_recommendations(student_id):
    weak_recommendations = db.session.query(
       Student_Progress.quiz_id, Student_Progress.topic, Student_Progress.time_spent

    ).filter(
        Student_Progress.student_id == student_id,
        Student_Progress.time_spent < 90,  # High engagement
        Student_Progress.action == 'complete'
    ).limit(2).all()
    # Fetch strengths based on high completion & long time spent
    strong_recommendations = db.session.query(
         Student_Progress.quiz_id, Student_Progress.topic, Student_Progress.time_spent
    ).filter(
        Student_Progress.student_id == student_id,
        Student_Progress.time_spent > 180,  # High engagement
        Student_Progress.action == 'complete', 
    ).limit(2).all()

    weak_quizzes = [{"topic":x.topic, "quiz_id": x.quiz_id, "time_spent": x.time_spent} for x in weak_recommendations]
    strong_quizzes = [{"topic":r.topic, "quiz_id": r.quiz_id, "time_spent": r.time_spent} for r in strong_recommendations]
    return jsonify({
        "balanced_recommendations": "balanced reommendations",
        "student": student_id,
        "reinforcement quizzes": weak_quizzes,
        "advanced_engagement quizzes": strong_quizzes
    })

@app.route("/submit_feedback", methods=["POST"])
@login_required
def submit_feedback():
    data = request.json
    course_id = data.get("course_id")
    rating = data.get("rating")
    topics_of_interest = data.get("topics_of_interest")
    user_id = current_user.id  

    feedback = CourseFeedback(user_id=user_id, course_id=course_id, rating=rating, topics_of_interest=topics_of_interest)
    db.session.add(feedback)
    db.session.commit()

    return jsonify({"message": "Feedback saved!"}), 200



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)