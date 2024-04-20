from app import db  # Ensure you import your db context appropriately
from models import Mentor, Mentee, TimeSlot, Rating  # Import models

# Function to get mentor availability
def get_mentor_availability():
    mentors_timeslots = db.session.query(Mentor.id, TimeSlot.id, TimeSlot.start_time, TimeSlot.end_time).join(
        Mentor.timeslots).all()
    availability = {}
    for mentor_id, timeslot_id, start_time, end_time in mentors_timeslots:
        timeslot = f"{start_time}-{end_time}"
        availability[(str(mentor_id), timeslot)] = True
    return availability

# Function to get mentee preferences
def get_mentee_preferences():
    mentee_ratings = db.session.query(Mentee.id, Rating.mentor_id, Rating.rating).join(
        Mentee.ratings).all()
    preferences = {}
    for mentee_id, mentor_id, rating in mentee_ratings:
        preferences[(str(mentee_id), str(mentor_id))] = rating
    return preferences

# Main function to prepare data
def prepare_data_for_optimizer():

    print("Data preparation started")
    mentor_availability = get_mentor_availability()
    mentee_preferences = get_mentee_preferences()

    # Assuming your optimizer needs a list of mentors, mentees, and timeslots
    mentors = list({key[0] for key in mentor_availability.keys()})
    mentees = list({key[0] for key in mentee_preferences.keys()})
    timeslots = list({key[1] for key in mentor_availability.keys()})
    timeslots.sort()  # Sort timeslots if necessary

    return {
        "mentors": mentors,
        "mentees": mentees,
        "timeslots": timeslots,
        "availability": mentor_availability,
        "preferences": mentee_preferences
    }
