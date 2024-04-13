# import pulp

# class Optimizer:
#     def __init__(self):


import pulp

# {
#         "mentors": mentors,
#         "mentees": mentees,
#         "timeslots": timeslots,
#         "availability": mentor_availability,
#         "preferences": mentee_preferences
#     }

# Example data structures
mentors = ['M1', 'M2', 'M3', 'NoMentor']  # 'NoMentor' is a dummy mentor for no assignment
mentees = ['m1', 'm2', 'm3']
timeslots = ['T1', 'T2', 'T3']

# Mentor availability including dummy mentor available all the time
availability = {
    ('M1', 'T1'): True,
    ('M1', 'T2'): False,
    ('M1', 'T3'): True,
    ('M2', 'T1'): True,
    ('M2', 'T2'): True,
    ('M2', 'T3'): False,
    ('M3', 'T1'): False,
    ('M3', 'T2'): True,
    ('M3', 'T3'): True,
    ('NoMentor', 'T1'): True,
    ('NoMentor', 'T2'): True,
    ('NoMentor', 'T3'): True,  # Dummy mentor is always available
}

# Preferences including very high preference for not being assigned
high_preference_penalty = 100  # This should be higher than any undesirable score
preferences = {
    ('m1', 'M1'): 2,
    ('m1', 'M2'): 1,
    ('m1', 'M3'): 3,
    ('m2', 'M1'): 1,
    ('m2', 'M2'): 3,
    ('m2', 'M3'): 2,
    ('m3', 'M1'): 3,
    ('m3', 'M2'): 1,
    ('m3', 'M3'): 2,
    ('m1', 'NoMentor'): high_preference_penalty,
    ('m2', 'NoMentor'): high_preference_penalty,
    ('m3', 'NoMentor'): high_preference_penalty,
}

# Set up the problem
problem = pulp.LpProblem("Mentor_Mentee_Scheduling", pulp.LpMinimize)

# Decision variables: (mentee, mentor, timeslot)
x = pulp.LpVariable.dicts("pairing", (mentees, mentors, timeslots), cat=pulp.LpBinary)

# Objective function: Minimize the total preference score
problem += pulp.lpSum([preferences[mentee, mentor] * x[mentee][mentor][timeslot]
                       for mentee in mentees for mentor in mentors for timeslot in timeslots
                       if (mentor, timeslot) in availability and availability[mentor, timeslot]])

# Constraints

# Constraint: Each mentee is scheduled at most once per timeslot
for mentee in mentees:
    for timeslot in timeslots:
        problem += pulp.lpSum([x[mentee][mentor][timeslot] for mentor in mentors
                               if (mentor, timeslot) in availability and availability[mentor, timeslot]]) == 1

# Constraint: Each mentor-mentee pair should meet only once (except for the dummy mentor)
for mentee in mentees:
    for mentor in mentors:
        if mentor != 'NoMentor':
            problem += pulp.lpSum([x[mentee][mentor][timeslot] for timeslot in timeslots]) <= 1

# New constraint: Each mentor can appear only once in each timeslot
for mentor in mentors:
    if mentor != 'NoMentor':  # Exclude the dummy mentor from this constraint
        for timeslot in timeslots:
            problem += pulp.lpSum([x[mentee][mentor][timeslot] for mentee in mentees]) <= 1

# Solve the problem
problem.solve()

# Output formatting
print("Schedule by Timeslot:")
for timeslot in timeslots:
    print(f"\nTimeslot {timeslot}:")
    for mentee in mentees:
        for mentor in mentors:
            if pulp.value(x[mentee][mentor][timeslot]) == 1:
                if mentor != 'NoMentor':
                    print(f"  Mentee {mentee} is assigned to Mentor {mentor}")
                else:
                    print(f"  Mentee {mentee} is not assigned to any mentor in this timeslot")
