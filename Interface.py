import os
import json
import time
import numpy as np
import networkx as nx
from itertools import starmap, filterfalse

from App.Control import Control
from MyDate import check_strdate, MyDate

from flask import Flask, request, jsonify, Response


app = Flask(__name__)
ctl = Control(root=os.path.abspath("../"),
              spreadsheet_directory="Spreadsheets")


@app.route("/")
def hello():
    global ctl
    return "Hello"


@app.route("/spreadsheet/")
def get_spreadsheet():
    global ctl
    args = request.args
    try:
        ctl.load_spreadsheet(current_date=MyDate(strdate=args.get("currentDate")),
                             previous_date=MyDate(strdate=args.get("previousDate")))
        return jsonify(message=ctl.message, state=(ctl.state == "Initial_main_spreadsheet_loaded"))
    except Exception as err:
        return jsonify(error=str(err), state="")


@app.route("/solve/")
def get_solve():
    global ctl
    args = request.args
    try:
        state, message = ctl.solve(Bmin=int(args.get("Bmin")), Bmax=int(args.get(
            "Bmax")), secondary_objective_coefficient=float(args.get("coefficient")))
        response = {budget: (sol['sampled_person_lst'], sol['sampled_groups_lst'])
                    for budget, sol in ctl.solutions_dictionary.items()}
        return jsonify(message=message, state=state, response=response)
    except Exception as err:
        return jsonify(error=str(err), state=False)


@app.route("/progress")
def get_progress():
    global ctl

    def generate():
        p = ctl.progress
        while p[0] != p[1]:
            p = ctl.progress
            time.sleep(0.2)
            if p[1] != -1:
                yield "data:{0:.1f}\n\n".format(100*p[0]/p[1] if p[1] != 0 else 0)
            else:
                yield "data:0\n\n"
            if p[0] == p[1]:
                ctl.progress = (0, -1)
                break
        return "data:100\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route("/institution/")
def get_institution():
    global ctl
    try:
        group_lst = ctl.institution.group_lst
        solutions_dictionary = ctl.solutions_dictionary
        nB = len(solutions_dictionary)
        wE = np.zeros((nB, len(group_lst)))
        for Bid, B in enumerate(sorted(solutions_dictionary.keys())):
            wE[Bid] = solutions_dictionary[B]['wE']
        group = list(starmap(lambda g, w: {"group": g, "weight": w}, zip(
            group_lst, [wE[:, pid].tolist() for pid in range(len(group_lst))])))
        graph = dict(filter(
            lambda x: "_" in x[0], nx.to_dict_of_lists(ctl.institution.G).items()))
        return jsonify(state=True, response={"group": group, "graph":  graph})
    except Exception as err:
        return jsonify(error=str(err), state=False)


@app.route("/checklist/")
def get_checklist():
    global ctl
    args = request.args
    try:
        state, message = ctl.produce_checklist(int(args.get("budget")))
        return jsonify(message=message, state=state)
    except Exception as err:
        return jsonify(error=str(err), state=False)


# start process
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, threaded=True)
