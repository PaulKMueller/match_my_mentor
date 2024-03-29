from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class MentorForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
    timeslots = IntegerField('Available Timeslots', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Register Mentor')
