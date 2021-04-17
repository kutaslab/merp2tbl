#!/usr/bin/env python
"""
Format long form merp text output as rows x columns or YAML document.

Notes
-----

  tab separated rows x columns or a YAML document

  merge in additional data from a separate YAML file

  select the columns (keys in YAML) of data

"""

import subprocess
import re
import hashlib
import pprint as pp
import warnings
import argparse

import yaml
from yamllint import linter
from yamllint.config import YamlLintConfig


# master list of merp measures except pkla which pkla which dumps
# 2 lines of data and is buggy wrt to soft errors

TRANSFORMS = ["baseline", "nobaseline"]
MERP_CATALOG = [
    "pkl",
    "centroid",
    "pka",
    "fpl" "fplf",
    "fpa",
    "fpaf",
    "lpkl",
    "lpka",
    "lfpl",
    "fal",
    "faa",
    "ppa",
    "npppa",
    "pnppa",
    "lnpppa",
    "lpnppa",
    "abblat",
    "bonslat",
    "pxonslat",
    "nxonslat",
    "rms",
    "meana",
    "mnarndpk",
    "slope",
    "pks",
]


# ------------------------------------------------------------
# helpers for the supplementary column data in the YAML file
# ------------------------------------------------------------

TAGF_LINT_CONFIG = YamlLintConfig("extends: default")


def lint_tags(tag_stream):
    """ run yamllint on tag file stream, die informatively on errors """
    errors = [e for e in linter.run(tag_stream, TAGF_LINT_CONFIG)]
    if errors != []:
        msg = "\n\n*** YAML ERRORS ***\n\n"
        for e in errors:
            msg += "{0}\n".format(e)
        raise Exception(msg)


def load_tagfile(tag_file):
    """ load tag file """
    with open(tag_file, "r") as f:
        tag_stream = f.read()
    lint_tags(tag_stream)  # raises exception on bad YAML
    return yaml.load(tag_stream, Loader=yaml.SafeLoader)


