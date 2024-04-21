# import pulp

# class Optimizer:
#     def __init__(self):

from .data_adapter import prepare_data_for_optimizer
from .models import Mentee, Mentor


import pulp

class Optimizer:
    def __init__(self, data:dict):
        self.high_preference_penalty = 100  # This should be higher than any undesirable score
        self.mentees = data["mentees"]
        self.mentors = data["mentors"]
        self.timeslots = data["timeslots"]
        self.availability = data["availability"]
        self.preferences = data["preferences"]

        for i in range(len(self.mentees)):
            self.mentors.append("NoMentor")

        for mentee in self.mentees:
            self.preferences[(mentee, 'NoMentor')] = self.high_preference_penalty

        for timeslot in self.timeslots:
            self.availability[('NoMentor', timeslot)] = True


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
                problem += (pulp.lpSum([self.x[mentee][mentor][timeslot] for timeslot in self.timeslots]) <= 1)

        # Constraint: Each mentor can appear only once in each timeslot
        for mentor in self.mentors:
            for timeslot in self.timeslots:
                problem += (pulp.lpSum([self.x[mentee][mentor][timeslot] for mentee in self.mentees]) <= 1)

        # Solve the problem
        status = problem.solve()

        # # Output formatting
        # print("Schedule by Timeslot:")
        # for timeslot in self.timeslots:
        #     print(f"\nTimeslot {timeslot}:")
        #     for mentee in self.mentees:
        #         for mentor in self.mentors:
        #             if pulp.value(self.x[mentee][mentor][timeslot]) == 1:
        #                 if mentor != 'NoMentor':
        #                     print(f"  Mentee {mentee} is assigned to Mentor {mentor}")
        #                 else:
        #                     print(f"  Mentee {mentee} is not assigned to any mentor in this timeslot")

        # if status == pulp.LpStatusOptimal:
        #     print("An optimal solution has been found.")
        # elif status == pulp.LpStatusInfeasible:
        #     print("No feasible solution exists.")
        # elif status == pulp.LpStatusUnbounded:
        #     print("The problem is unbounded.")
        # else:
        #     print("Some other status: ", pulp.LpStatus[status])
    
    def get_results(self):
        # Fetch all mentors and mentees first to avoid repeated database queries
        mentor_names = {mentor.id: mentor.name for mentor in Mentor.query.all()}
        mentee_names = {mentee.id: mentee.name for mentee in Mentee.query.all()}
        
        results_by_timeslot = {}
        for timeslot in self.timeslots:
            results_by_timeslot[timeslot] = []
            for mentee in self.mentees:
                for mentor in self.mentors:
                    if pulp.value(self.x[mentee][mentor][timeslot]) == 1:
                        if mentor == 'NoMentor':
                            mentor_name = "Break"
                        else:
                            mentor_name = mentor_names.get(int(mentor), 'None')  # Use 'None' or similar if no mentor
                        results_by_timeslot[timeslot].append({
                            'mentee': mentee_names[int(mentee)],
                            'mentor': mentor_name
                        })
        if self.check_results():
            print("Results are valid")
            return results_by_timeslot
        else:
            print("Invalid results found")
            return results_by_timeslot
    
    def check_results(self):
        # Check if mentor or mentee is assigned multiple times per timeslot
        for timeslot in self.timeslots:
            for mentor in self.mentors:
                if sum([pulp.value(self.x[mentee][mentor][timeslot]) for mentee in self.mentees]) > 1:
                    return False
            for mentee in self.mentees:
                if sum([pulp.value(self.x[mentee][mentor][timeslot]) for mentor in self.mentors]) > 1:
                    return False

