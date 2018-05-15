#!/usr/bin/env python

'''
Format long form merp text output as rows x columns or YAML document. 

Output options
-------
- tab separated rows x columns or a YAML document
- merge in additional data from a separate YAML file
- select the columns (keys in YAML) of data

'''

import subprocess
import re
import os.path
import hashlib
import pprint as pp

import yaml
from yamllint import linter
from yamllint.config import YamlLintConfig

# master list of merp measures except pkla which pkla which dumps
# 2 lines of data and is buggy wrt to soft errors

transforms = ['baseline', 'nobaseline']
merp_catalog = [
    'pkl', 'centroid', 'pka', 'fpl' 'fplf', 'fpa',
    'fpaf', 'lpkl', 'lpka', 'lfpl', 'fal', 'faa', 'ppa', 'npppa',
    'pnppa', 'lnpppa', 'lpnppa', 'abblat', 'bonslat', 'pxonslat',
    'nxonslat', 'rms', 'meana', 'mnarndpk', 'slope', 'pks'
]


# ------------------------------------------------------------
# helpers for the supplementary column data in the YAML file
# ------------------------------------------------------------

_tagf_config = YamlLintConfig('extends: default')
def lint_tags(tag_stream):
    ''' run yamllint on tag file stream, die informatively on errors '''
    errors = [e for e in linter.run(tag_stream, _tagf_config)]
    if errors != []:
        msg = '\n\n*** YAML ERRORS ***\n\n'
        for e in errors:
            msg += '{0}\n'.format(e)
        raise Exception(msg)

def load_tagfile(tag_file):
    with open(tag_file, 'r') as f:
        tag_stream = f.read()
    lint_tags(tag_stream) # raises exception on bad YAML
    return yaml.load(tag_stream)

# ------------------------------------------------------------
# merp processing
# ------------------------------------------------------------
def parse_merpfile(merpfile):
    '''parse merp command file

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

        for each dict in list:
          for each chan in chan list
             for file in file list 

    * Construction of the list of dicts is governed by the
      state table, write out the node-arc FSA graph to see
      how it works.
    
      States 
  
      0 = start
      1 = init/append file list
      2 = set/reset baseline, channel
      3 = init/append measure
      4 = error

      state table: 

      (cmd, from_state) -> to_state

                       from_state
                  -------------------
          cmd     |  0   1   2   3  4(Error)
      ----------------------------------
          file    |  1   1   1   3  -
      channels    |  4   2   2   2  -
      baseline    |  4   2   2   2  -
      <measure>   |  4   3   3   3  -

    Usage
    -----

    See merp docs for merp command file format.

    Files and channels may be reset, each measure command uses
    whatever the current value of file(s), channels.

    Not sure about baseline

    ```
    # at least one file is mandatory
    file ...
    file ...

    # channels is optional
    channels ...

    # baseline start stop or nobaseline is optional 
    baseline start_n stop_n

    # at least one measure is mandatory
    measure ...
    measure ...
    measure ...

    ```

    '''

    with open(merpfile, 'r') as f:
        merp_cmds = f.read()
    merp_cmds = re.sub('\n+','\n', merp_cmds)
    merp_cmds = merp_cmds.split('\n')

    # cleanup whitespace
    merp_cmds = [re.sub('\s+', ' ', m) for m in merp_cmds 
                 if re.match(r'(^$)|(^\s*#)',m) is None]

    # cleanup trailing comments
    merp_cmds = [re.sub('\s+#.+$', '', m).strip() for m in merp_cmds]

    # whitelist commands we can handle
    implemented_cmds = ['file', 'channels'] + transforms + merp_catalog

    # merp_cmds is a list of cmd_docs, each doc is a dict of 
    # file, baseline, channel, measure key:values

    cmd_dict = dict(files=[], channels='NA', baseline_s='NA', measures=[])
    cmd_list = [] 

    # state_table[state_key][from_state] -> next state
    state_table = dict(
        file =     [1, 1, 1, 1],
        channels = [4, 2, 2, 2],
        baseline = [4, 2, 2, 2],
        measure =  [4, 3, 3, 3])

    from_state = 0 # initial state

    for cmd_str in merp_cmds:

        if from_state == 4:
        # something bad happened
            raise ValueError('merp file command out of order?' + cmd)

        # split the command and process ...
        cmd_spec = cmd_str.split(' ')
        if cmd_spec[0] not in implemented_cmds:
            msg = 'merpfile: {0} line: {1}\n'.format(merpfile,cmd)
            msg += pp.pformat('choose from: ' + ' '.join(implemented_cmds))
            raise NotImplementedError(msg)

        cmd = cmd_spec[0] # first field of merp command
        if cmd == 'file':
            state_key = 'file'
            if from_state in [0, 2]:
                # start a new comand dict and set the first file
                # Note: state 2 is after channels/baseline before
                # measurement so amounts to a reset
                curr_dict = dict([(k,v) for k,v in cmd_dict.items()])
                curr_dict['files'] = [cmd_spec[1]] # reset

            elif from_state == 1: 
                # collecting files
                curr_dict['files'].append(cmd_spec[1]) # append

            elif from_state == 3:
                # state 3 is after a measure command, so push the current
                # command dict and start a new one
                cmd_list.append(curr_dict)
                curr_dict = dict([(k,v) for k,v in cmd_dict.items()])
                curr_dict['files'] = [cmd_spec[1]] # reset

        # handle channels
        if cmd == 'channels':
            state_key = 'channels'
            if from_state == 0:
                raise ValueError('file command out of order: ' + cmd_str)
            else:
                chan_ids = [int(c) for c in cmd_spec[1:]]
                assert all([0 <= c and c <= 64] for c in chan_ids)
                curr_dict['channels'] = chan_ids

        # handle baselines
        if cmd in ['baseline', 'nobaseline']:
            state_key = 'baseline'
            if from_state == 0:
                raise ValueError('file command out of order: ' + cmd_str)
            else:
                curr_dict['baseline_s'] = cmd_str

        # measurements
        if cmd in merp_catalog:
            state_key = 'measure'
            if from_state == 0:
                raise ValueError('file command out of order: ' + cmd_str)
            elif from_state in [1, 2]:
                # first measure this file block
                curr_dict['measures'] = [cmd_str]
            elif from_state == 3:
                curr_dict['measures'].append(cmd_str)

        # transition
        from_state = state_table[state_key][from_state]

    # push the work in progress on the way out 
    cmd_list.append(curr_dict)
    return(cmd_list)

