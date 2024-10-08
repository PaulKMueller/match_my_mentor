import datetime
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from .forms import MentorForm, MenteeForm, MentorRatingForm, TimeSlotsForm
from flask_sqlalchemy import SQLAlchemy
import qrcode
from flask import send_file, Blueprint
from io import BytesIO
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange, Optional
import base64
from .models import db, Mentee, Rating, Mentor, TimeSlot, mentor_timeslot
from .data_adapter import prepare_data_for_optimizer
from .optimizer import Optimizer

main = Blueprint("main", __name__)


@main.route("/")
def hello_world():
    return redirect(url_for("main.setup"))


@main.route("/setup", methods=["GET", "POST"])
def setup():
    form = TimeSlotsForm()

    if request.method == "GET":
        timeslots = TimeSlot.query.all()
        for timeslot in timeslots:
            form.timeslots.append_entry(
                {
                    "timeslot_id": timeslot.id,
                    "start_time": timeslot.start_time,
                    "end_time": timeslot.end_time,
                }
            )
    if request.method == "POST":
        # Handle form submission
        print(f"Form could be validated: {form.validate_on_submit()}")
        if form.validate_on_submit():
            for entry in form.timeslots:
                start_time = entry.start_time.data
                end_time = entry.end_time.data
                start_time_string = entry.start_time.data.strftime('%H%M')
                end_time_string = entry.end_time.data.strftime('%H%M')

                timeslot_id = f"{start_time_string}{end_time_string}"

                timeslot = TimeSlot.query.get(timeslot_id)
                if timeslot:
                    timeslot.start_time = start_time
                    timeslot.end_time = end_time
                else:
                    new_timeslot = TimeSlot(start_time=start_time, end_time=end_time, id=timeslot_id)
                    db.session.add(new_timeslot)

            db.session.commit()
            flash("Time slots updated successfully!", "success")
            return redirect(url_for("main.qr_code_mentor"))

    return render_template("setup.html", form=form)


@main.route('/delete-timeslot', methods=['POST'])
def delete_timeslot():
    data = request.get_json()
    timeslot_id = data.get('id')

    if timeslot_id:
        timeslot = TimeSlot.query.get(timeslot_id)
        if timeslot:
            db.session.delete(timeslot)
            db.session.commit()
            return jsonify(success=True)

    return jsonify(success=False)

