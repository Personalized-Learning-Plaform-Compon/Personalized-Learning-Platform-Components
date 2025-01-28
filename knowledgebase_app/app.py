from flask import Flask, render_template, redirect, url_for, session, request, flash

app = Flask(__name__)

#stimulated user database
users = {}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
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

@app.route('/register')
def register():
    
    return render_template('register.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)

    