def run_merp(mcf,debug=False):
    '''wrapper parses command file mcf, runs one test at a time via merp - < .tmp

    Parameters
    ----------
    mcf : string
        path to merp command file
    debug : bool
        if true reports internal command dict before running merp

    Returns
    -------
    measurements : list of dict
        each dict is the parsed long form merp output of one test

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

    '''
    
    measurements = [] # results
    all_tests = []  # minimal merp commands to run one test

    # fetch the merp command file
    merp_cmds_list = parse_merpfile(mcf)

    # optionally report
    if debug:
        print('merpfile ', mcf)
        pp.pprint(merp_cmds_list)

    # unpack the wildcards, if any, into individual commands
    test_params = ['measure', 'bin', 'chanspec', 'filespec']

    for merp_cmds in merp_cmds_list:
        for test_str in merp_cmds['measures']:
            # test format 
            # name bin filespec chanspec arg0 ... argN
            test = test_str.split()
            test_specs = dict()
            for i,k in enumerate(test_params):
                test_specs[k] = test[i]

            test_specs = dict([*zip(test_params, test[slice(0,len(test_params))])])

            # handle the arguments
            test_specs['argspec'] = test[len(test_params):]

            # expand file wild card if any
            if test_specs['filespec'] == '*':
                test_specs['filespec'] = merp_cmds['files']
            else:
                test_specs['filespec'] = [ test_specs['filespec'] ]

            # expand channel wildcard if any 
            if test_specs['chanspec'] == '$':
                test_specs['chanspec'] = merp_cmds['channels']
            else:
                test_specs['chanspec'] = list(test_specs['chanspec'])

            for chan in test_specs['chanspec']:
                for erpfile in test_specs['filespec']:

                    # build the file, baseline, and optional filter lines
                    this_file_lines = 'file {0}\n'.format(erpfile)

                    if ('baseline_s' in merp_cmds.keys() and 
                        merp_cmds['baseline_s'] is not 'NA'):
                        this_file_lines += '{0}\n'.format(merp_cmds['baseline_s'])

                    # set the measurement and params
                    this_test_spec = ' '.join([
                        test_specs['measure'], 
                        str(test_specs['bin']),
                        str(chan),
                        erpfile, 
                        *test_specs['argspec']])

                    # update the list of measures
                    this_file_lines += '{0}\n'.format(this_test_spec)
                    all_tests.append(this_file_lines)

    # run merp
    for test in all_tests:
        with open('.tmp', 'w') as f:
            f.write(test)

        file_proc = subprocess.Popen(['cat', '.tmp'], stdout=subprocess.PIPE)
        merp_proc = subprocess.Popen(['merp', '-'], stdin = file_proc.stdout, 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
        stdout, stderr = merp_proc.communicate()

        # catch merp hard errors with no data
        if re.match('^$',stdout.decode('utf-8')):
            msg = 'No merp output: {0}'.format(stderr.decode('utf-8'))
            msg += 'merpfile: {0}: '.format(mcf)
            msg += pp.pformat(test)
            raise RuntimeError(msg)

        measurement = parse_long_merp_output(stdout, stderr)

        # snapshot MD5 of file measured ... 
        with open(measurement['erpfile_s'], 'rb') as f:
            m = hashlib.md5()
            m.update(f.read())
        measurement.update({'erp_md5_s': m.hexdigest()})

        # add extra metadata here ... baseline
        for transform in ['baseline_s']:
            if transform in merp_cmds.keys():
                measurement.update({transform:  merp_cmds[transform]})

        measurement.update({'merpfile_s': mcf})

        measurements.append(measurement)
    return(measurements)


def parse_long_merp_output(data_bytes, err_bytes):
    '''parse long form merp output bytestring into a sensible dict 

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

    '''

    # tabs aren't expected but strip in case
    data = data_bytes.decode('utf-8').strip().replace('\t',' ')
    err = err_bytes.decode('utf-8')

    # if there is an error, first line is diagnostic
    err_match = re.match(r'(?P<error>^.*)\n', err)
    if err_match is not None:
        # squeeze extra whitespace 
        err = re.sub('\s+', ' ', err_match.groupdict()['error'])

    # Define one regex pattern per output line for
    # readibility/debugging

    # line 1 work around double label merp bug
    patt1 = ('^Channel\s+'
             '(?P<chan_desc_s>.{4})(?:.{4})*\s+Sum of\s+'
             '(?P<epochs_d>\S+)')

    # line 2 fixed length fields until the last. 
    patt2 = ('^.+\n'
             '(?P<subject_s>.{41})'
             '(?P<binfo_s>.{40})'
             '(?P<condition_s>.{41})'
             '(?P<expt_s>.{40})'
             '(?P<meas_specs_s>.*)'
             '[\\\\n]*' )

    # line 3 may not exist, e.g., on bad baseline error
    patt3 = ('.+\n.+\n'
             '(?P<meas_desc_s>.+?)'
             '(?P<value_f>[\.\d]+)\s'
             '(?P<units_s>\S+$)')

    # scrape column names from the patterns and precompile
    col_names, re_specs = [], []
    for patt in [patt1, patt2, patt3]:
        names = re.findall(r'\\?P<(.+?)>', patt)
        col_names += names
        re_specs.append( (names, re.compile(patt),) )


    # init output dict to NA
    row_dict = dict([ (col,'NA') for col in col_names ] )

    # First pass parse, override default 'NA' only on match
    for names, regex  in re_specs:
        matches = None
        matches = regex.match(data)
        if matches is not None:
            row_dict.update(matches.groupdict())

    # parse the 40 char bin number and description chunk
    bin_patt = ('^\s*bin\s+'
                '(?P<bin_d>\d+)\s+'
                '(?P<bin_desc_s>.*)')
    bin_info = re.match(bin_patt, row_dict['binfo_s']).groupdict()
    assert len(bin_info) == 2

    # parse the variable length meas_specs string
    meas_regex = re.compile('^'
                            '(?P<meas_label_s>\w+)\s+'
                            '(?P<bin2_d>\d+)\s+'
                            '(?P<chan_d>\d+)\s+'
                            '(?P<erpfile_s>\S+)\s+'
                            '(?P<win_start_f>\d+)\s+'
                            '(?P<win_stop_f>\d+)\s*'
                            '(?P<meas_args_s>.*)' )

    meas_specs = meas_regex.match(row_dict['meas_specs_s']).groupdict()
    assert len(meas_specs) == 7

    # add the new items
    kvs = [(k,v) for d in [row_dict, bin_info, meas_specs] 
           for k,v in d.items() ]
    for k,v in kvs:
        row_dict[k] = v.strip()

    # sanity checks ... 
    assert row_dict['bin_d'] == row_dict['bin2_d']

    # drop the redundant bin and parsed chunks
    del(row_dict['bin2_d'])
    del(row_dict['binfo_s'])
    del(row_dict['meas_specs_s'])

    # handle missing data
    if re.match('.+',err):
        row_dict['value_f'] = 'NA'
        row_dict['merp_error_s'] = err
    else:
        row_dict['merp_error_s'] = 'NA'

    # check measured value is convertible to numeric
    if row_dict['value_f'] != 'NA':
        float(row_dict['value_f'])

    return(row_dict)

def format_output(results, format='tsv', out_keys=None, tag_file=None):
    '''dump merp output to stdout in specified format

    Parameters
    ----------
    results : list of dict
        as returned by merp2tbl.run_merp()
    format : str ('tsv'), 'yaml' 
        specifies tab-separated rows x columns or yaml doc output
    out_keys : list of str
        whitelist of column names to report
    tag_file : str (None)
        path to YAML file with additional column:values 

    Notes
    -----

    '''


    # helper to convert the merp string output to python scalar types
    def spec2dtype(key_fmt,val_str):
        ''' converts val_str to data type according to _fmt, returns key, val 2-ple '''

        spec_map = dict(s=str, f=float, d=int) # map _fmt character to python data type

        # parse key_fmt
        key_spec = re.match('^(?P<key>.*)_(?P<spec>[fds])$', key_fmt)
        assert key_spec.groupdict()['spec'] in spec_map.keys()

        key = key_spec.groupdict()['key'] # == key_fmt stripped of '_fmt'

        # strings including NA don't need conversion
        if key_spec.groupdict()['spec'] == 's' or val_str == 'NA':
            val = val_str
        else: 
            # coerce string to float or int
            val = spec_map[key_spec.groupdict()['spec']](val_str)
        return key, val

    # set the output data types 
    results = [dict([spec2dtype(k,v) for k,v in r.items() ]) for r in results] 


    # set the external data data if any 
    if tag_file is not None:
        tags = load_tagfile(tag_file)

        # update results with the tags ... we could prescreen
        # more quickly but this allows diagnostic output on fail
        for k,v in tags.items():
            for i,r in enumerate(results):
                if type(v) in [str, int, float]:
                    r.update({k:v})
                elif type(v) is list and len(v) == 1:
                    r.update({k:v[0]}) # same tag all measurements
                elif type(v) is list and len(v) == len(results):
                    r.update({k:v[i]}) # ith tag -> ith measurement
                else:
                    msg = 'bad tag in {0} ... {1}: {2}\n'.format(tag_file, k, v)
                    msg += ('value must be a single scalar value or '
                            'list of exactly as many values as measurements')
                    raise ValueError(msg)

    assert all ( r.keys() == results[0].keys() for r in results)

    # handle the output column filter 
    if out_keys is None:
        out_keys = sorted(results[0].keys())

    results_out = []
    for r in results:
        ro = dict()
        for k,v in r.items():
            if k in out_keys:
                ro.update({k:v})
        results_out.append(ro)

    # switch for the output type and dump
    if format is None:
        format = 'tsv'
    assert format in ['tsv', 'yaml']

    if format == 'tsv':
        # tab separate with header in out_key order
        header = '\t'.join(out_keys) + '\n'
        data = '\n'.join(['\t'.join([str(r[c]) for c in out_keys]) 
                          for r in results_out])
        output = header + data

    if format == 'yaml':
        output = '# generated by merp2tbl\n'
        output += yaml.dump(results_out, explicit_start=True, 
                           default_flow_style=False,
                           canonical=False)

    print(output)


if __name__ == '__main__':
    import argparse  # successor to optparse

    # set up parser
    parser = argparse.ArgumentParser(
        description='convert verbose merp output to standard data interchange formats') 

    # names 
    parser.add_argument("mcf", metavar="mcf", type=str, help="merp command file")

    # collect optional column names to subset
    parser.add_argument("-columns", type=str, nargs="+",
                        dest="columns",
                        help="names of columns to select for the output")
    
    # output format
    parser.add_argument("-format", type=str, metavar='format',
                        dest="format", 
                        help=("'tsv' for tab-separated rows x columns or "
                              "'yaml' for YAML document output"))

    # supplementary data tags
    parser.add_argument("-tagf", type=str,
                        metavar='tagf',
                        dest="tagf",
                        help=("tagf.yml YAML file with additional "
                              "column data to merge with the output"))

    # supplementary data tags
    parser.add_argument("-debug", 
                        action="store_true",
                        dest="debug",
                        help=("-debug mode shows command file parse before running merp"))

    args_dict = vars(parser.parse_args()) # fetch from sys.argv

    result = run_merp(args_dict['mcf'], args_dict['debug'])
    format_output(result,
                  format=args_dict['format'], 
                  out_keys = args_dict['columns'],
                  tag_file = args_dict['tagf'])

