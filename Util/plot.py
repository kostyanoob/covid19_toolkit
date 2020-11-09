__author__ = "Kostya Berestizshevsky"
__version__ = "0.1.0"
__license__ = "MIT"
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import numpy as np
from Institution import Institution
import os
import logging
import ezodf
logging.getLogger('matplotlib.font_manager').disabled = True


def savefig(output_dir, output_filename, dpi=300, save_copy_as_eps=True, eps_dpi=1000, verbose=False):
    """
    Saves the current figure to an image file.

    :param output_dir: <str> a path to the directory where the new file will be created
    :param output_filename: <str> the name of the filename to be created. Can be specified with an extension
                           such as "image1.jpg" and then the format will be inferred. Otherwise, when
                           no extension is specified - c.f. "image1", the default PNG format is used.
    :param dpi: <int> (default 300) the dpi resolution of the image to be saved
    :param save_copy_as_eps: <bool> (default True) True iff an eps (vector-graphics) copy should be created
    * Removes all commas from the filename, except for the last comma - crucial for the LaTex *

    :param eps_dpi: <int> (default 1000) the dpi resolution of the eps image to be saved
    :param verbose: <bool> True iff messages regarding file saving success should be displayed.
    :return: nothing
    """
    # pylab.rcParams.update({'figure.autolayout': True})
    assert (len(output_filename) > 0)
    output_filename_list = output_filename.split(".")
    if len(output_filename_list) >= 1 and not (output_filename_list[-1] in plt.gcf().canvas.get_supported_filetypes().keys()):
        output_filename = output_filename + ".png"
    plt.gcf().tight_layout()
    plt.savefig(os.path.join(output_dir, output_filename), dpi=dpi, bbox_inches="tight", pad_inches=0)
    if verbose:
        print("Saved plot to:" + os.path.join(output_dir, output_filename))
    if save_copy_as_eps:
        output_filename_list = output_filename.split(".")
        if len(output_filename_list) > 1 and output_filename_list[-1] in plt.gcf().canvas.get_supported_filetypes().keys():
            output_filename_list[-1] = ".eps"
        elif len(output_filename_list) == 1:
            output_filename_list.append(".eps")
        else:
            raise Exception("Could not store the eps image: Illegal output_filename")
        output_filename_eps = "".join(output_filename_list)
        plt.savefig(os.path.join(output_dir, output_filename_eps), format='eps', dpi=eps_dpi, bbox_inches="tight", pad_inches=0)
        if verbose:
            print("Saved plot to:" + os.path.join(output_dir, output_filename_eps))

def plotManyManyLines(common_x_lst, y_lst_of_lists, legends_lst, xtitleStr, ytitleStr, titleStr,
                  output_dir, output_filename, extras_dict=None, customPointAnnotation=None,
                  std_lst_of_lists=None, save_copy_as_eps=True):
    assert len(y_lst_of_lists) == len(legends_lst)
    num_lines = len(y_lst_of_lists)
    num_lines_per_plot = 10
    line_id_start=0
    while line_id_start<num_lines:
        line_id_end = min(num_lines, line_id_start + num_lines_per_plot)

        plotManyLines(common_x_lst, y_lst_of_lists[line_id_start:line_id_end],
                      legends_lst[line_id_start:line_id_end], xtitleStr, ytitleStr, titleStr,
                      output_dir, output_filename+"_{}-{}".format(line_id_start,line_id_end),
                      extras_dict, customPointAnnotation, std_lst_of_lists, save_copy_as_eps)

        line_id_start = line_id_end


