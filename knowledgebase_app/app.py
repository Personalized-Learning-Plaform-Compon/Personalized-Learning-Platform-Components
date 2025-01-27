from flask import Flask, render_template
from flask import Flask,render_template, request
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'seniorproject'
app.config['MYSQL_DB'] = 'test'

mysql = MySQL(app)
 
#Creating a connection cursor (Testing the connection)
# with app.app_context():
#     cursor = mysql.connection.cursor()
    
#     #Executing SQL Statements
#     cursor.execute(''' DROP TABLE IF EXISTS test_table ''')
#     cursor.execute(''' CREATE TABLE test_table (test_field1 INT, test_field2 VARCHAR(100)) ''')
#     cursor.execute(''' INSERT INTO test_table (test_field1, test_field2) VALUES (%s, %s) ''', (1, 2))


    
#     #Saving the Actions performed on the DB
#     mysql.connection.commit()
    
#     #Closing the cursor
#     cursor.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')
    
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Fetch form data
        userDetails = request.form
        password = userDetails['password']
        # Hash the password
        hashed_password = generate_password_hash(password)
        email = userDetails['email']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(email, password) VALUES(%s, %s)",(email, hashed_password))
        mysql.connection.commit()
        cur.close()

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)

    