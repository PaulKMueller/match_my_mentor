from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

db = SQLAlchemy()

mentor_timeslot = db.Table('mentor_timeslot',
    db.Column('mentor_id', db.Integer, db.ForeignKey('mentor.id', ondelete='CASCADE'), primary_key=True),
    db.Column('timeslot_id', db.Integer, db.ForeignKey('time_slot.id', ondelete='CASCADE'), primary_key=True)
)

class Mentor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    job_description = db.Column(db.String(300), nullable=False)
    timeslots = db.relationship(
        'TimeSlot',
        secondary=mentor_timeslot,
        back_populates='mentors',
        cascade="all, delete"
    )
    ratings = db.relationship('Rating', cascade="all, delete", backref='mentor')

class Mentee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ratings = db.relationship('Rating', cascade="all, delete", backref='mentee')

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentee_id = db.Column(db.Integer, db.ForeignKey('mentee.id', ondelete='CASCADE'), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=6)

class TimeSlot(db.Model):
    id = db.Column(db.String, primary_key=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    mentors = db.relationship(
        'Mentor',
        secondary=mentor_timeslot,
        back_populates='timeslots'
    )

# Function to create default ratings for all mentees when a new mentor is added
def create_default_ratings_for_new_mentor(mapper, connection, target):
    mentees = Mentee.query.all()
    for mentee in mentees:
        existing_rating = Rating.query.filter_by(mentee_id=mentee.id, mentor_id=target.id).first()
        if not existing_rating:
            default_rating = Rating(mentee_id=mentee.id, mentor_id=target.id, rating=6)
            db.session.add(default_rating)

# Function to create default ratings for all mentors when a new mentee is added
def create_default_ratings_for_new_mentee(mapper, connection, target):
    mentors = Mentor.query.all()
    for mentor in mentors:
        existing_rating = Rating.query.filter_by(mentee_id=target.id, mentor_id=mentor.id).first()
        if not existing_rating:
            default_rating = Rating(mentee_id=target.id, mentor_id=mentor.id, rating=6)
            db.session.add(default_rating)

# Listen for Mentor and Mentee insert events to trigger default rating creation
event.listen(Mentor, 'after_insert', create_default_ratings_for_new_mentor)
event.listen(Mentee, 'after_insert', create_default_ratings_for_new_mentee)