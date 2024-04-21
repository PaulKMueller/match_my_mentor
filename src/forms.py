from flask_wtf import FlaskForm, Form
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, SelectField, FormField, FieldList, SelectMultipleField
from wtforms.validators import DataRequired, NumberRange, Optional, ValidationError
from .models import Mentee, Mentor, TimeSlot

class MentorForm(FlaskForm):
    name = StringField('Mentor Name', validators=[DataRequired()])
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
    # Assume Timeslot is a model that contains all timeslots
    timeslots = SelectMultipleField('Available Timeslots', choices=[], coerce=int)
    submit = SubmitField('Register')

    def __init__(self, *args, **kwargs):
        super(MentorForm, self).__init__(*args, **kwargs)
        self.timeslots.choices = [(timeslot.id, f"{timeslot.start_time} to {timeslot.end_time}") for timeslot in TimeSlot.query.order_by(TimeSlot.start_time).all()]


    def validate_name(self, field):
        if Mentor.query.filter_by(name=field.data).first():
            raise ValidationError('This name already exists in the database.')

class MentorRatingForm(FlaskForm):
    rating = SelectField(
        'Rating',
        choices=[1, 2, 3, 4, 5, 6],
        validators=[DataRequired()],
        coerce=int
    )

class MenteeForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    mentor_ratings = FieldList(FormField(MentorRatingForm), min_entries=0)
    submit = SubmitField('Submit Preferences')

    def validate_name(self, field):
        if Mentee.query.filter_by(name=field.data).first():
            raise ValidationError('This name already exists in the database.')
