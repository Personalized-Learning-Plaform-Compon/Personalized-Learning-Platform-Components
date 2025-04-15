from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, PasswordField, SubmitField, RadioField
from wtforms.validators import DataRequired, EqualTo, Optional
from wtforms import StringField

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    fname = StringField('First Name', validators=[DataRequired()])
    lname = StringField('Last Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    school = StringField('School', validators=[DataRequired()])
    user_type = RadioField('User Type', choices=[('student', 'Student'), ('teacher', 'Teacher'),  ("program_manager", "Program Manager")], validators=[DataRequired()])
    classification = StringField("Classification (e.g, Freshman, Sophomore, Junior, Senior)", [Optional()])
    submit = SubmitField('Register')

class StudentProfileForm(FlaskForm):
    progress = StringField('Progress')
    feedback = StringField('Feedback')
    preferred_topics = StringField('Preferred Topics')
    strengths = StringField('Strengths')
    weaknesses = StringField('Weaknesses')
    learning_style = SelectField('Learning Style', choices=[
        ('Visual', 'Visual'),
        ('Auditory', 'Auditory'),
        ('Kinesthetic', 'Kinesthetic'),
        ('Reading/Writing', 'Reading/Writing')
    ], validators=[Optional()])
    learning_pace = SelectField('Learning Pace', choices=[
        ('Slow', 'Slow'),
        ('Normal', 'Normal'),
        ('Fast', 'Fast')
    ], validators=[Optional()])
    interests = StringField('Interests', validators=[Optional()])
    classification = RadioField(
        'Classification',
        choices=[
            ('Freshman', 'Freshman'),
            ('Sophomore', 'Sophomore'),
            ('Junior', 'Junior'),
            ('Senior', 'Senior')
        ],
        default='Freshman'  # Set a default value if needed
    )
    submit = SubmitField('Submit')

