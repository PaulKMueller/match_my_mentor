# import pulp

# class Optimizer:
#     def __init__(self):

from .data_adapter import prepare_data_for_optimizer
from .models import Mentee, Mentor, TimeSlot


import pulp


class Optimizer:
    def __init__(self, data: dict):
        self.high_preference_penalty = (
            1000  # This should be higher than any undesirable score
        )
        self.mentees = data["mentees"]
        self.mentors = data["mentors"]
        self.timeslots = data["timeslots"]
        self.availability = data["availability"]
        self.preferences = data["preferences"]

        for i in range(len(self.mentees)):
            self.mentors.append("NoMentor")

        for mentee in self.mentees:
            self.preferences[(mentee, "NoMentor")] = self.high_preference_penalty

        for timeslot in self.timeslots:
            self.availability[("NoMentor", timeslot)] = True

    def solve(self):
        # Set up the problem
        problem = pulp.LpProblem("Mentor_Mentee_Scheduling", pulp.LpMinimize)

        # Decision variables: (mentee, mentor, timeslot)
        self.x = pulp.LpVariable.dicts(
            "pairing", (self.mentees, self.mentors, self.timeslots), cat=pulp.LpBinary
        )

        # Objective function: Minimize the total preference score
        problem += pulp.lpSum(
            [
                self.preferences[(mentee, mentor)] * self.x[mentee][mentor][timeslot]
                for mentee in self.mentees
                for mentor in self.mentors
                for timeslot in self.timeslots
                if (mentor, timeslot) in self.availability
                and self.availability[mentor, timeslot]
            ]
        )

        # Constraints

        # Constraint: Each mentee is scheduled at most once per timeslot
        for mentee in self.mentees:
            for timeslot in self.timeslots:
                problem += (
                    pulp.lpSum(
                        [
                            self.x[mentee][mentor][timeslot]
                            for mentor in self.mentors
                            if (mentor, timeslot) in self.availability
                            and self.availability[mentor, timeslot]
                        ]
                    )
                    == 1
                ) * 10000

        # Constraint: Each mentor-mentee pair should meet only once
        for mentee in self.mentees:
            for mentor in self.mentors:
                problem += (
                    pulp.lpSum(
                        [
                            self.x[mentee][mentor][timeslot]
                            for timeslot in self.timeslots
                        ]
                    )
                    <= 1
                )

        # Constraint: Each mentor can appear only once in each timeslot
        for mentor in self.mentors:
            for timeslot in self.timeslots:
                problem += (
                    pulp.lpSum(
                        [self.x[mentee][mentor][timeslot] for mentee in self.mentees]
                    )
                    <= 1
                ) * 10000

        # Constraint: Each mentee should be assigned to a mentor if available
        for mentee in self.mentees:
            for mentor in self.mentors:
                for timeslot in self.timeslots:
                    if (mentor, timeslot) in self.availability:
                        if not self.availability[mentor, timeslot]:
                            problem += self.x[mentee][mentor][timeslot] == 0

        # Solve the problem
        status = problem.solve()

    def get_results(self):
        # Fetch all mentors and mentees first to avoid repeated database queries
        mentor_names = {mentor.id: mentor.name for mentor in Mentor.query.all()}
        mentee_names = {mentee.id: mentee.name for mentee in Mentee.query.all()}
        time_slot_names = {
            time_slot.id: f"{time_slot.start_time.strftime('%H:%M')}-{time_slot.end_time.strftime('%H:%M')}"
            for time_slot in TimeSlot.query.all()
        }

        results_by_timeslot = {}
        for timeslot in self.timeslots:
            results_by_timeslot[time_slot_names[timeslot]] = []
            for mentee in self.mentees:
                for mentor in self.mentors:
                    if pulp.value(self.x[mentee][mentor][timeslot]) == 1:
                        if mentor == "NoMentor":
                            mentor_name = "Break"
                        else:
                            mentor_name = mentor_names.get(
                                int(mentor), "None"
                            )  # Use 'None' or similar if no mentor
                        results_by_timeslot[time_slot_names[timeslot]].append(
                            {"mentee": mentee_names[int(mentee)], "mentor": mentor_name}
                        )

        if self.check_results():
            print("Results are valid")
            return results_by_timeslot
        else:
            print("Invalid results found")
            return results_by_timeslot
        
    def get_results_by_mentor(self):
        mentor_names = {mentor.id: mentor.name for mentor in Mentor.query.all()}
        mentee_names = {mentee.id: mentee.name for mentee in Mentee.query.all()}
        print(f"Mentee names: {mentee_names}")
        time_slot_names = {
            time_slot.id: f"{time_slot.start_time.strftime('%H:%M')}-{time_slot.end_time.strftime('%H:%M')}"
            for time_slot in TimeSlot.query.all()
        }

        results_by_mentor = {}
        for mentor in self.mentors:
            if mentor == "NoMentor":
                mentor_name = "Break"
            else:
                mentor_name = mentor_names.get(
                    int(mentor), "None"
                )  # Use 'None' if no mentor name is found

            results_by_mentor[mentor_name] = (
                {}
            )  # Initialize each mentor with an empty dictionary for timeslots

            for timeslot in self.timeslots:
                timeslot_name = time_slot_names[timeslot]
                results_by_mentor[mentor_name][
                    timeslot_name
                ] = []  # Initialize each timeslot with an empty list for mentees

                for mentee in self.mentees:
                    if pulp.value(self.x[mentee][mentor][timeslot]) == 1:
                        results_by_mentor[mentor_name][timeslot_name].append(
                            mentee_names[int(mentee)]
                        )

        # Check results
        if self.check_results():
            print("Results are valid")
        else:
            print("Invalid results found")

        # Remove Break mentor from the results
        results_by_mentor.pop("Break", None)

        # Extract the mentees and timeslots from the results
        timeslots = list(next(iter(results_by_mentor.values())).keys())  # Assumes timeslots are consistent across mentors
        all_mentees = {mentee for schedule in results_by_mentor.values() for mentees in schedule.values() for mentee in mentees}

        # Track assignments by both mentee and mentor
        mentee_assignments = {timeslot: set() for timeslot in timeslots}
        mentor_assignments = {mentor: set() for mentor in results_by_mentor}

        # Populate assignments for initial state
        for mentor, schedule in results_by_mentor.items():
            for timeslot, mentees in schedule.items():
                mentor_assignments[mentor].update(mentees)
                mentee_assignments[timeslot].update(mentees)

        # Fill empty slots
        for mentor, schedule in results_by_mentor.items():
            for timeslot, mentees in schedule.items():
                if not mentees:  # If this slot is empty
                    available_mentees = [
                        mentee for mentee in all_mentees
                        if mentee not in mentee_assignments[timeslot]  # Mentee is not in this timeslot
                        and mentee not in mentor_assignments[mentor]   # Mentee hasn't met with this mentor yet
                    ]
                    
                    # Assign an available mentee if any are left
                    if available_mentees:
                        chosen_mentee = available_mentees[0]  # Choose the first available mentee
                        results_by_mentor[mentor][timeslot].append(chosen_mentee)
                        mentee_assignments[timeslot].add(chosen_mentee)
                        mentor_assignments[mentor].add(chosen_mentee)

        return results_by_mentor


    def check_results(self):
        # Check if mentor or mentee is assigned multiple times per timeslot
        for timeslot in self.timeslots:
            for mentor in self.mentors:
                if (
                    sum(
                        [
                            pulp.value(self.x[mentee][mentor][timeslot])
                            for mentee in self.mentees
                        ]
                    )
                    > 1
                ):
                    return False
            for mentee in self.mentees:
                if (
                    sum(
                        [
                            pulp.value(self.x[mentee][mentor][timeslot])
                            for mentor in self.mentors
                        ]
                    )
                    > 1
                ):
                    return False
        else:
            return True
