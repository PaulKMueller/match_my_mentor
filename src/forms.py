from flask_wtf import FlaskForm
from wtforms import (
    FieldList,
    FormField,
    HiddenField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired, ValidationError

from .models import Mentee, Mentor, TimeSlot


class MentorForm(FlaskForm):
    name = StringField('Mentor Name', validators=[DataRequired()])
    job_description = TextAreaField('Job Description', validators=[DataRequired()])
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
        
class TimeSlotForm(FlaskForm):
    timeslot_id = HiddenField('ID')
    start_time = TimeField('Start Time', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('End Time', format='%H:%M', validators=[DataRequired()])

    def validate_end_time(self, field):
        # print("Validate TimeSlotForm")
        # print(f"TimeSlot validation succeeded: {self.end_time.data > self.start_time.data}")
        if self.end_time.data <= self.start_time.data:
            raise ValidationError('End time must be after start time.')

class TimeSlotsForm(FlaskForm):
    timeslots = FieldList(FormField(TimeSlotForm), min_entries=0)  # To handle a list of time slots
    submit = SubmitField('Submit')
