import pulp as pl
import numpy as np
from Institution import Institution


class SelectCandidatesForTest:
    """
    Linear Programming problem. Receives the institution (which contains its organizational structure) and allowed
    number of tests. The goal o the problem is to sample the optimal candidates out of the people, such that
    the coverage of the overall risk in the groups is maximized.
    """
    def __init__(self, B: int, institution: Institution,
                 integer_programming=False,
                 normalized_coverage=True,
                 secondary_objective_coefficient=0.01):
        """

        :param B: maximum number of allowed tests (budget)
        :param institution: an object encompassing the structure of the organization
        :param integer_programming: True --> the linear program becomes an integer program.
                                    False --> the linear program is solved fractionally, then randomly rounded.
        :param normalized_coverage: Sets the type of coverage used in the constraints.
                                    False --> coverage(group) = sum of weights of tested people in the group
                                    True  --> coverage(group) = sum of weights of tested people in the group / weight of the group
        :param secondary_objective_coefficient: float - a coefficient to multiply the secondary objective of the optimization.
        """

        if len(institution.person_lst) < B:
            self.B = len(institution.person_lst)  # number of allotted tests
            print("Warning: The budget of B={} cannot be exploited since there are only "
                  "{} people in the organization. The budget was therefore "
                  "truncated to {}".format(B,self.B,self.B))
        else:
            self.B = B

        self.institution = institution
        self.integer_programming = integer_programming
        self.problem = pl.LpProblem("Institution_People_Sampling_for_CoVID-19_Testing", sense=pl.LpMaximize)
        self.x = pl.LpVariable.dicts("x", list(institution.person_idx_to_name_dict.keys()), lowBound=0.0, upBound=1.0, cat=pl.LpBinary if integer_programming else pl.LpContinuous)#, cat=pl.LpBinary) #TODO UNCOMMMENT ME if you wish to revert to Integer programming
        self.z = pl.LpVariable("z", cat=pl.LpContinuous)

        # Compute group coverages c(e) = <x,w>/W
        group_coverage = {}
        average_person_weight = sum(institution.nodes_attributes[person]['w'] for person in institution.person_lst)
        for group_idx, group in enumerate(institution.group_lst):

            group_people_name_lst = list(institution.G.neighbors(group))
            group_people_var_lst = [self.x[institution.person_name_to_idx_dict[person]] for person in group_people_name_lst]
            if normalized_coverage:
                group_people_weight_lst = [institution.G.nodes[person]['w'] / institution.G.nodes[group]['w'] if institution.G.nodes[group]['w'] != 0 else 0.0 for person in group_people_name_lst]
            else:
                group_people_weight_lst = [institution.G.nodes[person]['w'] for person in group_people_name_lst]
            group_coverage[group] = pl.lpDot(group_people_var_lst, group_people_weight_lst)

            # FOR EVERY GROUP set a constraint c(e) <= z
            if institution.G.nodes[group]['w'] >= (0.5 / len(institution.person_lst))*average_person_weight: # must avoid constraining on the non-risky groups TODO: change the 0.0 to a 1/(2|V|) * sum_all_weights
                self.problem += group_coverage[group] >= self.z, "group_{}_coverage".format(group_idx)


        # Sum of the sampled person must not exceed the number of allotted tests (B)
        self.problem += pl.lpSum(self.x[pid] for pid in list(institution.person_idx_to_name_dict.keys())) <= self.B, "Constraint_on_the_maximum_number_of_tests"

        # Primary objective - fairness; Secondary objective - sum of coverages
        regularizer = secondary_objective_coefficient / ( len(institution.group_lst)) if len(institution.group_lst) != 0 else 0.1
        self.problem += self.z + regularizer * pl.lpSum(group_coverage.values())

    def __str__(self):
        return "People Selection Linear Program with the " \
               "following parameters:\n B={}:\n{}".format(self.B,self.problem)

    def solve(self, path= "", verbosity=0):
        """
        Solves the LP problem and returns the list of people chosen for sampling.
        :param verbosity: 0 - no messages, 1 - only python messages, 2 - python and solver messages
        :return: list of person chosen for sampling, or None if failed
        """
        try:
            self.problem.solve(pl.GLPK_CMD(msg=verbosity, path= None if path == "" else path)) # TODO allow other solvers
            solver_crashed = False
        except:
            solver_crashed = True
			
        if not solver_crashed and self.problem.status == 1:
            sampled_person_lst = []
            person_idx_to_x_value_dict = {person_id:pl.value(x) for person_id, x in sorted(self.x.items())}
            for person_idx, x_value in sorted(person_idx_to_x_value_dict.items()):
                person = self.institution.person_idx_to_name_dict[person_idx]
                if self.integer_programming:
                    sampled = x_value
                    if verbosity > 0:
                        print("person {} : {}".format(person, pl.value(x_value)))
                else: # Requires randomized rounding
                    sampled = np.random.binomial(1, pl.value(x_value))
                    if verbosity > 0:
                        print("person {:25} : {} randomly rounded to {} ".format(person, x_value, sampled))
                if sampled:
                    sampled_person_lst.append(person)

            # if the number of sampled people is different than B - add/remove people as required to reach exactly B:
            sampled_person_lst = self.refine_sampled_person_lst(sampled_person_lst, person_idx_to_x_value_dict,
                                                                verbosity=verbosity)

            # Report the sampled people
            num_selected_people = len(sampled_person_lst)
            if verbosity > 0:
                print("Found a solution (z={}): People chosen for sampling".format(pl.value(self.z)))
                print(sampled_person_lst)
                print("-" * 72)
                print("The solution selected {} {} (B was set to {})".format(num_selected_people, "person" if num_selected_people == 1 else "people", self.B))
            return sampled_person_lst
        else:
            if verbosity > 0:
                print("Failed solving the linear program of people selection")
            return None

    def status(self):
        return self.problem.status

    def refine_sampled_person_lst(self, sampled_person_lst : list, person_idx_to_x_value_dict : dict, verbosity : int):
        """
        If, as a result of the linear problem solution, the number of sampled people is not exactly B,
        this function will attempt to bring it as close to B as possible.
        :param sampled_person_lst: list (of strings) of people that were chosen for testing by the solver.
        :param person_idx_to_x_value_dict: a dictionary where person indices are the keys and the values are the
                                       optimization variables.
        :param verbosity: integer, any positive value will allow messages to be printed to the stdout.
        :return: a refined list of people chosen for testing.
        """
        num_selected_people = len(sampled_person_lst)
        if not self.integer_programming and num_selected_people != self.B:
            if verbosity > 0: print("Number of chosen people {} doesn't "
                                    "correspond to budget B={}. Starting "
                                    "refinements...".format(num_selected_people, self.B))
            if num_selected_people > self.B:
                sampled_person_lst_ordered_by_score = [self.institution.person_idx_to_name_dict[person_idx] for person_idx, value
                                                       in sorted(person_idx_to_x_value_dict.items(), key=lambda item: item[1])
                                                       if self.institution.person_idx_to_name_dict[person_idx] in sampled_person_lst]
                while len(sampled_person_lst_ordered_by_score) > self.B:  # continue removing people with ascending score
                    person = sampled_person_lst_ordered_by_score.pop(0)
                    if verbosity > 0:
                        print(" - Removing person named {}".format(person))
                sampled_person_lst = sampled_person_lst_ordered_by_score
            elif num_selected_people < self.B:
                unsampled_person_lst_ordered_by_score = [self.institution.person_idx_to_name_dict[person_idx] for person_idx, value
                                                         in sorted(person_idx_to_x_value_dict.items(), key=lambda item: item[1])
                                                         if self.institution.person_idx_to_name_dict[person_idx] not in sampled_person_lst]
                while len(sampled_person_lst) < self.B and len(unsampled_person_lst_ordered_by_score) > 0:
                    person = unsampled_person_lst_ordered_by_score.pop(-1)
                    sampled_person_lst.append(person)
                    if verbosity > 0:
                        print(" - Adding person named {}".format(person))
        return sampled_person_lst




