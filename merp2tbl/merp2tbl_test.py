import os
import os.path
import glob
import pprint as pp
import pytest
import pdb

import merp2tbl 

# jump down to testdata to run merp
os.chdir(os.path.join(os.getcwd(), 'testdata'))

good_mcfs = glob.glob('*good*.mcf')
softerror_mcfs = glob.glob('*softerror*.mcf')
harderror_mcfs = glob.glob('*harderror*.mcf')

def test_minimal_good():
    mcf = 'test_minimal_good.mcf'
    merp_cmds = merp2tbl.parse_merpfile(mcf)
    result = merp2tbl.run_merp(mcf)

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

def test_run_merp():
    for mcf in good_mcfs + softerror_mcfs:
        result = merp2tbl.run_merp(mcf)

        for format in ['tsv', 'yaml']:
            print('# ' + '-' * 40)
            print('# mcf: {0} format: {1}'.format(mcf, format))
            print('# ' + '-' * 40)
            merp2tbl.format_output(result, format=format)
            print()
        

def test_select_columns():
    for mcf in good_mcfs + softerror_mcfs:
        result = merp2tbl.run_merp(mcf)

        n_cols = len(result[0].keys())
        col_names = [k for k in result[0].keys()]
        assert n_cols >= 2

        # select even and odd colums = 2 subsets that cover all columns
        for subset in [0,1]:
            cols = [col_names[idx] for idx in range(subset, n_cols, 2)]
            for format in ['tsv', 'yaml']:
                print('# ' + '-' * 40)
                print('# mcf: {0} format: {1}'.format(mcf, format))
                print('# ' + '-' * 40)
                merp2tbl.format_output(result, format=format, out_keys = cols)
                print()
        


