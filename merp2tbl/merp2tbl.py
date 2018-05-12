'''
format long form merp text output as rows x columns or YAML document

based on merp2R.pl, T. Urbach 08/25/08
'''

import subprocess
import re
import pdb
import os.path
import yaml
import hashlib

import pprint as pp

# master list of merp measures except pkla which pkla which dumps
# 2 lines of data and is buggy wrt to soft errors

transforms = ['baseline', 'nobaseline']
merp_catalog = [
    'pkl', 'centroid', 'pka', 'fpl' 'fplf', 'fpa',
    'fpaf', 'lpkl', 'lpka', 'lfpl', 'fal', 'faa', 'ppa', 'npppa',
    'pnppa', 'lnpppa', 'lpnppa', 'abblat', 'bonslat', 'pxonslat',
    'nxonslat', 'rms', 'meana', 'mnarndpk', 'slope', 'pks'
]
    
def parse_merpfile(merpfile):
    '''parse merp command file

    Parameters
    ----------
    merpfile : str
        name of a merp file

    Notes
    ------

    * channels, baseline, and nobaseline specs are supported

    * filter command is not supported by design

    * some variant forms of merp command files are not supported

    Usage
    -----

    The merp file should look like this: 

    ```
    # at least one file is mandatory
    file ...
    file ...

    # channels is optional
    channels ...

    # baseline start stop or nobaseline is optional 
    baseline start_n stop_n

    # at least one test is mandatory
    test ...
    test ...
    test ...
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

    cmd_dict = dict(files='NA', channels='NA', baseline='NA', tests='NA')

    # 0 = start,
    # 1 = loading files,
    # 2 = loading chans, baseline, order doesn't matter
    # 3 = loading tests

    # whitelist commands we can handle
    implemented_cmds = ['file', 'channels'] + transforms + merp_catalog
    parse_phase = 0 # start
    for cmd in merp_cmds:
        cmd_spec = cmd.split(' ')
        if cmd_spec[0] not in implemented_cmds:
            msg = 'merpfile: {0} line: {1}\n'.format(merpfile,cmd)
            msg += pp.pformat('choose from: ' + ' '.join(implemented_cmds))
            raise NotImplementedError(msg)

        # handle files ... these must come first
        if cmd_spec[0] == 'file':
            if not parse_phase <= 1:
                raise ValueError('file command out of order: ' + cmd)

            parse_phase = 1
            assert len(cmd_spec) == 2
            if cmd_dict['files'] is 'NA':
                cmd_dict['files'] = [ cmd_spec[1] ]
            else:
                cmd_dict['files'].append(cmd_spec[1])

        # handle chans and/or baseline
        if cmd_spec[0] in ['channels'] + transforms:
            if parse_phase not in [1,2]:
                raise ValueError('command out of order: ' + cmd)

            parse_phase = 2
            if cmd_spec[0] == 'channels':
                chan_ids = [int(c) for c in cmd_spec[1:]]
                assert all([0 <= c and c <= 64] for c in chan_ids)
                cmd_dict['channels'] = chan_ids

            elif cmd_spec[0] == 'baseline':
                cmd_dict['baseline_s'] = cmd

            elif cmd_spec[0] == 'nobaseline':
                cmd_dict['baseline_s'] = cmd_spec[0]

            else:
                raise ValueError('uh oh ... ' + cmd_spec)

        # handle tests
        if cmd_spec[0] in merp_catalog:
            parse_phase = 3 # loading tests

            if cmd_dict['tests'] is 'NA':
                cmd_dict['tests'] = [cmd]
            else:
                cmd_dict['tests'].append(cmd)

    return(cmd_dict)

def format_output(results, format='tsv', out_keys=None):
    '''dump merp output to stdout in specified format

    Parameters
    ----------
    results : list of dict
        as returned by merp2tbl.run_merp()
    format : str ('tsv', 'yaml')
        specifies tab-separated rows x columns or yaml doc output
    out_keys : list of str
        whitelist of column names to report

    Notes
    -----

    '''
    # helper to convert the merp string output to python scalar types
    def spec2dtype(key_fmt,val_str):
        ''' converts val_str to data type according to _fmt, returns key, val 2-ple '''

        spec_map = dict(s=str, f=float, d=int) # map _fmt character to python data type

        # parse key_fmt
        key_spec = re.match('^(?P<key>.*)_(?P<spec>[fds])$', key_fmt)
        assert key_spec['spec'] in spec_map.keys()

        key = key_spec['key'] # == key_fmt stripped of '_fmt'

        # strings don't need conversion
        if key_spec['spec'] == 's':
            val = val_str
        else: 
            val = spec_map[key_spec['spec']](val_str) # coerce string to float or int
        return key, val

    assert format in ['tsv', 'yaml']

    # handle the output column filter 
    if out_keys is None:
        assert all ( r.keys() == results[0].keys() for r in results)
        out_keys = sorted(results[0].keys())

    out_results = [ dict([spec2dtype(k, r[k]) for k in r.keys() if k in out_keys]) 
                    for r in results] 

    if format == 'tsv':
        # tab separate with header 
        header = '\t'.join(out_keys) + '\n'
        data = '\n'.join([ '\t'.join([r[k] for k in out_results.keys()]) for r in out_results])
        data = '\n'.join(['\t'.join([str(v) for v in r.values()]) for r in out_results])
        output = header + data

    if format == 'yaml':
        output = '# generated by merp2tbl\n'
        output += yaml.dump(out_results, explicit_start=True, 
                           default_flow_style=False,
                           canonical=False)

    print()
    # pp.pprint(output)
    print(output)


def run_merp(mcf):
    '''wrapper parses command file mcf, runs one test at a time via merp - < .tmp


    Parameters
    ----------
    mcf : string
       path to merp command file

    Returns
    -------
    table_rows : list of dict
        each dict is the parsed long form merp output of one test

    Notes
    -----

    * merp commands with file or channel wildcards are expanded into
      individual tests and run through merp one at a time to capture
      stdout and stderr output for the specific test.

    * in the results dicts from the merp output all the values are
      strings and all the keys end in an underscore and printf-like
      data type specification character indicating the natural data
      type:

        _f = float    value : '10.7'
        _d = int      bin_d: '3'
        _s = str      chan_desc_s : 'MiPa'  

    '''
    
    table_rows = [] # results
    all_tests = []  # minimal merp commands to run one test

    # fetch the merp command file
    merp_cmds = parse_merpfile(mcf)

    # unpack the wildcards, if any, into individual commands
    test_params = ['measure', 'bin', 'chanspec', 'filespec']

    for test_str in merp_cmds['tests']:
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

                if 'baseline_s' in merp_cmds.keys():
                    this_file_lines += '{0}\n'.format(merp_cmds['baseline_s'])

                # set the measurement and params
                this_test_spec = ' '.join([
                    test_specs['measure'], 
                    str(test_specs['bin']),
                    str(chan),
                    erpfile, 
                    *test_specs['argspec']])

                # update the list of tests
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
            pdb.set_trace()
            msg = 'No merp output: {0}'.format(stderr.decode('utf-8'))
            msg += 'merpfile: {0}: '.format(mcf)
            msg += pp.pformat(test)
            raise RuntimeError(msg)

        table_row = parse_long_merp_output(stdout, stderr)

        # snapshot MD5 of file measured ... 
        with open(table_row['erpfile_s'], 'rb') as f:
            m = hashlib.md5()
            m.update(f.read())
        table_row.update({'erp_md5_s': m.hexdigest()})

        # add extra metadata here ... baseline
        for transform in ['baseline_s']:
            if transform in merp_cmds.keys():
                table_row.update({transform:  merp_cmds[transform]})

        table_row.update({'merpfile_s': mcf})

        table_rows.append(table_row)
    return(table_rows)


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
        err = re.sub('\s+', ' ', err_match['error'])

    # Define one regex pattern per output line for
    # readibility/debugging

    # line 1 work around double label merp bug
    patt1 = ('^Channel\s+'
             '(?P<chan_s>.{4})(?:.{4})*\s+Sum of\s+'
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
    meas_regex = re.compile( ('^'
                              '(?P<meas_label_s>\w+)\s+'
                              '(?P<bin2_d>\d+)\s+'
                              '(?P<chan_d>\d+)\s+'
                              '(?P<erpfile_s>\S+)\s+'
                              '(?P<win_start_f>\d+)\s+'
                              '(?P<win_stop_f>\d+)\s*'
                              '(?P<meas_args_s>.*)\s*' ))

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


