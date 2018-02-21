import os
import sys

from pprint import pprint

from draco.spec import *
from draco.learn.helper import *
from draco.run import run

import logging

import copy

def absolute_path(p: str) -> str:
    return os.path.join(os.path.dirname(__file__), p)

def load_data(input_dir, format="compassql"):
    """ load compassql data
        Args: 
            input_dir: the directory containing a set of json compassql specs
            format: one of "compassql" and "vegalite"
        Returns:
            a dictionary containing name and the Task object representing the spec
    """
    files = [os.path.join(input_dir, f) for f in os.listdir(input_dir)]
    result = {}
    for fname in files:
        with open(fname, 'r') as f:
            content = json.load(f)
            content["data"]["url"] = os.path.join(input_dir, content["data"]["url"])
            if format == "compassql":
                spec = Task.from_cql(content, ".")
            elif format == "vegalite":
                spec = Task.from_vegalite(content)
            result[os.path.basename(fname)] = spec
    return result


def load_pairs(compassql_data_dir):
    """ load partial-full spec pairs from the directory
        Args:
            compassql_data_dir: the directory containing compassql data with
                 "input" and "output" directories specifying compassql input and output
        Returns:
            A dictionary mapping each case name into a pair of partial spec - full spec.
    """
    partial_specs = load_data(os.path.join(compassql_data_dir, "input"), "compassql")
    compassql_outs = load_data(os.path.join(compassql_data_dir, "output"), "vegalite")
    result = {}
    for k in partial_specs:
        result[k] = (partial_specs[k], compassql_outs[k])
    return result


def discriminative_learning(train_data, initial_weights, learning_rate=0.01, max_iter=100):
    """ discriminative learning for mln from partial and full specs """

    weights = {}
    for k in initial_weights:
        weights[k] = 0

    pprint(weights)
    logging.disable(logging.CRITICAL)

    t = 0
    while t < max_iter:
        print("[Iteration] {}".format(t))
        for case in train_data:
            partial_spec, full_spec = train_data[case][0], train_data[case][1]
            draco_rec = run(partial_spec, constants=weights, silence_warnings=True)

            pprint("=============")
            pprint(case)

            map_state = count_violations(draco_rec)
            truth_state = count_violations(full_spec)

            # get the names of violated rules in two specs
            violated_rules = set(list(map_state.keys()) + list(truth_state.keys()))

            for r in violated_rules:
                # get the num violations of the rule r
                n1 = map_state.get(r, 0)
                n2 = truth_state.get(r, 0)

                # since our weights are costs and we want to minimize the loss
                weights[r + "_weight"] += (n1 - n2)

            # the solution generated by visrec solution
            #print(draco_rec.to_vegalite_json())

        t += 1

    pprint(weights)


if __name__ == '__main__':
    train_data = load_pairs(absolute_path("../../data/compassql_examples"))
    weights = discriminative_learning(train_data, current_weights())
