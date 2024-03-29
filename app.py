from flask import Flask, render_template, redirect, url_for, flash
from forms import MentorForm
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mentoring.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "my_secret_key"
db = SQLAlchemy(app)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    form = MentorForm()
    if form.validate_on_submit():
        mentor = Mentor(name=form.name.data, job_description=form.job_description.data)
        db.session.add(mentor)
        db.session.commit()
        
        # Create Timeslot instances based on the number entered
        for _ in range(form.timeslots.data):
            timeslot = Timeslot(mentor_id=mentor.id, available=True)
            db.session.add(timeslot)
        
        db.session.commit()
        flash('Mentor registered successfully!', 'success')
        return redirect(url_for('admin'))
    return render_template('admin.html', form=form)


class Mentor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    timeslots = db.relationship('Timeslot', backref='mentor', lazy=True)

class Mentee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ratings = db.relationship('Rating', backref='mentee', lazy=True)

class Timeslot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    available = db.Column(db.Boolean, default=True, nullable=False)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentee_id = db.Column(db.Integer, db.ForeignKey('mentee.id'), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

with app.app_context():
    db.create_all()