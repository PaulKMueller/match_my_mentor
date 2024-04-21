from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from .forms import MentorForm, MenteeForm, MentorRatingForm
from flask_sqlalchemy import SQLAlchemy
import qrcode
from flask import send_file, Blueprint
from io import BytesIO
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange, Optional
import base64
from .models import db, Mentee, Rating, Mentor, TimeSlot, SetupInfo
from .data_adapter import prepare_data_for_optimizer
from .optimizer import Optimizer

main = Blueprint('main', __name__)

@main.route("/")
def hello_world():
    return redirect(url_for('main.setup'))

@main.route('/setup', methods=['GET', 'POST'])
def setup():
    setup_info = SetupInfo.query.first()  # Fetch the first setup info record, if it exists
    timeslots = TimeSlot.query.all()  # Query all timeslots

    if request.method == 'POST':
        timeslot_ids = request.form.getlist('timeslot_ids[]')
        start_times = request.form.getlist('start_times[]')
        end_times = request.form.getlist('end_times[]')
        num_mentors = request.form['num_mentors']
        num_participants = request.form['num_participants']

        print(start_times)

         # Loop over the timeslots and handle them accordingly
        for i, (start_time, end_time) in enumerate(zip(start_times, end_times)):
            # If the timeslot ID is present, update the existing timeslot
            if i < len(timeslot_ids) and timeslot_ids[i]:
                timeslot = TimeSlot.query.get(timeslot_ids[i])
                timeslot.start_time = start_time
                timeslot.end_time = end_time
            else:
                # If there's no ID, then it's a new timeslot
                new_timeslot = TimeSlot(start_time=start_time, end_time=end_time)
                db.session.add(new_timeslot)

        if setup_info:
            # Update existing SetupInfo
            print("test")
            setup_info.num_mentors = int(num_mentors)
            setup_info.num_participants = int(num_participants)
        else:
            # Create new SetupInfo instance if none exists
            setup_info = SetupInfo(num_mentors=int(num_mentors), num_participants=int(num_participants))
            db.session.add(setup_info)

        db.session.commit()
        return redirect(url_for('main.qr_code_mentor'))

    # Pass existing data to the template if it exists
    if request.method == 'GET':
        if setup_info and timeslots:
            return render_template('setup.html', setup_info=setup_info, timeslots=timeslots)
        elif setup_info:
            return render_template('setup.html', setup_info=setup_info)
        else:
            return render_template('setup.html')
        
@main.route('/delete-timeslot', methods=['POST'])
def delete_timeslot():
    data = request.json
    timeslot_id = data['id']
    timeslot = TimeSlot.query.get(timeslot_id)
    if timeslot:
        db.session.delete(timeslot)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Timeslot deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Timeslot not found'}), 404

@main.route('/update-mentee-rankings', methods=['POST'])
def update_mentee_rankings():
    data = request.get_json()
    mentee_id = data['mentee_id']
    rankings = data['rankings']

    try:
        for ranking in rankings:
            mentor_id = ranking['mentor_id']
            new_rating = ranking['rating']

            # Find the existing rating or create a new one if it doesn't exist
            rating = Rating.query.filter_by(mentee_id=mentee_id, mentor_id=mentor_id).first()
            if rating:
                rating.rating = new_rating  # Update the existing rating
            else:
                # Create a new rating record if it doesn't exist
                rating = Rating(mentee_id=mentee_id, mentor_id=mentor_id, rating=new_rating)
                db.session.add(rating)

        db.session.commit()  # Commit changes
        return jsonify({'success': True, 'message': 'Rankings updated successfully!'})

    except Exception as e:
        db.session.rollback()  # Roll back in case of error
        return jsonify({'success': False, 'message': 'Failed to update rankings: {}'.format(str(e))}), 500

    
@main.route('/update-mentor', methods=['POST'])
def update_mentor():
    data = request.json
    mentor_id = data['id']
    mentor = Mentor.query.get(mentor_id)
    if mentor:
        mentor.name = data.get('name', mentor.name)
        mentor.job_description = data.get('job_description', mentor.job_description)
        # You would also handle the timeslots here, possibly requiring additional logic

        db.session.commit()
        return jsonify({'message': 'Mentor updated successfully'}), 200
    return jsonify({'message': 'Mentor not found'}), 404


@main.route('/update-mentee', methods=['POST'])
def update_mentee():
    mentee_id = request.json['id']
    new_rating = request.json['rating']
    mentor_id = request.json['mentor_id']
    rating = Rating.query.filter_by(mentee_id=mentee_id, mentor_id=mentor_id).first()
    if rating:
        rating.rating = new_rating
        db.session.commit()
        return jsonify({'message': 'Rating updated successfully'}), 200
    return jsonify({'message': 'Rating not found'}), 404