def plotManyLines(common_x_lst, y_lst_of_lists, legends_lst, xtitleStr, ytitleStr, titleStr,
                  output_dir, output_filename, extras_dict=None, customPointAnnotation=None,
                  std_lst_of_lists=None, save_copy_as_eps=True):
    '''


    for python 3.5
    :param common_x_lst:
    :param y_lst_of_lists:
    :param legends_lst:
    :param xtitleStr:
    :param ytitleStr:
    :param titleStr:
    :param output_dir:
    :param output_filename:
    :return:
    '''

    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] - %(message)s')
    ld = logging.debug
    if 'font_size' in extras_dict:
        plt.rcParams.update({'font.size': extras_dict['font_size']})
    fig = plt.figure()
    plt.xlabel(xtitleStr)
    plt.ylabel(ytitleStr)
    plt.suptitle(titleStr)
    colors = ['r', 'g', 'b', 'c', 'm', 'y', 'k', "#96f97b", '#ae7181', '#0504aa', '#c1f80a', '#b9a281', '#ff474c'][
             :len(legends_lst)]
    if extras_dict is None:
        linewidth_list = [2] * len(y_lst_of_lists)
        markersize_list = [2] * len(y_lst_of_lists)
        legend_location = 0
        plt.yscale('linear')
        marker_list = ["."] * len(y_lst_of_lists)
    else:
        linewidth_list = extras_dict["linewidth_list"]
        markersize_list = extras_dict["markersize_list"]
        legend_location = extras_dict["legend_location"]
        if 'y_axis_scale' in extras_dict:
            plt.yscale(extras_dict["y_axis_scale"])
        if 'marker_list' not in extras_dict:
            marker_list = ['s', 'x', '*', '^', 'p', 'D', '>', '<', '+', 'o', '.'][
                          :len(legends_lst)] if 'marker_list' not in extras_dict else extras_dict['extras_dict']
        else:
            marker_list = extras_dict['marker_list']
        if 'markersize_list' in extras_dict:
            markersize_list = extras_dict["markersize_list"]
        else:
            markersize_list = [2] * len(y_lst_of_lists)

    if std_lst_of_lists is None or 'kill_errorbar' in extras_dict and extras_dict['kill_errorbar']:
        axes = [plt.plot(common_x_lst, y_lst, label=legenda, linewidth=linewidth, color=cllr, marker=marker, markersize=markersize) for
                cllr, y_lst, marker, linewidth, markersize, legenda  in
                zip(colors, y_lst_of_lists, marker_list, linewidth_list, markersize_list, legends_lst)]
    else:
        axes = [plt.errorbar(common_x_lst, y_lst, std_, label=legenda, linewidth=linewidth, color=cllr, marker=marker, markersize=markersize,
                               elinewidth=errorLineSize, capsize=errorLineSize)
                for cllr, y_lst, std_, marker, linewidth, markersize,  legenda, errorLineSize in
                zip(colors, y_lst_of_lists, std_lst_of_lists, marker_list, linewidth_list, markersize_list, legends_lst,
                    list(range(2, len(legends_lst) + 2)))]
    # pylab.legend(handles = [mpatches.Patch(color =cllr, label=legenda) for cllr, legenda in zip(colors,legends_lst)])
    plt.legend(loc=legend_location, markerscale=2)

    if not (customPointAnnotation is None):
        if type(customPointAnnotation) != list:
            customPointAnnotation = [customPointAnnotation]
        for pt in customPointAnnotation:
            if (pt >= min(common_x_lst) or pt <= max(common_x_lst)):
                annotation_mark_x = pt
                annotation_mark_y = min([min(t) for t in y_lst_of_lists])
                plt.plot([annotation_mark_x], [annotation_mark_y], '^', markersize=5)
                plt.annotate("", xy=(annotation_mark_x, annotation_mark_y),
                               arrowprops=dict(facecolor='#AAAAAA', shrink=0.05))
            else:
                ld("Warning: cannot annotate plot at point {}, since it's out of the range of X-axis".format(pt))

    # Save to file both to the required format and to png
    savefig(output_dir, output_filename, save_copy_as_eps=save_copy_as_eps)
    plt.close(fig)


def plot_budget_exploration(solutions_dictionary: dict, institution: Institution, plot_dir: str, break_to_smaller_plots: bool = True):
    """
    Plots the weights of the people as a function of B (test budget)
    :param solutions_dictionary:
    :param institution:
    :param plot_dir:
    :return:
    """
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    plot_function = plotManyManyLines if break_to_smaller_plots else plotManyLines
    nB = len(solutions_dictionary)
    x_axis_list = list(sorted(solutions_dictionary.keys()))
    budget_min, budget_max = min(x_axis_list), max(x_axis_list)
    wV = np.zeros((nB, len(institution.person_lst)))
    wE = np.zeros((nB, len(institution.group_lst)))
    for Bid, B in enumerate(sorted(solutions_dictionary.keys())):
        wV[Bid] = solutions_dictionary[B]['wV']
        wE[Bid] = solutions_dictionary[B]['wE']
    y_lst_of_lists = [wV[:, pid] for pid in range(len(institution.person_lst))]
    extras_dict = {"linewidth_list": [2] * len(y_lst_of_lists),
                   "markersize_list": [1] * len(y_lst_of_lists),
                   "legend_location": 0,
                   "y_axis_scale": 'linear',
                   "kill_errorbar": True}
    plot_function(common_x_lst=x_axis_list,
                  y_lst_of_lists=y_lst_of_lists,
                  legends_lst=[person for person in institution.person_lst],
                  xtitleStr="B", ytitleStr=r"$w_{person}(B)$",
                  titleStr=r"Person weights various test budgets $B\in\{" + "${},...,{}$".format(budget_min, budget_max) + r"\}$",
                  output_dir=plot_dir, output_filename='Person_risk_weight_B_{}-{}'.format(budget_min, budget_max),
                  extras_dict=extras_dict,
                  save_copy_as_eps=False)

    # Group weight plot
    y_lst_of_lists = [wE[:, pid] for pid in range(len(institution.group_lst))]
    extras_dict = {"linewidth_list": [1] * len(y_lst_of_lists),
                   "markersize_list": [1] * len(y_lst_of_lists),
                   "legend_location": 0,
                   "y_axis_scale": 'linear',
                   "kill_errorbar": True}
    plot_function(common_x_lst=x_axis_list,
                  y_lst_of_lists=y_lst_of_lists,
                  legends_lst=[group for group in institution.group_lst],
                  xtitleStr="B", ytitleStr=r"$w_{group}(B)$",
                  titleStr=r"Group weights various test budgets $B\in\{" + "${},...,{}$".format(budget_min, budget_max) + r"\}$",
                  output_dir=plot_dir, output_filename='Group_weight_B_{}-{}'.format(budget_min, budget_max), extras_dict=extras_dict,
                  save_copy_as_eps=False)
