__author__ = "Kostya Berestizshevsky"
__version__ = "0.1.0"
__license__ = "MIT"
import os
import itertools
import numpy as np
import networkx as nx
import pandas
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from Util.numeric import modified_sigmoid_vector
from MyDate import MyDate
from RiskManager import RiskManager
from typing import Tuple, List, Union, Iterable


class Institution:

    def __init__(self, organization_df: pandas.DataFrame, risk_df: pandas.DataFrame, current_date: MyDate,
                 risk_manager: RiskManager):

        # Flat Data
        self.num_organization_columns_that_arent_group_names = 4
        self.num_risk_df_columns_that_arent_risk_factors = 4
        person_details_columns_list = []
        for i in range(self.num_organization_columns_that_arent_group_names):
            person_details_columns_list.append(organization_df[organization_df.columns[i]])
        self.current_date = current_date
        self.group_lst = list(organization_df.columns[self.num_organization_columns_that_arent_group_names:])
        self.person_lst = ["_".join(wid_cid_fn_pos_Tuple) for wid_cid_fn_pos_Tuple in zip(*person_details_columns_list)]
        self.person_idx_to_name_dict = {pid: pname for pid, pname in enumerate(self.person_lst)}
        self.group_idx_to_name_dict  = {gid: gname for gid, gname in enumerate(self.group_lst)}
        self.person_name_to_idx_dict = {pname: pid for pid, pname in enumerate(self.person_lst)}
        self.group_name_to_idx_dict  = {gname: gid for gid, gname in enumerate(self.group_lst)}

        # Graph
        self.G = nx.Graph()
        self.G.add_nodes_from(self.person_lst + self.group_lst)
        for personid_name_tuple, group in itertools.product(enumerate(self.person_lst), self.group_lst):
            personid, person = personid_name_tuple
            if organization_df[group][personid]:
                self.G.add_edge(person, group)

        # Set the weight attribute for each node in the graph - both in self.nodes_attributes and in self.G
        self.risk_manager = risk_manager
        self.nodes_attributes = {}
        self.init_nodes_attributes(risk_df)

    def get_discount_factor(self, t: MyDate, ts: MyDate):
        """
        Given the current time "t" and the most recent time ts at which a sampling was made
        return the discount factor for this time interval

        :param t  current time step
        :param ts: most recent time of sampling (disease testing)
        :return: float in [0,1], the risk discount factor that should be applied to the weighted risks.
        """
        if ts is None:
            return 1.0
        else:
            time_elapsed = t - ts
            return self.risk_manager.get_discount(time_elapsed)

    def init_nodes_attributes(self, risk_df: pandas.DataFrame):
        """
        Sets each person a dictionary with the following 3 values:
            'r': initial risk - is set to the provided risk (as provided in the risk_df)
            'ts': time of the most recent test date of this person
            'w': current weight - the discounted risk
        Sets each group a dictionary with the following 3 values:
            'w': current weight - equal to the sum of all the weights of the people associated with this group

        This function updates both the self.nodes_attributes and the self.G

        :param risk_df: a pandas dataframe carrying 3 columns of people id data,
                        followed by 1 column of 'Date of last COVID19 test' or 'תאריך בדיקה אחרון'
                        and followed the risk factor columns (as many as needed)
        :return:
        """

        covid_test_col_str = 'Date of last COVID19 test' if 'Date of last COVID19 test' in risk_df.columns else 'תאריך בדיקה אחרון'
        num_risk_factors = len(risk_df.columns) - self.num_risk_df_columns_that_arent_risk_factors
        risk_factor_coefficients = self.risk_manager.get_coefficients(num_risk_factors)

        for personid, person in enumerate(self.person_lst):
            personal_risk_vector = np.array(risk_df.iloc[personid, self.num_risk_df_columns_that_arent_risk_factors:],
                                            dtype=np.float32)
            personal_weighted_risk_vector = np.multiply(personal_risk_vector, risk_factor_coefficients)
            personal_static_risk = np.sum(personal_weighted_risk_vector)
            personal_test_date_str = risk_df[covid_test_col_str][personid]
            personal_test_date = MyDate(strdate=personal_test_date_str) if personal_test_date_str != "" else None
            self.nodes_attributes[person] = {'weighted_risk_vector': personal_weighted_risk_vector,
                                             'discount_factor' : 1.0,
                                             'r' : personal_static_risk,
                                             'ts': personal_test_date,
                                             'w' : 0.0}
        for group in self.group_lst:
            self.nodes_attributes[group] = {'w': 0.0}

        self.update_weights(current_date=self.current_date)  # this recalculates the group weights and updates the graph

    def update_test_date(self, sampled_person_lst: list, test_date: MyDate):
        """
        Update the state of the sampled_person_lst such that their sampling time is
        update to the provided "sampling_time_step" value.

        This function updates both the self.nodes_attributes and the self.G

        :param sampled_person_lst:list of strings
        :param test_date: a date at which the person was tested
        :return:
        """

        for person in sampled_person_lst:
            self.nodes_attributes[person]['ts'] = test_date
        nx.set_node_attributes(self.G, self.nodes_attributes)

    def update_weights(self, current_date: MyDate):
        """
        (1) Update the weights (by discounting the risks) of all the people in the organization
        (2) Update the discount_factors (lambda) of all the people in the organization, based on
                   the last disease testing date relative to the "current_date".
        (3) Recalculates the weights of all the groups, as a consequence of the peoples' weight update.

        The peoples' weight update is according to the following strategy:
        if the person was not sampled or it was sampled more than 10 days ago --> his weight will be his initial_risk
        if the person was sampled during the last week --> his weight is 0.0
        if the person was sampled

        This function updates both the self.nodes_attributes and the self.G

        :param current_date: a date for which the weights of the people (and of the groups)
                             should be recalculated. The recalculation will be a result of
                             a new time intervals between the date each person was tested,
                             and the current_date (due to a discount factor).
        """

        # (1+2) recalculate the person discount factors and weights
        for person in self.person_lst:
            #  this person was sampled before, apply the strategy!
            discount_factor = self.get_discount_factor(current_date, self.nodes_attributes[person]['ts'])
            self.nodes_attributes[person]['discount_factor'] = discount_factor
            self.nodes_attributes[person]['w'] = self.nodes_attributes[person]['r'] * discount_factor

        # (3) recalculate the group weights
        for group in self.group_lst:
            self.nodes_attributes[group]['w'] = sum(self.nodes_attributes[person]['w'] for person in self.G.neighbors(group))

        # (finally) plug all the node_attributes back into the graph structure.
        nx.set_node_attributes(self.G, self.nodes_attributes)

    def get_groups_of_people(self, person_lst, format="dict"):
        """
        Given a list of people, determine the groups that are associated with them.
        :param person_lst: list of strings, with a person (node) name in each item.
        :param format: "list" - return only the list of the group names, that are covered by the people
                       "dict" - return a dictionary of the groups that this people is associated with,
                                 The returned dictionary has group_names as keys and people count as value
        :return: dictionary of group:num_sampled_person
        """
        sampled_groups_dict = {}
        for group_lst_of_person in [list(self.G.neighbors(person)) for person in person_lst]:
            for group in group_lst_of_person:
                if group in sampled_groups_dict:
                    sampled_groups_dict[group] += 1
                else:
                    sampled_groups_dict[group] = 1

        if format == "dict":
            return sampled_groups_dict
        elif format == "list":
            return list(sampled_groups_dict.keys())
        else:
            raise TypeError("For the format keyword 'format' the only acceptable "
                            "values are 'dict' or 'list'. Given:{}".format(format))

    def get_people_of_one_group(self, group):
        assert group in self.group_lst
        return list(self.G.neighbors(group))

    def draw(self, node_size=200, marked_nodes=[], output_dir=None, output_filename=None, output_type="png",
             keep_fig_open=False, figsize=(16, 24), margins=0.2, font_size=12, crop_center=False):
        """
        Draws (using matplotlib) the bipartite graph representing the assignment of sets of people to the sets of groups.
        :param font_size:
        :param margins:
        :param figsize:
        :param node_size: size of a vertex in the plot that will be produced
        :param marked_nodes: a subset of the person list and group_lists. These vertices will be marked with red
        :param output_dir - if none, then no file will be produced, otherwise, an image file will be produced in this directory
        :param output_filename - if none, then no file will be produced, otherwise, an image file will be produced carrying this name
        :param crop_center: True if you want to crop the huge white border around the figure.
        :param keep_fig_open - if True then the figure will remainopen after the function returns
        :return:
        """
        if output_dir is not None and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        fig = plt.figure(figsize=figsize)
        if type(margins)==tuple:
            plt.margins(y=margins[0], x=margins[1])
        else:
            plt.margins(margins)
        ax = plt.gca() if not (output_dir is None or output_filename is None) else None
        node_positions = nx.bipartite_layout(self.G, nodes=self.person_lst, scale=1)
        attrributes_positions = {k: (v[0], -0.008 + v[1]) for k, v in node_positions.items()}
        selected_positions_to_mark = {}
        selected_edge_to_mark = [] # list of edges of a format (person,group)
        for node_name in marked_nodes:
            selected_positions_to_mark[node_name] = node_positions[node_name]
            if node_name in self.person_lst:
                for group_name in self.G.neighbors(node_name):
                    selected_edge_to_mark.append((node_name,group_name))

        nx.draw_networkx_nodes(self.G, node_positions,
                               nodelist=self.group_lst,
                               node_color='g',
                               node_size=node_size,
                               font_size=font_size,
                               alpha=0.8,
                               ax=ax)
        nx.draw_networkx_nodes(self.G, node_positions,
                               nodelist=self.person_lst,
                               node_color='b',
                               node_size=node_size,
                               font_size=font_size,
                               alpha=0.8,
                               ax=ax)
        nx.draw_networkx_nodes(self.G, node_positions,
                               nodelist=selected_positions_to_mark,
                               node_color='r',
                               node_size=node_size * 2,
                               font_size=font_size,
                               alpha=0.8,
                               ax=ax)
        nx.draw_networkx_edges(self.G, node_positions,
                               edgelist=selected_edge_to_mark,
                               width=2.0, edge_color='r',
                               font_size=font_size,
                               style='solid',
                               ax=ax)
        nx.draw(self.G, node_positions,
                with_labels=True, node_color="skyblue",
                font_size=font_size,
                alpha=0.5, linewidths=2, ax=ax)

        node_to_attr_string_dict = {}
        w_attributes = nx.get_node_attributes(self.G, 'w')
        r_attributes = nx.get_node_attributes(self.G, 'r')
        ts_attributes = nx.get_node_attributes(self.G, 'ts')
        for person in self.person_lst:
            node_to_attr_string_dict[person] = "(w={:.2f} ".format(w_attributes[person])
            node_to_attr_string_dict[person] += ", r={:.2f}".format(r_attributes[person])
            ts_str = str(ts_attributes[person]) if ts_attributes[person] != -1 else "None"
            node_to_attr_string_dict[person] += ", ts={})".format(ts_str)
        for group in self.group_lst:
            node_to_attr_string_dict[group] = "(w={:.2f}) ".format(w_attributes[group])

        nx.draw_networkx_labels(self.G, attrributes_positions, labels=node_to_attr_string_dict, font_size=font_size,)
        if output_dir is not None and output_filename is not None:
            # if "selected" in output_filename:
            #     fig_title = output_filename[6:].replace(":", " = ").replace("_", " people ")
            # elif "before" in output_filename:
            #     fig_title = output_filename[6:].replace(":"," = ").replace("_"," ") + " selection"
            try:
                picid = int(output_filename[-4:])
                if picid % 2 == 1:
                    fig_title = "t = {}, before test candidate selection".format((picid-1)//2)
                else:
                    fig_title = "t = {}, after test candidate selection".format((picid - 2) // 2)
                ax.set_title(fig_title, fontsize=40)
            except ValueError:
                pass
            if crop_center:
                ax.set_axis_off()
                fig.subplots_adjust(left=0, bottom=0, right=0, top=0, wspace=0, hspace=0)
            fig.savefig(os.path.join(output_dir, output_filename+"."+output_type))
        if not keep_fig_open:
            plt.close(fig)

    def print_coverage_per_group(self, sampled_person_lst: List[str], normalize_coverage: bool = True):
        """
        Given a list of sampled people, this function prints to the std-output the coverage c(e) obtained in each
        group e (individually).
        :param normalize_coverage: bool - set to True if a coverage of each group should be normalized by
                                          by the weight of the group.
        :param sampled_person_lst: list of person
        """
        print("Coverage per group:")
        for group in self.group_lst:
            people_of_group_lst = self.get_people_of_one_group(group)
            group_coverage = 0.0
            group_num_sampled_person = 0
            for person in people_of_group_lst:
                if person in sampled_person_lst:
                    group_coverage += self.nodes_attributes[person]['w']
                    group_num_sampled_person += 1
            if normalize_coverage:
                group_cov_norm = self.nodes_attributes[group]['w'] if self.nodes_attributes[group]['w'] != 0 else 1
                group_coverage = group_coverage / group_cov_norm
            print(' coverage({}) = {:.3f} ({}/{} person)'.format(group, group_coverage, group_num_sampled_person,
                                                                 len(people_of_group_lst)))