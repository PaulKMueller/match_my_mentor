# import pulp

# class Optimizer:
#     def __init__(self):

from data_adapter import prepare_data_for_optimizer


import pulp

# {
#         "mentors": mentors,
#         "mentees": mentees,
#         "timeslots": timeslots,
#         "availability": mentor_availability,
#         "preferences": mentee_preferences
#     }

# # Example data structures
# mentors = ['M1', 'M2', 'M3', 'NoMentor']  # 'NoMentor' is a dummy mentor for no assignment
# mentees = ['m1', 'm2', 'm3']
# timeslots = ['T1', 'T2', 'T3']

# # Mentor availability including dummy mentor available all the time
# availability = {
#     ('M1', 'T1'): True,
#     ('M1', 'T2'): False,
#     ('M1', 'T3'): True,
#     ('M2', 'T1'): True,
#     ('M2', 'T2'): True,
#     ('M2', 'T3'): False,
#     ('M3', 'T1'): False,
#     ('M3', 'T2'): True,
#     ('M3', 'T3'): True,
#     ('NoMentor', 'T1'): True,
#     ('NoMentor', 'T2'): True,
#     ('NoMentor', 'T3'): True,  # Dummy mentor is always available
# }

# # Preferences including very high preference for not being assigned
# high_preference_penalty = 100  # This should be higher than any undesirable score
# preferences = {
#     ('m1', 'M1'): 2,
#     ('m1', 'M2'): 1,
#     ('m1', 'M3'): 3,
#     ('m2', 'M1'): 1,
#     ('m2', 'M2'): 3,
#     ('m2', 'M3'): 2,
#     ('m3', 'M1'): 3,
#     ('m3', 'M2'): 1,
#     ('m3', 'M3'): 2,
#     ('m1', 'NoMentor'): high_preference_penalty,
#     ('m2', 'NoMentor'): high_preference_penalty,
#     ('m3', 'NoMentor'): high_preference_penalty,
# }

class Optimizer:

    def __init__(self, data):
        self.high_preference_penalty = 100  # This should be higher than any undesirable score
        self.mentees = data["mentees"]
        self.mentors = data["mentors"]
        self.timeslots = data["timeslots"]
        self.availability = data["availability"]
        self.preferences = data["preferences"]

        self.mentors.append("NoMentor")

        for mentee in self.mentees:
            self.preferences[(mentee, 'NoMentor')] = self.high_preference_penalty

        for timeslot in self.timeslots:
            self.availability[('NoMentor', timeslot)] = True

        print("Here are the mentors:")
        print(self.mentors)

    def solve(self):
        # Set up the problem
        problem = pulp.LpProblem("Mentor_Mentee_Scheduling", pulp.LpMinimize)

        # Decision variables: (mentee, mentor, timeslot)
        self.x = pulp.LpVariable.dicts("pairing", (self.mentees, self.mentors, self.timeslots), cat=pulp.LpBinary)

        # Objective function: Minimize the total preference score
        problem += pulp.lpSum([self.preferences[(mentee, mentor)] * self.x[mentee][mentor][timeslot]
                            for mentee in self.mentees for mentor in self.mentors for timeslot in self.timeslots
                            if (mentor, timeslot) in self.availability and self.availability[mentor, timeslot]])

        # Constraints

        # Constraint: Each mentee is scheduled at most once per timeslot
        for mentee in self.mentees:
            for timeslot in self.timeslots:
                problem += pulp.lpSum([self.x[mentee][mentor][timeslot] for mentor in self.mentors
                                    if (mentor, timeslot) in self.availability and self.availability[mentor, timeslot]]) == 1

        # Constraint: Each mentor-mentee pair should meet only once
        for mentee in self.mentees:
            for mentor in self.mentors:
                problem += pulp.lpSum([self.x[mentee][mentor][timeslot] for timeslot in self.timeslots]) <= 1

        # Constraint: Each mentor can appear only once in each timeslot
        for mentor in self.mentors:
            for timeslot in self.timeslots:
                problem += (pulp.lpSum([self.x[mentee][mentor][timeslot] for mentee in self.mentees]) <= 1) * -1000

        # Solve the problem
        status = problem.solve()

        # Output formatting
        print("Schedule by Timeslot:")
        for timeslot in self.timeslots:
            print(f"\nTimeslot {timeslot}:")
            for mentee in self.mentees:
                for mentor in self.mentors:
                    if pulp.value(self.x[mentee][mentor][timeslot]) == 1:
                        if mentor != 'NoMentor':
                            print(f"  Mentee {mentee} is assigned to Mentor {mentor}")
                        else:
                            print(f"  Mentee {mentee} is not assigned to any mentor in this timeslot")

        if status == pulp.LpStatusOptimal:
            print("An optimal solution has been found.")
        elif status == pulp.LpStatusInfeasible:
            print("No feasible solution exists.")
        elif status == pulp.LpStatusUnbounded:
            print("The problem is unbounded.")
        else:
            print("Some other status: ", pulp.LpStatus[status])
    
    def get_results(self):
        result_list = []
        for timeslot in self.timeslots:
            for mentee in self.mentees:
                for mentor in self.mentors:
                    if pulp.value(self.x[mentee][mentor][timeslot]) == 1:
                        result_list.append({
                            'timeslot': timeslot,
                            'mentee': mentee,
                            'mentor': mentor if mentor != 'NoMentor' else 'None'
                        })
        return result_list
