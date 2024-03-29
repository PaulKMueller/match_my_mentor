from flask import Flask, render_template, redirect, url_for, flash
from forms import MentorForm, MenteeForm
from flask_sqlalchemy import SQLAlchemy
import qrcode
from flask import send_file
from io import BytesIO


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
        db.session.flush()  # This ensures the mentor has an ID without committing the transaction

        # Process each timeslot and create a new Timeslot object
        timeslots = [timeslot.strip() for timeslot in form.timeslots.data.split(',')]
        for timeslot_str in timeslots:
            timeslot = Timeslot(mentor_id=mentor.id, timeslot=timeslot_str, available=True)
            db.session.add(timeslot)
        
        db.session.commit()
        flash('Mentor and timeslots registered successfully!', 'success')
        return redirect(url_for('admin'))
    
    return render_template('admin.html', form=form)

@app.route('/generate_qr')
def generate_qr():
    # Replace the URL below with the actual route to your mentee form
    mentee_form_url = url_for('mentee_form', _external=True)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(mentee_form_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/mentee_form', methods=['GET', 'POST'])
def mentee_form():
    form = MenteeForm()
    if form.validate_on_submit():
        # Process form data here, such as saving the mentee's ratings
        flash('Thank you for submitting your preferences!', 'success')
        return redirect(url_for('mentee_form'))
    return render_template('mentee_form.html', form=form)




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
    timeslot = db.Column(db.Integer, nullable=False)  # Storing the timeslot as a string
    available = db.Column(db.Boolean, default=True, nullable=False)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentee_id = db.Column(db.Integer, db.ForeignKey('mentee.id'), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

with app.app_context():
    db.create_all()