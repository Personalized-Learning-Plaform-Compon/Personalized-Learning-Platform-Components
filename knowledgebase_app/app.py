import os
import requests
import re
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
from forms import LoginForm, RegistrationForm, StudentProfileForm
from models import User, db, Students, Student_Progress, Quizzes, Teachers, Courses, CourseEnrollment, Folder, CourseContent

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
    course = Courses.query.get(course_id)
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
    # Pass the course to the template
    return render_template('course_page.html', course=course, suggested_content=suggested_content, student=student)

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
    file_extension = file.filename.rsplit('.', 1)[1].lower()

    if file.filename == "":
        flash("No selected file", "danger")
        return redirect(url_for('manage_course', course_id=course_id))

    if file and allowed_file(file.filename):

        # If a folder is selected, get the folder name from the database
        if folder_id:
            folder = Folder.query.get(folder_id)
            if folder and folder.course_id == course_id:
                folder_name = folder.name

                # Add file path with new file name + original file extension
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"course_{course_id}", folder_name, secure_filename(file_name + '.' + file_extension))
            else:
                flash("Invalid folder selected.", "danger")
                return redirect(url_for('manage_course', course_id=course_id))
        else:
            flash("No folder selected.", "danger")
            return redirect(url_for('manage_course', course_id=course_id))

        # Check if the file already exists in the folder, and delete it if it does
        if os.path.exists(file_path):
            os.remove(file_path)

        # Create the folder if it doesn't exist
        folder_path = os.path.dirname(file_path)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Save the new file
        file.save(file_path)

        # Save the file info in the database (replace the old entry if needed)
        content = CourseContent.query.filter_by(course_id=course_id, folder_id=folder_id, filename=file_name).first()
        if content:
            content.file_url = file_path  # Update the file path if the file already exists
            content.category = content_types
        else:

            # Save file into vector_store (used for AI tutor) if not existent
            # Ensure course and vector store ID exist
            course = db.session.get(Courses, course_id)
            if not course or not course.vector_store_id:
                flash("Error: Course not found or vector store not initialized.", "danger")
                return redirect(url_for('manage_course', course_id=course_id))

            vector_store_id = course.vector_store_id

            try:
                # Upload file to vector store
                vector_store_file_id = create_file(openai_client, file_path)
                if not vector_store_file_id:
                    flash("Error uploading file to vector store.", "danger")
                    return redirect(url_for('manage_course', course_id=course_id))

                result = openai_client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=vector_store_file_id
                )

            except openai.OpenAIError as e:
                flash(f"Vector store upload failed: {str(e)}", "danger")
                return redirect(url_for('manage_course', course_id=course_id))

            # If the file does not exist in the database, create a new entry
            content = CourseContent(
                filename=file_name,
                file_url=file_path,
                course_id=course_id,
                folder_id=folder_id,
                teacher_id=teacher.id,
                category=content_types,
                file_extension=file_extension,
                vector_store_file_id=vector_store_file_id
            )
            db.session.add(content)
        db.session.commit()

        flash("File uploadeded successfully!", "success")

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

@app.route('/view_file/<int:course_id>/<folder_name>/<filename>/<file_extension>')
@login_required
def view_file(course_id, folder_name, filename, file_extension):
    file_extension = file_extension.lower()
    course = Courses.query.get(course_id)
    # Check if the file is a YouTube video
    if file_extension == "youtube":
        # Construct the YouTube video URL from the database
        content = CourseContent.query.filter_by(course_id=course_id, filename=filename).first()
        if not content:
            flash("Video not found.", "danger")
            return redirect(url_for('profile'))

        return render_template('view_file.html', content=content, youtube=True, course=course, filename=filename)

    # Otherwise, handle normal files (PDF, TXT, DOC, DOCX)
    folder_path = os.path.join(app.config["UPLOAD_FOLDER"], f"course_{course_id}", folder_name)
    stored_filename = (filename + '.' + file_extension).replace(' ', '_')
    file_path = os.path.join(folder_path, stored_filename)
    folder_id = Folder.query.filter_by(course_id=course_id, name=folder_name).first().id
    if not os.path.exists(file_path):
        flash("File not found.", "danger")
        return redirect(url_for('view_folder', folder_id=folder_id))

    # If it's a PDF or TXT, show it in the browser
    if file_extension in ["pdf", "txt"]:
        return render_template('view_file.html', file_url=url_for('serve_file', course_id=course_id, folder_name=folder_name, filename=stored_filename), filename=filename, file_extension=file_extension, course=course)

    # If it's a DOC/DOCX, provide a download link
    elif file_extension in ["doc", "docx"]:
        return render_template('view_file.html', file_url=url_for('download_file', course_id=course_id, folder_name=folder_name, filename=stored_filename), filename=filename, file_extension=file_extension, course=course)

