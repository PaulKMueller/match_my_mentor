from flask_wtf import FlaskForm, Form
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, SelectField, FormField, FieldList
from wtforms.validators import DataRequired, NumberRange, Optional

class MentorForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
    timeslots = StringField('Timeslots (comma-separated, e.g., 9am-10am, 10am-11am)', validators=[DataRequired()])
    submit = SubmitField('Register Mentor')

class MentorRatingForm(FlaskForm):
    rating = SelectField(
        'Rating',
        choices=[('0', 'Select a ranking')] + [(str(i), str(i)) for i in range(1, 7)],
        validators=[Optional()],
        coerce=int
    )

class MenteeForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    mentor_ratings = FieldList(FormField(MentorRatingForm), min_entries=1)
    submit = SubmitField('Submit Preferences')