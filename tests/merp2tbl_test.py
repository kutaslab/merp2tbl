#!/usr/bin/env python

import pdb
import subprocess
import os
import os.path
import glob
import re
from pathlib import Path

import merp2tbl.merp2tbl as merp2tbl
import pytest

p = Path(".")
os.chdir(p / "tests" / "testdata")
good_mcfs = [str(x) for x in p.glob("*good*.mcf")]
softerror_mcfs = [str(x) for x in p.glob("*softerror*.mcf")]
harderror_mcfs = [str(x) for x in p.glob("*harderror*.mcf")]


def test_minimal_good():

    mcf = "test_minimal_good.mcf"
    _ = merp2tbl.parse_merpfile(mcf)
    _ = merp2tbl.run_merp(mcf)


def test_load_merp_file():
    # go tests
    for mcf in good_mcfs:
        merp_cmds = merp2tbl.parse_merpfile(mcf)

    for mcf in softerror_mcfs:
        merp_cmds = merp2tbl.parse_merpfile(mcf)

    # nogo tests
    for mcf in harderror_mcfs:
        with pytest.raises(Exception):
            merp_cmds = merp2tbl.parse_merpfile(mcf)


def test_validate_merp2tbl():
    """ this checks all non-NA data output matches merp output row for row """

    for mcf in good_mcfs + softerror_mcfs:
        print("testing ", mcf)

        # run merp2tbl
        result = merp2tbl.run_merp(mcf)
        merp2tbl_vals = []
        for i, r in enumerate(result):
            val = r["value_f"]
            if not val == "NA":
                val = float(val)
            merp2tbl_vals.append(val)

        # run merp -d and slurp values
        proc_res = subprocess.run(
            ["merp", "-d", mcf], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        merp_vals = [
            float(v)
            for v in proc_res.stdout.decode("utf-8").split("\n")
            if len(v.strip()) > 0
        ]

        # if no merp error, check all values, else just the non-NAs
        if proc_res.stderr.decode("utf-8") == "":
            assert len(merp_vals) == len(merp2tbl_vals)
            assert merp_vals == merp2tbl_vals
        else:
            assert all(
                [
                    merp_vals[i] == merp2tbl_vals[i]
                    for i, v in enumerate(merp2tbl_vals)
                    if v is not "NA"
                ]
            )


def test_merp2tbl_output_format():
    for mcf in good_mcfs + softerror_mcfs:
        result = merp2tbl.run_merp(mcf)

        for format in ["tsv", "yaml"]:
            print("# " + "-" * 40)
            print("# mcf: {0} format: {1}".format(mcf, format))
            print("# " + "-" * 40)
            merp2tbl.format_output(result, mcf, fmt=format)
            print()


def test_select_columns():
    """ test column slicer for subsetting output """
    for mcf in good_mcfs + softerror_mcfs:

        result = merp2tbl.run_merp(mcf)
        n_cols = len(result[0].keys())
        col_names = [re.sub("_[dfs]$", "", k) for k in result[0].keys()]
        assert n_cols >= 2

        # select even and odd colums = 2 subsets that cover all columns
        for subset in [0, 1]:
            cols = [col_names[idx] for idx in range(subset, n_cols, 2)]
            for format in ["tsv", "yaml"]:
                print("# " + "-" * 40)
                print("# mcf: {0} format: {1}".format(mcf, format))
                print("# " + "-" * 40)
                merp2tbl.format_output(result, mcf, fmt=format, out_keys=cols)
                print()
