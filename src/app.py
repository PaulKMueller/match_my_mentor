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


@main.route("/timeslots", methods=["GET", "POST"])
def manage_timeslots():
    form = TimeSlotsForm()

    # Pre-fill the form with existing timeslots from the database
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

    # Handle form submission
    if form.validate_on_submit():
        for entry in form.timeslots:
            timeslot_id = entry.timeslot_id.data
            start_time = entry.start_time.data
            end_time = entry.end_time.data

            # Update existing time slot or create a new one
            if timeslot_id:
                timeslot = TimeSlot.query.get(timeslot_id)
                if timeslot:
                    timeslot.start_time = start_time
                    timeslot.end_time = end_time
            else:
                new_timeslot = TimeSlot(start_time=start_time, end_time=end_time)
                db.session.add(new_timeslot)

        db.session.commit()
        flash("Time slots updated successfully!", "success")
        return redirect(url_for("manage_timeslots"))

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

        mentor = Mentor.query.get(mentor_id)
        timeslot_entry = TimeSlot.query.filter_by(
            start_time=timeslot.split("-")[0], end_time=timeslot.split("-")[1]
        ).first()

        if not mentor or not timeslot_entry:
            return (
                jsonify({"success": False, "message": "Mentor or timeslot not found"}),
                404,
            )

        if is_available:
            if timeslot_entry not in mentor.timeslots:
                mentor.timeslots.append(timeslot_entry)
        else:
            if timeslot_entry in mentor.timeslots:
                mentor.timeslots.remove(timeslot_entry)

        db.session.commit()
        return jsonify(
            {"success": True, "message": "Availability updated successfully"}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@main.route("/update-mentor", methods=["POST"])
def update_mentor():
    data = request.json
    mentor_id = data["id"]
    mentor = Mentor.query.get(mentor_id)
    if mentor:
        mentor.name = data.get("name", mentor.name)
        mentor.job_description = data.get("job_description", mentor.job_description)
        # You would also handle the timeslots here, possibly requiring additional logic

        db.session.commit()
        return jsonify({"message": "Mentor updated successfully"}), 200
    return jsonify({"message": "Mentor not found"}), 404


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
        timeslots = ", ".join(
            [f"{ts.start_time}-{ts.end_time}" for ts in mentor.timeslots]
        )
        mentors_data.append({"mentor": mentor, "timeslots": timeslots})

    mentees_with_rankings = Mentee.query.all()

    # Prepare data for the template
    mentees_data = []
    for mentee in mentees_with_rankings:
        rankings = {rating.mentor_id: rating.rating for rating in mentee.ratings}
        mentees_data.append({"mentee": mentee, "rankings": rankings})

    return render_template(
        "admin.html",
        form=form,
        mentors_data=mentors_data,
        mentees_data=mentees_data,
        all_timeslots=[f"{ts.start_time}-{ts.end_time}" for ts in TimeSlot.query.all()],
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
        print("Form is not valid")
        print(form.errors)
        if request.method == "POST":
            # Form was submitted but didn't validate
            print("test")
            flash(
                "There was a problem with your submission. Please check your input.",
                "error",
            )

    mentor_names = [mentor.name for mentor in mentors]
    mentors_and_forms = zip(mentor_names, form.mentor_ratings)
    return render_template(
        "mentee_form.html", form=form, mentors_and_forms=mentors_and_forms
    )

@main.route('/reset-database', methods=['POST'])
def reset_database():
    try:
        # Delete all data from the tables
        Mentor.query.delete()
        Mentee.query.delete()
        TimeSlot.query.delete()
        Rating.query.delete()
        
        # Commit the changes to the database
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error resetting database: {e}")
        db.session.rollback()
        return jsonify({'success': False}), 500

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
    print(data)
    optimizer = Optimizer(data)
    optimizer.solve()

    # Fetch results from the optimizer
    results = (
        optimizer.get_results()
    )  # You would need to add a method to extract formatted results

    return render_template("matching.html", results=results)


if __name__ == "__main__":
    main.run(host="0.0.0.0", port=5000)
