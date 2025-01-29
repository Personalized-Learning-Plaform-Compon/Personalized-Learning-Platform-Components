from flask import Flask, render_template


app = Flask(__name__)

#stimulated user database
users = {}

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

# User ORM for SQLAlchemy
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    fname = db.Column(db.String(50), nullable=False)
    lname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    school = db.Column(db.String(50), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.get(email, None)
        
        if user and user['password'] == password:
            session['user'] = user
            flash('Login Successful!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Login Failed! Please check your credentials', 'danger')
    return render_template('login.html')
    
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Fetch form data
        userDetails = request.form
        fname = userDetails['fname']
        lname = userDetails['lname']
        email = userDetails['email']
        password = userDetails['password']
        school = userDetails['school']
        user_type = userDetails['user-type']
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        # checking if user already exists
        user = Users.query.filter_by(email=email).first()

        if not user:
            try:
                # creating Users object
                user = Users(
                    fname=fname,
                    lname=lname,
                    email=email,
                    password=hashed_password,
                    school=school,
                    user_type=user_type
                )
                # adding the fields to users table
                db.session.add(user)
                db.session.commit()
                # flash success message
                flash('Successfully registered.', 'success')
                return redirect(url_for('register'))
            except Exception as e:
                logging.error(f"Error occurred: {e}")
                flash('Some error occurred!!', 'danger')
                return redirect(url_for('register'))
        else:
            # if user already exists then send status as fail
            flash('User already exists!!', 'warning')
            return redirect(url_for('register'))

    return render_template('register.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)