# ------------------------------------------------------------
# merp processing
# ------------------------------------------------------------
def parse_merpfile(merpfile):
    """parse merp command file

    See merp docs for merp command file format.

    At least one file is mandatory before a measurement is made

    merp's algorithm (probably)

    The list of files accumulates across the file. Baseline and
    channels are set when encountered. Wild cards expand current lists
    and apply current baseline when the measurement command is
    encountered.


    Parameters
    ----------
    merpfile : str
        name of a merp file

    Notes
    ------

    * channels, baseline, and nobaseline are supported

    * filter command line argument is not supported

    * some variant forms of merp command files are not supported

    * Native merp command processing is procedural, mixing optional
      command line arguments with an embedded baseline command,
      wildcard filename and channel expansion.

      This constructs a list of dicts, each dict containing the file
      and channel lists.

      To reconstruct the merp test output in canonical merp order,
      expand the list of dicts, channels and files like so

      ```
      for each dict in list:
          for each chan in chan list
             for file in file list
      ```

    * Construction of the list of dicts is governed by the
      state table, write out the node-arc FSA graph to see
      how it works.

      ```
      States:

      0 = -files, -channels (start, all measures fail)
      1 = -files, +channels (all measures fail)
      2 = +files, -channels (explicit chan measures OK, chan $ fails)
      3 = +files, +channels (all measures OK)
      4 = error (no files)
      5 = error (no wild channels)

      Transitions:

      (cmd, from_state) -> to_state


                        from_state
                     ----------------
          cmd        |  0   1   2  3
      -------------------------------
          file       |  2   3   2  3
      channels       |  1   1   3  3
      baseline       |  0   1   2  3
      measure chan   |  4   4   2  3
      measure $      |  4   4   5  3



    # typical

    file ...
    file ...

    # wild channels, required for $ expansion
    channels ...

    # baseline start stop or nobaseline is optional
    # default is avg preampling
    baseline start_n stop_n

    measure ...
    measure ...
    measure ...

    ```

    """

    with open(merpfile, "r") as f:
        merp_cmds = f.read()
    merp_cmds = re.sub(r"\n+", "\n", merp_cmds)
    merp_cmds = merp_cmds.split("\n")

    # cleanup whitespace
    merp_cmds = [
        re.sub(r"\s+", " ", m)
        for m in merp_cmds
        if re.match(r"(^$)|(^\s*#)", m) is None
    ]

    # cleanup trailing comments
    merp_cmds = [re.sub(r"\s+#.+$", "", m).strip() for m in merp_cmds]

    # whitelist commands we can handle
    implemented_cmds = ["file", "channels"] + TRANSFORMS + MERP_CATALOG

    # merp_cmds is a list of cmd_docs, each doc is a dict of
    # file, baseline, channel, measure key:values

    cmd_list = []

    from_state = 0  # initial state

    # list of minimal merp command 3-ples
    # (fileame,
    #  baseline_spec=(None, "baseline start stop", "nobaseline", measure_spec),
    # measure literal chan, file)

    cmd_list = []  #
    files = []  # for wildcard expansion, accumulate all files
    channels = []  # for wildcard expansion, set/reset when encountered
    baseline = (
        "default"  # if not overwritten, merp2tbl falls back to merp prestim default
    )

    for cmd_str in merp_cmds:
        if from_state == 6:
            # something bad happened
            raise ValueError("uh oh ... ", cmd_str)

        # split the command and process ...
        cmd_spec = cmd_str.split(" ")
        if cmd_spec[0] not in implemented_cmds:
            msg = "merpfile: {0} line: {1}\n".format(merpfile, cmd_str)
            msg += pp.pformat("choose from: " + " ".join(implemented_cmds))
            raise NotImplementedError(msg)

        cmd = cmd_spec[0]  # first field of merp command

        # handle file
        if cmd == "file":
            # state_key = 'file'
            files.append(cmd_spec[1])

        # always set channels
        if cmd == "channels":
            # state_key = 'channels'
            channels = [int(c) for c in cmd_spec[1:]]
            assert all([c >= 0 and c <= 64] for c in channels)

        # handle baselines
        if cmd in ["baseline", "nobaseline"]:
            # state_key = 'baseline'
            baseline = cmd_str

        # parse measurement string
        if cmd in MERP_CATALOG:
            meas_patt = (
                r"^\s*"
                r"(?P<measure>\S+)\s+"
                r"(?P<bin>\d+)\s+"
                r"(?P<chan>\S+)\s+"
                r"(?P<file>\S+)\s+"
                r"(?P<args>.*)\s*$"
            )

            meas_match = re.match(meas_patt, cmd_str)
            assert meas_match is not None
            meas_cmd = meas_match.groupdict()

            # four cases +/- chan wildcard, +/- file wildcard
            if meas_cmd["chan"] == "$":
                for c in channels:
                    if meas_cmd["file"] == "*":
                        for f in files:
                            # build and append the 3-ple
                            cmd_list.append(
                                (
                                    "file " + f,
                                    baseline,
                                    re.sub(r"\$", str(c), re.sub(r"\*", f, cmd_str),),
                                )
                            )
                    else:
                        cmd_list.append(
                            # build and append the 3-ple
                            (
                                "file " + meas_cmd["file"],
                                baseline,
                                re.sub(r"\$", str(c), cmd_str),
                            )
                        )
            else:
                if meas_cmd["file"] == "*":
                    for f in files:
                        # build and append the 3-ple
                        cmd_list.append(
                            ("file " + f, baseline, re.sub(r"\*", f, cmd_str))
                        )
                else:
                    # build and append the 3-ple
                    cmd_list.append(("file " + meas_cmd["file"], baseline, cmd_str))
    return cmd_list