@main.route("/delete-mentor", methods=["POST"])
def delete_mentor():
    try:
        data = request.get_json()
        mentor_id = data.get("id")  # Expecting 'id' instead of 'mentor_id'
        mentor = Mentor.query.get(mentor_id)

        if not mentor:
            return jsonify({"success": False, "message": "Mentor not found"}), 404

        # Delete associated ratings for this mentor
        Rating.query.filter_by(mentor_id=mentor_id).delete()

        # Remove the mentor from any timeslots they're associated with
        mentor.timeslots.clear()

        # Now delete the mentor
        db.session.delete(mentor)
        db.session.commit()
        return jsonify({"success": True, "message": "Mentor deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@main.route("/delete-mentee", methods=["POST"])
def delete_mentee():
    try:
        data = request.get_json()
        mentee_id = data.get("id")  # Expecting 'id' instead of 'mentee_id'
        mentee = Mentee.query.get(mentee_id)

        if not mentee:
            return jsonify({"success": False, "message": "Mentee not found"}), 404

        # Delete associated ratings for this mentee
        Rating.query.filter_by(mentee_id=mentee_id).delete()

        # Now delete the mentee
        db.session.delete(mentee)
        db.session.commit()
        return jsonify({"success": True, "message": "Mentee deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@main.route("/update-mentee-rankings", methods=["POST"])
def update_mentee_rankings():
    data = request.get_json()
    mentee_id = data["mentee_id"]
    rankings = data["rankings"]

    try:
        for ranking in rankings:
            mentor_id = ranking["mentor_id"]
            new_rating = ranking["rating"]

            # Find the existing rating or create a new one if it doesn't exist
            rating = Rating.query.filter_by(
                mentee_id=mentee_id, mentor_id=mentor_id
            ).first()
            if rating:
                rating.rating = new_rating  # Update the existing rating
            else:
                # Create a new rating record if it doesn't exist
                rating = Rating(
                    mentee_id=mentee_id, mentor_id=mentor_id, rating=new_rating
                )
                db.session.add(rating)

        db.session.commit()  # Commit changes
        return jsonify({"success": True, "message": "Rankings updated successfully!"})

    except Exception as e:
        db.session.rollback()  # Roll back in case of error
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Failed to update rankings: {}".format(str(e)),
                }
            ),
            500,
        )


@main.route("/update-availability", methods=["POST"])
def update_availability():
    try:
        data = request.get_json()
        mentor_id = int(data["mentor_id"])
        timeslot = data["timeslot"]
        is_available = data["is_available"]

        # Debugging Output
        logging.info(f"Received Data: mentor_id={mentor_id}, timeslot={timeslot}, is_available={is_available}")

        # Assuming the format 'HH:MM-HH:MM', parse start_time and end_time
        try:
            start_time_str, end_time_str = timeslot.split("-")
            start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
        except ValueError as e:
            logging.error(f"Error parsing timeslot string: {e}")
            return jsonify({"success": False, "message": "Invalid timeslot format"}), 400

        # Query Mentor and Timeslot
        mentor = Mentor.query.get(mentor_id)
        timeslot_entry = TimeSlot.query.filter_by(start_time=start_time, end_time=end_time).first()

        if not mentor or not timeslot_entry:
            logging.warning("Mentor or timeslot not found.")
            return jsonify({"success": False, "message": "Mentor or timeslot not found"}), 404

        # Update availability
        if is_available:
            if timeslot_entry not in mentor.timeslots:
                mentor.timeslots.append(timeslot_entry)
                logging.info(f"Added timeslot {timeslot} to mentor {mentor_id}.")
        else:
            if timeslot_entry in mentor.timeslots:
                mentor.timeslots.remove(timeslot_entry)
                logging.info(f"Removed timeslot {timeslot} from mentor {mentor_id}.")

        db.session.commit()
        return jsonify({"success": True, "message": "Availability updated successfully"})

    except Exception as e:
        db.session.rollback()
        logging.error(f"Exception during update availability: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@main.route("/update-mentor", methods=["POST"])
def update_mentor():
    data = request.json
    logging.info(f"Received data: {data}")
    print(f"Received data: {data}")
    mentor_id = data.get("id")

    print(f"Updating mentor with ID: {mentor_id} and job description: {data.get('job_description')}")
    mentor = Mentor.query.get(mentor_id)
    if mentor:
        mentor.name = data.get("name", mentor.name)
        mentor.job_description = data.get("jobDescription", mentor.job_description)
        db.session.commit()
        return jsonify({"success": True, "message": "Mentor updated successfully"}), 200
    return jsonify({"success": False, "message": "Mentor not found"}), 404


@main.route("/update-mentee", methods=["POST"])
def update_mentee():
    mentee_id = request.json["id"]
    new_rating = request.json["rating"]
    mentor_id = request.json["mentor_id"]
    rating = Rating.query.filter_by(mentee_id=mentee_id, mentor_id=mentor_id).first()
    if rating:
        rating.rating = new_rating
        db.session.commit()
        return jsonify({"message": "Rating updated successfully"}), 200
    return jsonify({"message": "Rating not found"}), 404


@main.route("/admin", methods=["GET", "POST"])
def admin():
    form = MentorForm()
    if form.validate_on_submit():
        mentor = Mentor(name=form.name.data, job_description=form.job_description.data)
        db.session.add(mentor)
        db.session.commit()  # Commit mentor to obtain an ID for them

        # Process each timeslot and create a new Timeslot object
        timeslots = [timeslot.strip() for timeslot in form.timeslots.data.split(",")]
        for timeslot_str in timeslots:
            start_time, end_time = timeslot_str.split("-")
            timeslot = TimeSlot(start_time=start_time, end_time=end_time)
            timeslot.mentors.append(mentor)
            db.session.add(timeslot)

        db.session.commit()
        flash("Mentor and timeslots registered successfully!", "success")
        return redirect(url_for("main.admin"))

    # Query all mentors and their timeslots
    mentors_with_timeslots = Mentor.query.all()

    # Prepare data for the template
    mentors_data = []
    for mentor in mentors_with_timeslots:
        timeslots = [f"{ts.start_time.strftime('%H:%M')}-{ts.end_time.strftime('%H:%M')}" for ts in mentor.timeslots]
        mentors_data.append({"mentor": mentor, "timeslots": timeslots})

    mentees_with_rankings = Mentee.query.all()

    # Prepare data for the template
    mentees_data = []
    for mentee in mentees_with_rankings:
        rankings = {rating.mentor_id: rating.rating for rating in mentee.ratings}
        mentees_data.append({"mentee": mentee, "rankings": rankings})

    all_timeslots = [f"{ts.start_time.strftime('%H:%M')}-{ts.end_time.strftime('%H:%M')}" for ts in TimeSlot.query.all()]

    return render_template(
        "admin.html",
        form=form,
        mentors_data=mentors_data,
        mentees_data=mentees_data,
        all_timeslots=all_timeslots,
    )


@main.route("/qr_code_mentor")
def qr_code_mentor():
    mentor_form_url = url_for("main.mentor_form", _external=True)

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
    img_mentor.save(img_io_mentor, "JPEG")
    img_io_mentor.seek(0)
    qr_mentor_data = base64.b64encode(img_io_mentor.getvalue()).decode()

    # Pass the QR data to the template
    return render_template(
        "qr_codes.html", form_name="Mentor Form", qr_code=qr_mentor_data
    )


@main.route("/qr_code_mentee")
def qr_code_mentee():
    # Replace the URL below with the actual route to your mentee form
    mentee_form_url = url_for("main.mentee_form", _external=True)

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
    img_mentee.save(img_io_mentee, "JPEG")
    img_io_mentee.seek(0)
    qr_mentee_data = base64.b64encode(img_io_mentee.getvalue()).decode()

    # Pass the QR data to the template
    return render_template(
        "qr_codes.html", form_name="Mentee Form", qr_code=qr_mentee_data
    )


@main.route("/confirmation_page")
def confirmation_page():
    return render_template("confirmation_page.html")


@main.route("/mentor_form", methods=["GET", "POST"])
def mentor_form():
    form = MentorForm()
    print(f"Mentor Form is valid: {form.validate_on_submit()}")
    if form.validate_on_submit():
        mentor = Mentor(name=form.name.data, job_description=form.job_description.data)
        # This assumes timeslot IDs are passed from checkboxes in the form
        selected_timeslots = form.timeslots.data  # List of timeslot IDs
        print(f"Selected timeslots: {selected_timeslots}")
        for timeslot_id in selected_timeslots:
            timeslot = TimeSlot.query.get(timeslot_id)
            if timeslot:
                # Add entry to the matching table
                mentor.timeslots.append(timeslot)

        db.session.add(mentor)
        db.session.commit()
        flash("Mentor and timeslots registered successfully!", "success")
        return redirect(
            url_for("main.confirmation_page")
        )  # Make sure to redirect to a confirmation or another appropriate page

    return render_template("mentor_form.html", form=form)


@main.route("/mentee_form", methods=["GET", "POST"])
def mentee_form():
    form = MenteeForm()
    mentors = Mentor.query.all()

    if request.method == "GET":
        for mentor in mentors:
            form.mentor_ratings.append_entry(MentorRatingForm())

        for subform in form.mentor_ratings.entries:
            subform.rating.data = 6  # Setting each rating default to 6

    if form.validate_on_submit():
        mentee = Mentee(name=form.name.data)
        db.session.add(mentee)
        db.session.commit()  # Commit to get the mentee ID

        for mentor_form, mentor in zip(form.mentor_ratings.entries, mentors):
            rating_value = mentor_form.form.rating.data
            if rating_value:  # Assuming '0' means no rating given
                rating = Rating(
                    mentee_id=mentee.id, mentor_id=mentor.id, rating=rating_value
                )
                db.session.add(rating)

        db.session.commit()
        flash("Preferences submitted successfully!", "success")
        return redirect(url_for("main.confirmation_page"))
    else:
        print(form.errors)
        if request.method == "POST":
            # Form was submitted but didn't validate
            print("test")
            flash(
                "There was a problem with your submission. Please check your input.",
                "error",
            )

    # Include job descriptions in the list
    mentors_and_forms = [(mentor.name, mentor.job_description, mentor_form)
                         for mentor, mentor_form in zip(mentors, form.mentor_ratings)]

    return render_template(
        "mentee_form.html", form=form, mentors_and_forms=mentors_and_forms
    )

@main.route('/reset-database', methods=['POST'])
def reset_database():
    try:
        db.drop_all()
        db.create_all()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error resetting database: {e}")
        db.session.rollback()
        return jsonify({'success': False}), 500

@main.route("/matching_old")
def matching_old():
    mentors_timeslots = (
        db.session.query(Mentor.id, TimeSlot.id, TimeSlot.start_time, TimeSlot.end_time)
        .join(Mentor.timeslots)
        .all()
    )
    mentee_ratings = (
        db.session.query(Mentee.id, Rating.mentor_id, Rating.rating)
        .join(Mentee.ratings)
        .all()
    )
    # Prepare data for the optimizer
    data = prepare_data_for_optimizer(
        mentors_timeslots, mentee_ratings
    )  # You need to define this based on your needs

    optimizer = Optimizer(data)
    optimizer.solve()

    # Fetch results from the optimizer
    results = (
        optimizer.get_results()
    )  # You would need to add a method to extract formatted results

    return render_template("matching_old.html", results=results)


@main.route("/matching")
def matching():
    mentors_timeslots = (
        db.session.query(Mentor.id, TimeSlot.id, TimeSlot.start_time, TimeSlot.end_time)
        .join(Mentor.timeslots)
        .all()
    )
    mentee_ratings = (
        db.session.query(Mentee.id, Rating.mentor_id, Rating.rating)
        .join(Mentee.ratings)
        .all()
    )
    # Prepare data for the optimizer
    data = prepare_data_for_optimizer(
        mentors_timeslots, mentee_ratings
    )  # You need to define this based on your needs

    optimizer = Optimizer(data)
    optimizer.solve()
    results_by_mentor = optimizer.get_results_by_mentor()

    print(results_by_mentor)

    # Extract the unique list of timeslots from the results
    timeslots = list(next(iter(results_by_mentor.values())).keys())

    # Pass both the results and timeslots to the template
    return render_template("matching.html", results=results_by_mentor, timeslots=timeslots)


if __name__ == "__main__":
    main.run(host="0.0.0.0", port=5000)