@app.route('/serve_file/<int:course_id>/<folder_name>/<filename>')
@login_required
def serve_file(course_id, folder_name, filename):
    folder_path = os.path.join(app.config["UPLOAD_FOLDER"], f"course_{course_id}", folder_name)
    file_path = os.path.join(folder_path, filename)
    if not os.path.exists(file_path):
        flash("File not found.", "danger")
        return redirect(url_for('profile'))

    # Get file extension
    file_extension = filename.split('.')[-1].lower()

    # Define MIME types
    mimetypes_dict = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }

    mimetype = mimetypes_dict.get(file_extension, "application/octet-stream")

    return send_file(file_path, mimetype=mimetype)

@app.route('/download/<int:course_id>/<folder_name>/<filename>')
@login_required
def download_file(course_id, folder_name, filename):
    folder_path = os.path.join(app.config["UPLOAD_FOLDER"], f"course_{course_id}", folder_name)
    file_path = os.path.join(folder_path, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash("File not found.", "danger")
        return redirect(url_for('profile'))

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

    # Create folder in local storage
    course_path = os.path.join(UPLOAD_FOLDER, f"course_{course_id}")
    folder_path = os.path.join(course_path, folder_name)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    flash("Folder created successfully!", "success")
    return redirect(url_for("manage_course", course_id=course_id))

@app.route('/folder/<int:folder_id>')
@login_required
def view_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    course = Courses.query.get(folder.course_id)
    content = course.content

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

    return render_template("folder_page.html", folder=folder, course=course, user = current_user, content=content)

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

    # Remove the file from the file system
    file_path = content.file_url
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove the file from the database
    db.session.delete(content)
    db.session.commit()

    # Remove file from vector store
    if content.vector_store_file_id:
        try:
            # Try to delete vector_store file
            openai_client.vector_stores.files.delete(
                vector_store_id=course.vector_store_id,
                file_id=content.vector_store_file_id
            )
            openai_client.files.delete(content.vector_store_file_id)
        except openai.OpenAIError as e:
            flash(f"Warning: Could not check vector store files. Error: {str(e)}", "warning")
    else:
        flash("Warning: No vector store file ID found. Skipping vector store deletion.", "warning")

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

    # Delete all files in the folder
    files_in_folder = CourseContent.query.filter_by(folder_id=folder_id).all()
    for file in files_in_folder:
        if os.path.exists(file.file_url):
            os.remove(file.file_url)  # Delete file from the file system
        db.session.delete(file)  # Delete file from the database
        
        # Delete files from vector store
        if file.vector_store_file_id:
            try:
                openai_client.vector_stores.files.delete(
                    vector_store_id=course.vector_store_id,
                    file_id=file.vector_store_file_id
                )
                openai_client.files.delete(file.vector_store_file_id)

            except openai.OpenAIError as e:
                flash(f"Warning: Could not remove file from vector store. Error: {str(e)}", "warning")


    # Delete the folder itself
    db.session.delete(folder)
    db.session.commit()

    # Remove the folder from the file system
    folder_path = os.path.join(app.config["UPLOAD_FOLDER"], f"course_{folder.course_id}", folder.name)
    if os.path.exists(folder_path):
        os.rmdir(folder_path)  # Remove the empty folder

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

@socketio.on('send_message')
def handle_message(data):
    user_message = data.get("message", "")
    courseName = data.get("courseName", "")
    learningStyle = data.get("learningStyle", "")
    learningPace = data.get("learningPace", "")
    vectorStoreId = data.get("vectorStoreId", "").strip()

    try:
        # OpenAI API Call
        response = openai_client.responses.create(
            model="gpt-4o-mini",
            instructions=f"You are a tutor specializing in {courseName}. "
                         f"Adapt to the student's learning style: {learningStyle} and pace: {learningPace}. "
                         f"Do not answer questions unrelated to the course material"
                         f"Give your responses in HTML format, and don't include <html>, <meta>, <DOCTYPE>, <title>, <head>, or <body> tags, however, <h> tags are fine.",
            input=user_message,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vectorStoreId],
                "max_num_results": 1
            }],
            max_output_tokens=1000,
            temperature = 0.4
        )

        ai_response = response.output[-1].content[0].text

        print(response)

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
def generate_quiz_endpoint():
    # Get the topic from the request
    request_body:dict = request.get_json()
    quiz_topic:str = request_body.get("quiz_topic")
        
    if quiz_topic is None:
        return jsonify({"error": "No quiz topic provided."})
    
    # Send a prompt with the topic included to OpenAI
    quiz_questions = generate_quiz_from_openai(quiz_topic)
    
    # TODO: Comment out
    print(f"{quiz_questions=}")
    
    # Return the questions as a JSON response to the user
    return jsonify({"quiz_questions": quiz_questions})




