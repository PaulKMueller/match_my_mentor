# Function to get mentor availability
def get_mentor_availability(mentors_timeslots_data):
    availability = {}
    for mentor_id, timeslot_id, start_time, end_time in mentors_timeslots_data:
        availability[(mentor_id, timeslot_id)] = True
    return availability

# Function to get mentee preferences
def get_mentee_preferences(mentee_ratings_data):
    preferences = {}
    for mentee_id, mentor_id, rating in mentee_ratings_data:
        preferences[(mentee_id, mentor_id)] = rating
    return preferences

# Example call to prepare data for the optimizer
def prepare_data_for_optimizer(mentors_timeslots_data, mentee_ratings_data):
    mentor_availability = get_mentor_availability(mentors_timeslots_data)
    mentee_preferences = get_mentee_preferences(mentee_ratings_data)

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