@main.route('/admin', methods=['GET', 'POST'])
def admin():
    form = MentorForm()
    if form.validate_on_submit():
        mentor = Mentor(name=form.name.data, job_description=form.job_description.data)
        db.session.add(mentor)
        db.session.commit()  # Commit mentor to obtain an ID for them

        # Process each timeslot and create a new Timeslot object
        timeslots = [timeslot.strip() for timeslot in form.timeslots.data.split(',')]
        for timeslot_str in timeslots:
            start_time, end_time = timeslot_str.split('-')
            timeslot = TimeSlot(start_time=start_time, end_time=end_time)
            timeslot.mentors.append(mentor)
            db.session.add(timeslot)
        
        db.session.commit()
        flash('Mentor and timeslots registered successfully!', 'success')
        return redirect(url_for('main.admin'))
    
    # Query all mentors and their timeslots
    mentors_with_timeslots = Mentor.query.all()

    # Prepare data for the template
    mentors_data = []
    for mentor in mentors_with_timeslots:
        timeslots = ', '.join([f"{ts.start_time}-{ts.end_time}" for ts in mentor.timeslots])
        mentors_data.append({'mentor': mentor, 'timeslots': timeslots})
    
    mentees_with_rankings = Mentee.query.all()

    # Prepare data for the template
    mentees_data = []
    for mentee in mentees_with_rankings:
        rankings = {rating.mentor_id: rating.rating for rating in mentee.ratings}
        mentees_data.append({'mentee': mentee, 'rankings': rankings})

    return render_template('admin.html', form=form, mentors_data=mentors_data, mentees_data=mentees_data)

@main.route('/qr_code_mentor')
def qr_code_mentor():
    mentor_form_url = url_for('main.mentor_form', _external=True)

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
    return render_template('qr_codes.html', form_name="Mentor Form", qr_code=qr_mentor_data)

@main.route('/qr_code_mentee')
def qr_code_mentee():
    # Replace the URL below with the actual route to your mentee form
    mentee_form_url = url_for('main.mentee_form', _external=True)

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

    # Pass the QR data to the template
    return render_template('qr_codes.html', form_name="Mentee Form", qr_code=qr_mentee_data)


@main.route('/confirmation_page')
def confirmation_page():
    return render_template('confirmation_page.html')

@main.route('/mentor_form', methods=['GET', 'POST'])
def mentor_form():
    form = MentorForm()
    if form.validate_on_submit():
        mentor = Mentor(
            name=form.name.data,
            job_description=form.job_description.data
        )
        # This assumes timeslot IDs are passed from checkboxes in the form
        selected_timeslots = form.timeslots.data  # List of timeslot IDs
        for timeslot_id in selected_timeslots:
            timeslot = TimeSlot.query.get(timeslot_id)
            if timeslot:
                mentor.timeslots.append(timeslot)

        db.session.add(mentor)
        db.session.commit()
        flash('Mentor and timeslots registered successfully!', 'success')
        return redirect(url_for('main.confirmation_page'))  # Make sure to redirect to a confirmation or another appropriate page

    return render_template('mentor_form.html', form=form)


@main.route('/mentee_form', methods=['GET', 'POST'])
def mentee_form():
    form = MenteeForm()
    mentors = Mentor.query.all()

    if request.method == 'GET':
        for mentor in mentors:
            form.mentor_ratings.append_entry(MentorRatingForm())
    
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
        return redirect(url_for('main.confirmation_page'))
    else:
        print("Form is not valid")
        print(form.errors)
        if request.method == 'POST':
            # Form was submitted but didn't validate
            print("test")
            flash('There was a problem with your submission. Please check your input.', 'error')

    mentor_names = [mentor.name for mentor in mentors]
    mentors_and_forms = zip(mentor_names, form.mentor_ratings)
    return render_template('mentee_form.html', form=form, mentors_and_forms=mentors_and_forms)

@main.route('/matching')
def index():
    # Prepare data for the optimizer
    data = prepare_data_for_optimizer()  # You need to define this based on your needs
    print(data)
    optimizer = Optimizer(data)
    optimizer.solve()

    # Fetch results from the optimizer
    results = optimizer.get_results()  # You would need to add a method to extract formatted results

    return render_template('matching.html', results=results)


if __name__ == "__main__":
    main.run(host='0.0.0.0', port=5000) 