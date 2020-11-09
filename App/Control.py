from PIL import ImageTk, Image
from typing import Tuple, List, Union
import os
from datetime import date, timedelta
import numpy as np
import pandas as pd
import tqdm

from Institution import Institution
from RiskManager import RiskManager
from LinearProgramming import SelectCandidatesForTest
from MyDate import check_strdate, MyDate
from Util.plot import plot_budget_exploration
from Util.spreadsheet import merge_checklist_to_main, read_main_spreadsheet, produce_checklist, produce_weighted_risk_sheet
from shutil import copyfile


class Control:

    def __init__(self, root: str, spreadsheet_directory: str):
        """
        A path to where all the main and checklist spreadsheets can be found.
        If not exists, this directory will be created during the construction
        of this object.
        :param root:
        :param spreadsheet_directory:
        """

        self.root = root
        self.spreadsheet_directory = os.path.join(
            self.root, spreadsheet_directory)
        self.state = "Init"
        self.message = "Please set the dates for which you wish to perform smart candidate " \
                       "selection. Then click 'Load Spreadsheet'."
        self.main_spreadsheet_path = ""
        self.solver_path = os.path.join(self.root,
                                        "Solvers/glpk-4.65/w64/glpsol.exe")

        # When spreadsheet succeeds to load - (self.state = Initial_main_spreadsheet_loaded)
        # the following values should become non-None:
        self.organization_df = None
        self.risk_df = None
        self.current_date = None
        self.previous_date = None
        self.institution = None
        self.progress = (0, -1)

        # When spreadsheet succeeds to be solved - the following values should become non-None
        self.solutions_dictionary = None
        self.fig_output_dir = None

    def load_spreadsheet(self, current_date: MyDate, previous_date: MyDate):
        print(self.root)
        self.state, self.message, self.main_spreadsheet_path = self.spreadsheet_file_setup(
            current_date, previous_date)
        if "Initial_main_spreadsheet_ready" in self.state:
            self.organization_df, self.risk_df, spreadsheet_loading_msg = read_main_spreadsheet(
                self.main_spreadsheet_path)

            if spreadsheet_loading_msg != "":
                self.message += "\n\n{}".format(spreadsheet_loading_msg)
            else:
                # only now we can move to the solution screen
                self.state = "Initial_main_spreadsheet_loaded"
                self.current_date = current_date
                self.previous_date = previous_date

    def spreadsheet_file_setup(self, current_date: MyDate, previous_date: MyDate) -> Tuple[str, str, str]:
        """
        Review the state of the current main spreadsheet, create it if required (by merging the previous main + checklist)
        or by copying the previous main spreadsheet if the previous checklist is missing.
        This will determine which initial window will be shown
        :return: state, message, main_spreadsheet_path - three strings
        that describe the state of the main spreadsheet of the current date.
        """
        if not os.path.exists(self.spreadsheet_directory):
            os.makedirs(self.spreadsheet_directory)

        current_date_str = current_date.strdate
        previous_date_str = previous_date.strdate
        xlsx_current_main_path = os.path.join(
            self.spreadsheet_directory, current_date_str + "_main.xlsx")
        odt_current_main_path = os.path.join(
            self.spreadsheet_directory, current_date_str + "_main.odt")
        xlsx_previous_main_path = os.path.join(
            self.spreadsheet_directory, previous_date_str + "_main.xlsx")
        odt_previous_main_path = os.path.join(
            self.spreadsheet_directory, previous_date_str + "_main.odt")
        xlsx_previous_checklist_path = os.path.join(
            self.spreadsheet_directory, previous_date_str + "_checklist.xlsx")
        odt_previous_checklist_path = os.path.join(
            self.spreadsheet_directory, previous_date_str + "_checklist.odt")
        xlsx_curr_main_exists, odt_curr_main_exists = os.path.exists(
            xlsx_current_main_path), os.path.exists(odt_current_main_path)

        if xlsx_curr_main_exists and odt_curr_main_exists:
            state = "Initial_main_spreadsheet_exists_ambiguity_current"
            message = "Ambiguity: Both xlsx and odt spreadsheets exist for the current date ({}). " \
                      "Please keep only one of them, or remove them both if you wish to attempt to " \
                      "build a new main spreadsheet from the previous days, then click 'Load Spreadsheet'" \
                      ".".format(current_date_str)
            main_spreadsheet_path = ""
        elif xlsx_curr_main_exists != odt_curr_main_exists:
            state = "Initial_main_spreadsheet_ready"
            message = "Main spreadsheet {} was successfully detected.".format(
                xlsx_current_main_path)
            main_spreadsheet_path = xlsx_current_main_path if xlsx_curr_main_exists else odt_current_main_path
        else:
            # If reached here, there is no main spreadsheet for the current day!
            # Attempt to create it from the previous days (by copying from previous
            # main or merging previous main + checklist).
            xlsx_prev_main_exists, odt_prev_main_exists = os.path.exists(
                xlsx_previous_main_path), os.path.exists(odt_previous_main_path)
            xlsx_prev_checklist_exists, odt_prev_checklist_exists = os.path.exists(
                xlsx_previous_checklist_path), os.path.exists(odt_previous_checklist_path)
            if not(xlsx_prev_main_exists or odt_prev_main_exists):
                state = "Initial_main_spreadsheet_missing_both_current_and_previous"
                message = "No main spreadsheet found for the current date ({}) or the previous date ({}). " \
                          "Please make sure you have at least one of these two spreadsheets, " \
                          "then click 'Load Spreadsheet'.".format(
                              current_date_str, previous_date_str)
                main_spreadsheet_path = ""
            elif xlsx_prev_main_exists and odt_prev_main_exists:
                state = "Initial_main_spreadsheet_missing_ambiguity_previous_main"
                message = "No main spreadsheet found for the current date ({}). While attempting to" \
                          "produce a new current main spreadsheet, the program ran into an ambiguity: " \
                          "Both xlsx and odt main spreadsheets exist for the previous date ({}). " \
                          "Please keep only one of them, then click " \
                          "'Load Spreadsheet'.".format(
                              current_date_str, previous_date_str)
                main_spreadsheet_path = ""
            else:
                # If reached here, the path to the previous main file is well known.
                # It is now left to determine whether the checklist file will be available as well.
                prev_main_path = xlsx_previous_main_path if xlsx_prev_main_exists else odt_previous_main_path
                if not (xlsx_prev_checklist_exists or odt_prev_checklist_exists):
                    state = "Initial_main_spreadsheet_ready_after_copying_from_prev_main"
                    message = "No main spreadsheet found for the current ({}) date. Since " \
                              "there is no checklist spreadsheet for the previous date ({}), " \
                              "the current main file was created as an exact copy of the previous main " \
                              "file.".format(current_date_str,
                                             previous_date_str)
                    main_spreadsheet_path = xlsx_current_main_path if xlsx_prev_main_exists else odt_current_main_path
                    copyfile(
                        xlsx_previous_main_path if xlsx_prev_main_exists else odt_previous_main_path, main_spreadsheet_path)
                elif xlsx_prev_checklist_exists and odt_prev_checklist_exists:
                    state = "Initial_main_spreadsheet_missing_ambiguity_previous_checklist"
                    message = "No main spreadsheet found for the current date ({}). While attempting to" \
                              "produce a new current main spreadsheet, the program ran into an ambiguity: "\
                              "Both xlsx and odt spreadsheets exist for the previous date ({}) checklist. " \
                              "Please keep only one of them, then click 'Load Spreadsheet'.".format(
                                  current_date_str, previous_date_str)
                    main_spreadsheet_path = ""
                else:
                    # At this point the path to the previous main file is well known.
                    #           and the path to the previous checklist file is well known
                    prev_checklist_path = xlsx_previous_checklist_path if xlsx_prev_main_exists else odt_previous_checklist_path
                    state = "Initial_main_spreadsheet_ready_after_merge"
                    message = "The current main spreadsheet was successfully created by " \
                              "merging {} with {}. ".format(
                                  prev_main_path, prev_checklist_path)
                    main_spreadsheet_path = xlsx_current_main_path if xlsx_previous_main_path else odt_current_main_path
                    merge_succeeded, merge_errmsg = merge_checklist_to_main(
                        prev_checklist_path, prev_main_path, main_spreadsheet_path)
                    message = message + "\n\n" + merge_errmsg if merge_errmsg != "" else message
                    if not merge_succeeded:
                        state = "Initial_main_spreadsheet_missing_merge_failed"
                        message = "The current main spreadsheet couldn't be created by merging " \
                                  " {} with {}. Please try removing the checklist, clicking 'Load Spreadsheet' " \
                                  "and then once the new current main spreadsheet is ready - update" \
                                  "the tested people via a manual editing of the spreadsheet and relaunching this app." \
                                  "".format(prev_main_path,
                                            prev_checklist_path)
                        main_spreadsheet_path = ""

        return state, message, main_spreadsheet_path

    def solve(self, Bmin=2, Bmax=6, integer_programming=False,
              normalized_coverage=True, secondary_objective_coefficient=0.01, risk_manager=None) -> Tuple[bool, str]:
        """
        Solve the people selection for every natural budget B in the range [Bmin, Bmax]
        Gather a solution to each such B under self.solution_dictionary[B].
        :param Bmin: integer, a budget to start from
        :param Bmax: integer, a maximum budget to consider
        :param progress_widget -  a tk label, which can receive text updates, or None - then just ignore it
        :return: a tuple with a boolean indicating the success, and a string carrying an
                 error message if necessary
        """
        if self.state == "Initial_main_spreadsheet_loaded":
            self.solutions_dictionary = {}
            self.fig_output_dir = os.path.join(self.root, "Figures", self.current_date.strdate)
            self.progress = (0, Bmax + 1 - Bmin)
            pbar = tqdm.tqdm(total=Bmax + 1 - Bmin)
            ws_success, msg = produce_weighted_risk_sheet(self.organization_df, self.risk_df,
                                                          self.main_spreadsheet_path,
                                                          Institution(self.organization_df, self.risk_df,
                                                                      self.current_date, risk_manager))
            for B in range(Bmin, Bmax + 1):
                pbar.set_description()
                pbar.update(1)

                self.progress = (lambda x: (x[0]+1, x[1]))(self.progress)
                # New Institution including weight calculation and discounting - important to create a new
                # instance to override the weight updates performed by the previous budget selections.
                self.institution = Institution(
                    self.organization_df, self.risk_df, self.current_date, risk_manager)
                problem = SelectCandidatesForTest(B=B, institution=self.institution,
                                                  integer_programming=integer_programming,
                                                  normalized_coverage=normalized_coverage,
                                                  secondary_objective_coefficient=secondary_objective_coefficient)
                sampled_person_lst = problem.solve(
                    path=self.solver_path, verbosity=0)
                if sampled_person_lst is None:
                    msg += "Solver failed while solving B={}".format(B)
                    self.solutions_dictionary = None
                    self.fig_output_dir = None
                    self.state = "Initial_main_spreadsheet_loaded"
                    self.message = msg
                    return False, msg
                sampled_groups_lst = self.institution.get_groups_of_people(
                    sampled_person_lst, format="list")

                # mark the selected people as if they were tested right away
                self.institution.update_test_date(
                    sampled_person_lst, self.current_date)
                self.institution.update_weights(self.current_date)

                # record history
                # self.institution.draw(node_size=100, marked_nodes=sampled_person_lst+sampled_groups_lst,
                #                       output_dir=self.fig_output_dir,
                #                       output_filename="Graph_B_{}".format(B),
                #                       output_type="png", figsize=(8, 12), margins=(0.05, 0.21), font_size=6)
                self.solutions_dictionary[B] = dict(sampled_person_lst=sampled_person_lst,
                                                    sampled_groups_lst=sampled_groups_lst,
                                                    wV=np.array([self.institution.nodes_attributes[person]['w'] for person in
                                                                 self.institution.person_lst], dtype=np.float32),
                                                    wE=np.array([self.institution.nodes_attributes[group]['w'] for group in
                                                                 self.institution.group_lst], dtype=np.float32))
            pbar.close()

            # Plot of the w(e) and the w(v) as a function of B (one line per w(e)) -
            # plot_budget_exploration(solutions_dictionary=self.solutions_dictionary,
            #                         institution=Institution(
            #                             self.organization_df, self.risk_df, self.current_date, risk_manager),
            #                         plot_dir=self.fig_output_dir, break_to_smaller_plots=False)
            self.state = "Solved"
            msg += "Successfully solved for budgets {}-{}".format(Bmin, Bmax)
            self.message = msg
            return True, msg
        else:
            msg = "The spreadsheet must be loaded and ready for a solution"
            self.message = msg
            return False, msg

    def produce_checklist(self, budget):
        state, message = produce_checklist(self.solutions_dictionary[budget]['sampled_person_lst'], self.current_date, self.spreadsheet_directory,
                                           "xlsx" if self.main_spreadsheet_path[-4:] == "xlsx" else "odt")
        return state, message
