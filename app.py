from flask import Flask, render_template, redirect, url_for, flash
from forms import MentorForm, MenteeForm, MentorRatingForm
from flask_sqlalchemy import SQLAlchemy
import qrcode
from flask import send_file
from io import BytesIO
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange, Optional
import base64
from models import db, Mentee, Rating, Mentor, Timeslot



def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mentoring.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = "my_secret_key"

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app

app = create_app()



@app.route("/")
def hello_world():
    return redirect(url_for('qr_codes'))

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
    
    # Query all mentors and their timeslots
    mentors_with_timeslots = Mentor.query.all()

    # Prepare data for the template
    mentors_data = []
    for mentor in mentors_with_timeslots:
        timeslots = ', '.join([str(timeslot.timeslot) for timeslot in mentor.timeslots])
        mentors_data.append({'mentor': mentor, 'timeslots': timeslots})
    
        mentees_with_rankings = Mentee.query.all()

    # Prepare data for the template
    mentees_data = []
    for mentee in mentees_with_rankings:
        rankings = {rating.mentor_id: rating.rating for rating in mentee.ratings}
        mentees_data.append({'mentee': mentee, 'rankings': rankings})

    return render_template('admin.html', form=form, mentors_data=mentors_data, mentees_data=mentees_data)

@app.route('/qr_codes')
def qr_codes():
    # Replace the URL below with the actual route to your mentee form
    mentee_form_url = url_for('mentee_form', _external=True)
    mentor_form_url = url_for('mentor_form', _external=True)

    # Create QR for mentee
    qr_mentee = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr_mentee.add_data(mentee_form_url)
    qr_mentee.make(fit=True)
    img_mentee = qr_mentee.make_image(fill_color="black", back_color="white")
    img_io_mentee = BytesIO()
    img_mentee.save(img_io_mentee, 'JPEG')
    img_io_mentee.seek(0)
    qr_mentee_data = base64.b64encode(img_io_mentee.getvalue()).decode()

    # Create QR for mentor
    qr_mentor = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr_mentor.add_data(mentor_form_url)
    qr_mentor.make(fit=True)
    img_mentor = qr_mentor.make_image(fill_color="black", back_color="white")
    img_io_mentor = BytesIO()
    img_mentor.save(img_io_mentor, 'JPEG')
    img_io_mentor.seek(0)
    qr_mentor_data = base64.b64encode(img_io_mentor.getvalue()).decode()

    # Pass the QR data to the template
    return render_template('qr_codes.html', qr_mentee=qr_mentee_data, qr_mentor=qr_mentor_data)


@app.route('/confirmation_page')
def confirmation_page():
    return render_template('confirmation_page.html')

@app.route('/mentor_form', methods=['GET', 'POST'])
def mentor_form():
    form = MenteeForm()
    mentors = Mentor.query.all()
    
    if not form.is_submitted():
        for mentor in mentors:
            mentor_form = MentorRatingForm()
            form.mentor_ratings.append_entry(mentor_form)

        mentor_names = [mentor.name for mentor in mentors]
        mentors_and_forms = zip(mentor_names, form.mentor_ratings)

        return render_template('mentor_form.html', form=form, mentors_and_forms=mentors_and_forms)
    else:
        # Form submission logic remains the same
        if form.validate_on_submit():
            mentee = Mentee(name=form.name.data)
            db.session.add(mentee)
            db.session.commit()  # Commit to get the mentee ID

            for mentor_form, mentor in zip(form.mentor_ratings.entries, mentors):
                rating_value = mentor_form.form.rating.data
                if rating_value:  # Assuming '0' means no rating given
                    rating = Rating(mentee_id=mentee.id, mentor_id=mentor.id, rating=rating_value)
                    db.session.add(rating)

            db.session.commit()
            flash('Preferences submitted successfully!', 'success')
            return redirect(url_for('confirmation_page'))

    # If form not submitted, re-fetch mentors for consistency
    return redirect(url_for('confirmation_page'))


@app.route('/mentee_form', methods=['GET', 'POST'])
def mentee_form():
    form = MenteeForm()
    mentors = Mentor.query.all()
    
    if not form.is_submitted():
        for mentor in mentors:
            mentor_form = MentorRatingForm()
            form.mentor_ratings.append_entry(mentor_form)

        mentor_names = [mentor.name for mentor in mentors]
        mentors_and_forms = zip(mentor_names, form.mentor_ratings)

        return render_template('mentee_form.html', form=form, mentors_and_forms=mentors_and_forms)
    else:
        # Form submission logic remains the same
        if form.validate_on_submit():
            mentee = Mentee(name=form.name.data)
            db.session.add(mentee)
            db.session.commit()  # Commit to get the mentee ID

            for mentor_form, mentor in zip(form.mentor_ratings.entries, mentors):
                rating_value = mentor_form.form.rating.data
                if rating_value:  # Assuming '0' means no rating given
                    rating = Rating(mentee_id=mentee.id, mentor_id=mentor.id, rating=rating_value)
                    db.session.add(rating)

            db.session.commit()
            flash('Preferences submitted successfully!', 'success')
            return redirect(url_for('confirmation_page'))

    return redirect(url_for('confirmation_page'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