def run_merp(mcf, debug=False):
    """wrapper parses command file mcf, runs the measurements one test at a time via  merp - stdin

    Parameters
    ----------
    mcf : string
        path to merp command file
    debug : bool
        if true reports internal command dict before running merp

    Returns
    -------
    measurements : list of dict
        each dict is parsed long form merp output of one measurement, ready to format

    Notes
    -----

    * merp commands with file or channel wildcards are expanded into
      individual measures and run through merp one at a time to capture
      stdout and stderr output for the specific test.

    * in the results dicts from the merp output all the values are
      strings and all the keys end in an underscore and printf-like
      data type specification character indicating the natural data
      type:

        _f = float    value : '10.7'
        _d = int      bin_d: '3'
        _s = str      chan_desc_s : 'MiPa'

    """

    measurements = []  # results

    # fetch the merp command file
    merp_cmds_list = parse_merpfile(mcf)

    # optionally report
    if debug:
        print("merpfile ", mcf)
        pp.pprint(merp_cmds_list)

    for merp_cmds in merp_cmds_list:
        cmd_str = None

        # build the single measure file lines, except baseline if 'default'
        cmd_str = "\n".join([cmd for cmd in merp_cmds if cmd is not "default"])
        cmd_str += "\n"

        # run it
        file_proc = subprocess.Popen(["echo", cmd_str], stdout=subprocess.PIPE)
        merp_proc = subprocess.Popen(
            ["merp", "-"],
            stdin=file_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = merp_proc.communicate()

        # catch merp hard errors with no data
        if re.match("^$", stdout.decode("utf-8")):
            msg = "No merp output: {0}".format(stderr.decode("utf-8"))
            msg += "merpfile: {0}: ".format(mcf)
            msg += pp.pformat(cmd_str)
            raise RuntimeError(msg)

        # parse the output
        measurement = parse_long_merp_output(stdout, stderr)

        # snapshot MD5 of file measured ...
        with open(measurement["erpfile_s"], "rb") as f:
            m = hashlib.md5()
            m.update(f.read())
        measurement.update({"erp_md5_s": m.hexdigest()})

        # log baseline
        if merp_cmds[1] == "default":
            measurement.update({"baseline_s": "default"})
        else:
            measurement.update({"baseline_s": merp_cmds[1]})

        # log file
        measurement.update({"merpfile_s": mcf})
        measurements.append(measurement)
    return measurements


def parse_long_merp_output(data_bytes, err_bytes):
    """parse long form merp output bytestring into a sensible dict

    Parameters
    ----------
    data_bytes : byte string
       one line of long form output merp sends to stdout
    err_bytes : byte string
       one line that merp sends to stderr, '' if all is well

    Returns
    -------
    row_dict : dict
        keys are column labels for the parsed output row, plus
        the key 'err' for stderr status, 0 = ok, 1 = some error

    Notes
    -----

    * named regex capture groups define the row_dict keys

    * merp long form output has a bug that farts out an extra 4 char
      channel label on the first line. The reg exp takes the first four
      characters of the channel label field, dropping the last 4, if
      any. So MiPa -> MiPa and MiCeMiPa -> MiCe

    """

    # tabs aren't expected but strip in case
    data = data_bytes.decode("utf-8").strip().replace("\t", " ")
    err = err_bytes.decode("utf-8")

    # if there is an error, first line is diagnostic
    err_match = re.match(r"(?P<error>^.*)\n", err)
    if err_match is not None:
        # squeeze extra whitespace
        err = re.sub(r"\s+", " ", err_match.groupdict()["error"])

    # Define one regex pattern per output line for
    # readibility/debugging

    # line 1 work around double label merp bug
    patt1 = (
        r"^Channel\s+"
        r"(?P<chan_desc_s>.{4})(?:.{4})*\s+Sum of\s+"
        r"(?P<epochs_d>\S+)"
    )

    # line 2 fixed length fields until the last.
    patt2 = (
        r"^.+\n"
        r"(?P<subject_s>.{41})"
        r"(?P<bin_desc_s>.{40})"
        r"(?P<condition_s>.{41})"
        r"(?P<expt_s>.{40})"
        r"(?P<meas_specs_s>.*)"
        r"[\\\\n]*"
    )

    # line 3 may not exist, e.g., on bad baseline error
    patt3 = (
        r".+\n.+\n"
        r"(?P<meas_desc_s>.+?)"
        r"(?P<value_f>[-\.\d]+)\s"
        r"(?P<units_s>\S+$)"
    )

    # scrape column names from the patterns and precompile
    col_names, re_specs = [], []
    for patt in [patt1, patt2, patt3]:
        names = re.findall(r"\\?P<(.+?)>", patt)
        col_names += names
        re_specs.append((names, re.compile(patt)))

    # init output dict to NA
    row_dict = dict([(col, "NA") for col in col_names])

    # First pass parse, override default 'NA' only on match
    for names, regex in re_specs:
        matches = None
        matches = regex.match(data)
        if matches is not None:
            row_dict.update(matches.groupdict())

    # parse the variable length meas_specs string
    meas_regex = re.compile(
        r"^"
        r"(?P<meas_label_s>\w+)\s+"
        r"(?P<bin_d>\d+)\s+"
        r"(?P<chan_d>\d+)\s+"
        r"(?P<erpfile_s>\S+)\s+"
        r"(?P<win_start_f>\d+)\s+"
        r"(?P<win_stop_f>\d+)\s*"
        r"(?P<meas_args_s>.*)"
    )

    meas_specs = meas_regex.match(row_dict["meas_specs_s"]).groupdict()
    assert len(meas_specs) == 7

    # add the new items
    kvs = [(k, v) for d in [row_dict, meas_specs] for k, v in d.items()]
    for k, v in kvs:
        row_dict[k] = v.strip()

    # drop the redundant bin and parsed chunks
    del row_dict["meas_specs_s"]

    # handle missing data
    if re.match(".+", err):
        row_dict["value_f"] = "NA"
        row_dict["merp_error_s"] = err
    else:
        row_dict["merp_error_s"] = "NA"

    # check measured value is convertible to numeric
    if row_dict["value_f"] != "NA":
        float(row_dict["value_f"])

    return row_dict


def format_output(results, mcf, fmt="tsv", out_keys=None, tag_file=None):
    """dump merp output to stdout in specified format

    Parameters
    ----------
    results : list of dict
        as returned by merp2tbl.run_merp()
    mcf : str
        path to merp file the output come from for data validation
    fmt : str ('tsv'), 'yaml'
        specifies tab-separated rows x columns or yaml doc output
    out_keys : list of str
        whitelist of column names to report
    tag_file : str (None)
        path to YAML file with additional column:values

    Notes
    -----

    """

    # helper to convert the merp string output to python scalar types
    def spec2dtype(key_fmt, val_str):
        """ converts val_str to data type according to _fmt, returns key, val 2-ple """

        spec_map = dict(s=str, f=float, d=int)  # map _fmt character to python data type

        # parse key_fmt
        key_spec = re.match("^(?P<key>.*)_(?P<spec>[fds])$", key_fmt)
        assert key_spec.groupdict()["spec"] in spec_map.keys()

        key = key_spec.groupdict()["key"]  # == key_fmt stripped of '_fmt'

        # strings including NA don't need conversion
        if key_spec.groupdict()["spec"] == "s" or val_str == "NA":
            val = val_str
        else:
            # coerce string to float or int
            val = spec_map[key_spec.groupdict()["spec"]](val_str)
        return key, val

    # set the output data types
    results = [dict([spec2dtype(k, v) for k, v in r.items()]) for r in results]

    # set the external data data if any
    if tag_file is not None:
        tags = load_tagfile(tag_file)

        # update results with the tags ... we could prescreen
        # more quickly but this allows diagnostic output on fail
        for k, v in tags.items():
            for i, r in enumerate(results):
                if type(v) in [str, int, float]:
                    r.update({k: v})
                elif type(v) is list and len(v) == 1:
                    r.update({k: v[0]})  # same tag all measurements
                elif type(v) is list and len(v) == len(results):
                    r.update({k: v[i]})  # ith tag -> ith measurement
                else:
                    msg = "bad tag in {0} ... {1}: {2}\n".format(tag_file, k, v)
                    msg += (
                        "value must be a single scalar value or "
                        "list of exactly as many values as measurements"
                    )
                    raise ValueError(msg)

    assert all(r.keys() == results[0].keys() for r in results)

    # handle the output column filter
    if out_keys is None:
        out_keys = sorted(results[0].keys())

    results_out = []
    for r in results:
        ro = dict()
        for k, v in r.items():
            if k in out_keys:
                ro.update({k: v})
        results_out.append(ro)

    # switch for the output type and dump
    if fmt is None:
        fmt = "tsv"
    assert fmt in ["tsv", "yaml"]

    if fmt == "tsv":
        # tab separate with header in out_key order
        header = "\t".join(out_keys) + "\n"
        data = "\n".join(
            ["\t".join([str(r[c]) for c in out_keys]) for r in results_out]
        )
        output = header + data

    if fmt == "yaml":
        output = "# generated by merp2tbl\n"
        output += yaml.dump(
            results_out, explicit_start=True, default_flow_style=False, canonical=False,
        )

    # sanity check 0 == good, >0 == warnings, <0 == fail
    vo, msg = validate_output(output, fmt, mcf)
    if vo < 0:
        raise RuntimeError(msg)
    elif vo > 0:
        warnings.warn(msg)

    return output


def validate_output(output, fmt, mcf):
    """compare values in merp2tbl output with merp -d row for row, non-NA must agree

    Parameters
    ----------
    output : dict
       as returned by format_output
    fmt : str
       'tsv' or 'yaml'
    mcf : str
       path to merp command file

    Returns
    -------
      rval, msg : 2-ple of int, str
        rval 0 = success, positive = warning, negative = fail
        msg = brief explanation
    """
    merp2tbl_vals = []
    if fmt == "yaml":
        for out in yaml.load(output, Loader=yaml.SafeLoader):
            if "value" in out.keys():
                merp2tbl_vals.append(out["value"])
            else:
                msg = "yaml value key not found, cannot validate data"
                return (1, msg)

    elif fmt == "tsv":
        out_lines = output.split("\n")
        header = out_lines[0].split("\t")
        value_idx = None
        try:
            value_idx = header.index("value")
        except ValueError:
            msg = "tsv value column not found, cannot validate data"
            return (2, msg)

        if value_idx is not None:
            merp2tbl_vals = [
                out_line.split("\t")[value_idx] for out_line in out_lines[1:]
            ]
            merp2tbl_vals = [v if v == "NA" else float(v) for v in merp2tbl_vals]
    else:
        raise ValueError("unknown format: ", fmt)

    if merp2tbl_vals == []:
        msg = "no merp2tbl values not found, cannot validate data"
        return (1, msg)

    # run merp -d and slurp values
    proc_res = subprocess.run(
        ["merp", "-d", mcf], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    merp_vals = [
        float(v)
        for v in proc_res.stdout.decode("utf-8").split("\n")
        if len(v.strip()) > 0
    ]

    # length mismatch
    if len(merp_vals) != len(merp2tbl_vals):
        msg = "merp2tbl " + mcf + "output value length mismatch"
        return -1

    # check value for value, skip NAs
    for i, v in enumerate(merp2tbl_vals):
        if v != "NA" and not merp_vals[i] == merp2tbl_vals[i]:
            msg = "merp2tbl {0} output line {1}: {2} != merp -d {3}".format(
                mcf, i, merp2tbl_vals[i], merp_vals[i]
            )
            return (-2, msg)
    return (0, "")


def main():
    """ wrapper for console_scripts shim """

    # set up parser
    PARSER = argparse.ArgumentParser(
        description="convert verbose merp output to standard data interchange formats"
    )

    # names
    PARSER.add_argument("mcf", metavar="mcf", type=str, help="merp command file")

    # collect optional column names to subset
    PARSER.add_argument(
        "-columns",
        type=str,
        nargs="+",
        dest="columns",
        help="names of columns to select for the output",
    )

    # output format
    PARSER.add_argument(
        "-format",
        type=str,
        metavar="format",
        dest="format",
        help=(
            "'tsv' for tab-separated rows x columns or "
            "'yaml' for YAML document output"
        ),
    )

    # supplementary data tags
    PARSER.add_argument(
        "-tagf",
        type=str,
        metavar="tagf",
        dest="tagf",
        help=(
            "tagf.yml YAML file with additional " "column data to merge with the output"
        ),
    )

    # supplementary data tags
    PARSER.add_argument(
        "-debug",
        action="store_true",
        dest="debug",
        help=("-debug mode shows command file parse before running merp"),
    )

    ARGS_DICT = vars(PARSER.parse_args())  # fetch from sys.argv

    RESULT = run_merp(ARGS_DICT["mcf"], ARGS_DICT["debug"])

    # validation built into formatter
    FORMATTED = format_output(
        RESULT,
        ARGS_DICT["mcf"],
        fmt=ARGS_DICT["format"],
        out_keys=ARGS_DICT["columns"],
        tag_file=ARGS_DICT["tagf"],
    )
    print(FORMATTED)
