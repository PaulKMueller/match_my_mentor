from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

mentor_timeslot = db.Table('mentor_timeslot',
    db.Column('mentor_id', db.Integer, db.ForeignKey('mentor.id'), primary_key=True),
    db.Column('timeslot_id', db.Integer, db.ForeignKey('time_slot.id'), primary_key=True)
)

class Mentor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    timeslots = db.relationship('TimeSlot', secondary=mentor_timeslot, lazy='dynamic', back_populates='mentors')

class Mentee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ratings = db.relationship('Rating', backref='mentee', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentee_id = db.Column(db.Integer, db.ForeignKey('mentee.id'), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

class TimeSlot(db.Model):
    id = db.Column(db.String, primary_key=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    mentors = db.relationship('Mentor', secondary=mentor_timeslot, lazy='dynamic', back_populates='timeslots')


class SetupInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num_mentors = db.Column(db.Integer, nullable=False)
    num_participants = db.Column(db.Integer, nullable=False)