@app.route('/quiz')
@login_required
def quiz():
    return render_template('quiz.html')  

@app.route('/milestones/<int:user_id>/<int:course_id>')
# @login_required
def get_course_milestones(user_id, course_id):
    # Fetch total quizzes in the course
    total_quizzes = db.session.query(Quizzes).filter(
        Quizzes.courses_id == course_id
    ).count()

    # Fetch completed quizzes in the course
    from sqlalchemy import func, distinct

    completed_quizzes = db.session.query(func.count(distinct(Student_Progress.quiz_id))).join(Quizzes).filter(
    Student_Progress.student_id == user_id,
    Student_Progress.action == 'complete',
    Quizzes.courses_id == course_id
).scalar()

    

    completion_percentage = (completed_quizzes / total_quizzes * 100) if total_quizzes > 0 else 0
    

    return jsonify({
        "student_id": user_id,
        "course_id": course_id,
        "completed_quizzes": completed_quizzes,
        "total_quizzes": total_quizzes,
        "completion_percentage": round(completion_percentage, 2)
    })



@app.route('/strengths/weakness/<int:user_id>')
def analyze_strengths_weaknesses(user_id):
    results = (
        db.session.query(Student_Progress.topic, db.func.avg(Student_Progress.score).label('avg_score'))
        .filter(Student_Progress.student_id == user_id)
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
        Student_Progress.student_id == user_id,
        Student_Progress.score > 75  # Threshold for strong performance
    ).all()

    # Separate quizzes into weak and strong areas
    weak_areas_quizzes = []
    strong_areas_quizzes = []

    for quiz_id, topic, difficulty, score in weak_recommendations:
        # If student scored high on a "weak topic," move it to strong area instead
        if (quiz_id, topic, difficulty, score) in strong_recommendations:
            strong_areas_quizzes.append({"quiz_id": quiz_id, "topic": topic, "difficulty": difficulty})
        else:
            weak_areas_quizzes.append({"quiz_id": quiz_id, "topic": topic, "difficulty": difficulty})

    for quiz_id, topic, difficulty, score in strong_recommendations:
        if {"quiz_id": quiz_id, "topic": topic, "difficulty": difficulty} not in strong_areas_quizzes:
            strong_areas_quizzes.append({"quiz_id": quiz_id, "topic": topic, "difficulty": difficulty})

    return jsonify({
        "student_id": user_id,
        "weak_areas_quizzes": weak_areas_quizzes,
        "strong_areas_quizzes": strong_areas_quizzes
    })


    # QuizAlias = aliased(Quizzes)
    
    # # Recommend quizzes for weaknesses (Only quizzes the student hasn't scored well on)
    # weak_recommendations = (
    #     db.session.query(QuizAlias.quiz_id, QuizAlias.topic, QuizAlias.difficulty)
    #     .join(Student_Progress, QuizAlias.quiz_id == Student_Progress.quiz_id)
    #     .filter(Student_Progress.student_id == user_id)
    #     .filter(QuizAlias.topic.in_(weaknesses))
    #     .distinct()
    #     .limit(5)
    #     .all()
    # )

    # # Recommend advanced quizzes for strengths (Only quizzes matching strong topics)
    # strong_recommendations = (
    #     db.session.query(QuizAlias.quiz_id, QuizAlias.topic, QuizAlias.difficulty)
    #     .join(Student_Progress, QuizAlias.quiz_id == Student_Progress.quiz_id)
    #     .filter(Student_Progress.student_id == user_id)
    #     .filter(QuizAlias.topic.in_(strengths))
    #     .distinct()
    #     .limit(5)
    #     .all()
    # )
    
    # return jsonify({
    #     "student_id": user_id,
    #     "weak_areas_quizzes": [{"quiz_id": r[0], "topic": r[1], "difficulty": r[2]} for r in weak_recommendations],
    #     "strong_areas_quizzes": [{"quiz_id": r[0], "topic": r[1], "difficulty": r[2]} for r in strong_recommendations]
    # })
    # return jsonify({"recommendations": "recommendations", "weak_topics": [r[1] for r in weak_recommendations], "student": user_id, "weak_areas_quizzes": [r[0] for r in weak_recommendations], "strong_topics": [r[1] for r in strong_recommendations], "strong_areas_quizzes": [r[0] for r in strong_recommendations]})

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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)