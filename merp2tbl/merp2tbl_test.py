import os
import os.path
import merp2tbl 
import pprint as pp
import pdb

# jump down to testdata to run merp
os.chdir(os.path.join(os.getcwd(), 'testdata'))

good_mcfs = ['test_mixed.mcf', 'test_nobaseline.mcf', 'test_filterspec.mcf']
good_mcfs = ['test_filterspec.mcf']
good_mcfs = ['test_baseline.mcf']

def test_load_merp_file():

    # go tests
    for mcf in good_mcfs:
        merp_cmds = merp2tbl.parse_merp_file(mcf)

    # no go tests 

def test_run_merp():
    for mcf in good_mcfs:
        result = merp2tbl.run_merp(mcf)
        merp2tbl.format_output(result)
        merp2tbl.format_output(result, format='yaml')
        

