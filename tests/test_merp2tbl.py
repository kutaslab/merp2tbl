#!/usr/bin/env python
"""merp2tbl tests"""

import subprocess
import os
import os.path
import re
from pathlib import Path
import hashlib
import pandas as pd
import pytest

import merp2tbl.merp2tbl as merp2tbl

IS_CI = "ACTION" in os.environ.keys()

skip_ci = pytest.mark.skipif(IS_CI, reason="requires 32-bit binary")

p = Path(".")
os.chdir(p / "tests" / "data")
good_mcfs = [str(x) for x in p.glob("*good*.mcf")]
softerror_mcfs = [str(x) for x in p.glob("*softerror*.mcf")]
harderror_mcfs = [str(x) for x in p.glob("*harderror*.mcf")]

MIN_GOOD_MCF = "test_minimal_good.mcf"

TABLE_MD5 = {
    "baseline_good.tsv": "fcbb50bce149d4aee2f2ec613533499b",
    "baseline_reset_good.tsv": "49d6ff5097d8f5b71d124ba8f9a76277",
    "baseline_softerrors.tsv": "a5aa60a8fdf7535755dea9d5a84e3856",
    "files_reset_good.tsv": "875b95486d5391f4b1a95d6c2ee27d6e",
    "minimal_good.tsv": "14daf79f2c4f2c7ff612ab7dc795cb21",
    "newfiles_good.tsv": "c648069159286977bef829adcb13f0b8",
    "nobaseline_good.tsv": "b939f4f2980ea543c12f5f8fef61a1aa",
    "softerrors.tsv": "e721a09baa0e77344154840471278aa1",
    "typical_baseline_good.tsv": "8b19d2814c2cbd3a1913701b82f19219",
    "typical_good.tsv": "6d90aff002c01d60ce88b46736daafc4",
}

DAT_MD5 = {
    "baseline_good.dat": "6ca7f03378edf684c638b73b7b7670d9",
    "baseline_reset_good.dat": "a335f219726fbf509169ea86118498e9",
    "baseline_softerrors.dat": "246cccd03e5e824e9b6278789428bacb",
    "files_reset_good.dat": "cabd8c2d88550777e741f09522e982d9",
    "minimal_good.dat": "5f859a7b8ac32b084315194004bb4997",
    "newfiles_good.dat": "e34a50173b9f2b427f0e57bb45ce6b06",
    "nobaseline_good.dat": "75b23c2188cde0e2399f0289019d3e4d",
    "softerrors.dat": "5559398d7ce4efdd3fbdcad15e880cc4",
    "typical_baseline_good.dat": "9297c1fc74d19a922aa868f93b4101e3",
    "typical_good.dat": "9297c1fc74d19a922aa868f93b4101e3",
}

# ------------------------------------------------------------
# set up
@skip_ci
def test_write_tsv_dat():
    """run locally and write results"""
    for mcf in good_mcfs + softerror_mcfs:
        tsv_f = mcf.replace("mcf", "tsv")
        pd.DataFrame(merp2tbl.run_merp(mcf)).to_csv(tsv_f, sep="\t")

        # uncomment run merp -d and update gold standard values
        dat_f = mcf.replace("mcf", "dat")
        proc_res = subprocess.run(
            ["merp", "-d", mcf], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        with open(dat_f, "wb") as dat:
            dat.write(proc_res.stdout)


# ------------------------------------------------------------
# CI testable
def test_check_md5():
    """ensure the md5s are still good"""
    for mcf in good_mcfs + softerror_mcfs:

        tsv_f = mcf.replace("mcf", "tsv")
        with open(tsv_f, "rb") as table:
            assert TABLE_MD5[tsv_f] == hashlib.md5(table.read()).hexdigest()

        dat_f = mcf.replace("mcf", "dat")
        with open(dat_f, "rb") as dat:
            assert DAT_MD5[dat_f] == hashlib.md5(dat.read()).hexdigest()


def test_smoke_parse_merpfile():
    """just parse"""
    for mcf in good_mcfs + softerror_mcfs:
        merp2tbl.parse_merpfile(mcf)

    for mcf in harderror_mcfs:
        with pytest.raises(NotImplementedError):
            merp2tbl.parse_merpfile(mcf)


def test_table_dat():
    """check the locally generated files haven't changed"""
    for mcf in good_mcfs + softerror_mcfs:

        tsv_f = mcf.replace("mcf", "tsv")
        with open(tsv_f, "rb") as table:
            assert TABLE_MD5[tsv_f] == hashlib.md5(table.read()).hexdigest()

        dat_f = mcf.replace("mcf", "dat")
        with open(dat_f, "rb") as dat:
            assert DAT_MD5[dat_f] == hashlib.md5(dat.read()).hexdigest()


# ------------------------------------------------------------
# not CI testable
@skip_ci
def test_validate_merp2tbl():
    """ this checks all non-NA data output matches merp output row for row """

    for mcf in good_mcfs + softerror_mcfs:
        print("testing ", mcf)

        # run merp2tbl
        result = merp2tbl.run_merp(mcf)
        merp2tbl_vals = []
        for i, res in enumerate(result):
            val = res["value_f"]
            if not val == "NA":
                val = float(val)
            merp2tbl_vals.append(val)

        # run merp -d and slurp values
        proc_res = subprocess.run(
            ["merp", "-d", mcf], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
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
                (
                    merp_vals[i] == merp2tbl_vals[i]
                    for i, v in enumerate(merp2tbl_vals)
                    if not v == "NA"
                )
            )


@skip_ci
def test_merp2tbl_output_format():
    """smoke test formatter"""
    for mcf in good_mcfs + softerror_mcfs:
        result = merp2tbl.run_merp(mcf)

        for fmt in ["tsv", "yaml"]:
            print("# " + "-" * 40)
            print(f"# mcf: {mcf} format: {fmt}")
            print("# " + "-" * 40)
            merp2tbl.format_output(result, mcf, fmt=fmt)
            print()


@skip_ci
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
            for fmt in ["tsv", "yaml"]:
                print("# " + "-" * 40)
                print("# mcf: {0} format: {1}".format(mcf, format))
                print("# " + "-" * 40)
                merp2tbl.format_output(result, mcf, fmt=fmt, out_keys=cols)
                print()
