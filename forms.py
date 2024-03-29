from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class MentorForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
    timeslots = StringField('Timeslots (comma-separated, e.g., 9am-10am, 10am-11am)', validators=[DataRequired()])
    submit = SubmitField('Register Mentor')

class MenteeForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    # Add other fields as necessary, such as ratings for each mentor
    submit = SubmitField('Submit')
