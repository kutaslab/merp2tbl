import subprocess
import re
import pdb
import os.path
import pprint as pp

# pkla # exclude, this dumps 2 lines of data and is buggy wrt to soft errors

transforms = ['filter', 'baseline', 'nobaseline']
merp_catalog = [ 'pkl', 'centroid', 'pka', 'fpl' 'fplf', 'fpa',
                 'fpaf', 'lpkl', 'lpka', 'lfpl', 'fal', 'faa', 'ppa', 'npppa', 'pnppa',
                 'lnpppa', 'lpnppa', 'abblat', 'bonslat', 'pxonslat', 'nxonslat',
                 'rms', 'meana', 'mnarndpk', 'slope', 'pks' ]
    

def parse_merp_file(merp_f):
    ''' parse merp command file in order to unwind the file and channel wildcards


    Parameters
    ----------
    merp_f : str
        name of a merp file

    Notes
    ------

    * explicit baseline spec is *MANDATORY*

    * filter spec is *OPTIONAL

    * merp commands should look like this: 

    ```
    file ...
    file ...

    channels ...

    baseline start_n stop_n

    test ...
    test ...
    test ...
    ```

    '''
    # with open(merp_f, 'r') as f:
    #    merp_cmds = f.read()
    f = open(merp_f, 'r')
    merp_cmds = f.read()
    f.close()
	
    merp_cmds = re.sub('\n+','\n', merp_cmds)
    merp_cmds = merp_cmds.split('\n')

    # cleanup whitespace, empty lines 
    merp_cmds = [re.sub('\s+', ' ', m) for m in merp_cmds 
                 if re.match(r'(^$)|(^\s*#)',m) is None]

    # cleanup trailing comments
    merp_cmds = [re.sub('\s+#.+$', '', m).strip() for m in merp_cmds]

    cmd_dict = dict(files=None, 
                    channels=None, baseline=None, filter=None, 
                    tests=None)

    # 0 = start,
    # 1 = loading files,
    # 2 = loading chans, baseline, filter specs order doesn't matter
    # 3 = loading tests

    parse_phase = 0 # start
    for cmd in merp_cmds:
        cmd_spec = cmd.split(' ')
        if cmd_spec[0] not in ['file', 'channels'] + transforms + merp_catalog:
            raise ValueError('unknown merp command: ', cmd)

        # handle files ... must be first items
        if cmd_spec[0] == 'file':
            if not parse_phase <= 1:
                raise ValueError('file command out of order: ' + cmd)

            parse_phase = 1
            assert len(cmd_spec) == 2
            if cmd_dict['files'] is None:
                cmd_dict['files'] = [ cmd_spec[1] ]
            else:
                cmd_dict['files'].append(cmd_spec[1])

        # handle chans and transforms
        if cmd_spec[0] in ['channels'] + transforms:
            if parse_phase not in [1,2]:
                raise ValueError('command out of order: ' + cmd)

            parse_phase = 2
            if cmd_spec[0] == 'channels':
                chan_ids = [int(c) for c in cmd_spec[1:]]
                assert all([0 <= c and c <= 64] for c in chan_ids)
                cmd_dict['channels'] = chan_ids

            elif cmd_spec[0] == 'baseline':
                cmd_dict['baseline'] = cmd_spec[1:]

            elif cmd_spec[0] == 'nobaseline':
                cmd_dict['baseline'] = [None, None]

            elif cmd_spec[0] == 'filter':
                cmd_dict['filter'] = cmd_spec[1:]

            else:
                raise ValueError('uh oh ... ' + cmd_spec)

        # handle tests
        if cmd_spec[0] in merp_catalog:
            parse_phase = 3 # loading tests

            if cmd_dict['baseline'] is None:
                raise ValueError('merp file MUST specify baseline or nobaseline')

            if cmd_dict['tests'] is None:
                cmd_dict['tests'] = [cmd]
            else:
                cmd_dict['tests'].append(cmd)

    return(cmd_dict)

def run_merp(mcf, args=None):

    # fetch the merp command file
    merp_cmds = parse_merp_file(mcf)

    
    # unpack the wildcards, if any, into individual commands
    test_params = ['measure', 'bin', 'filespec', 'chanspec']
    all_tests = []
    for test_str in merp_cmds['tests']:
        # test format 
        # name bin filespec chanspec arg0 ... argN
        test = test_str.split()
        test_specs = dict([*zip(test_params, test[slice(0,len(test_params))])])

        # handle the arguments
        test_specs['argspec'] = test[len(test_params):]

        # expand file wild card if any
        if test_specs['filespec'] == '$':
            test_specs['filespec'] = merp_cmds['files']
        else:
            test_specs['filespec'] = list(test_specs['filespec'])

        # expand channel wildcard if any 
        if test_specs['chanspec'] == '*':
            test_specs['chanspec'] = merp_cmds['channels']
        else:
            test_specs['chanspec'] = list(test_specs['chanspec'])

        for chan in test_specs['chanspec']:
            for erpfile in test_specs['filespec']:
                this_file_line = 'file '+ erpfile
                this_test_spec = ' '.join([
                    test_specs['measure'], 
                    str(test_specs['bin']),
                    str(chan),
                    erpfile, 
                    *test_specs['argspec']])
                all_tests.append('{0}\n{1}\n'.format(this_file_line,
                                                   this_test_spec))
    # run merp
    for test in all_tests:
        with open('.tmp', 'w') as f:
            f.write(test)
        file_proc = subprocess.Popen(['cat', '.tmp'], stdout=subprocess.PIPE)
        merp_proc = subprocess.Popen(['merp', '-'], stdin = file_proc.stdout, 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
        stdout, stderr = merp_proc.communicate()
        table_row = parse_long_merp_output(stdout, stderr)
        for transform in ['baseline', 'filter']:
            table_row.update({transform:  merp_cmds[transform]})
        table_row.update({'merp_f': mcf})
        pp.pprint(table_row)

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

    * merp long form output has a bug that farts out an extra 4 char
      channel label on the first line. The reg exp takes the first four
      characters of the channel label field, dropping the last 4, if
      any. So MiPa -> MiPa and MiCeMiPa -> MiCe


    '''

    # clean up the long form out returned by merp, tabs aren't
    # expected but strip in case
    data = data_bytes.decode('utf-8').strip().replace('\t',' ')
    err = re.sub(r'[\n\t ]+', ' ', err_bytes.decode('utf-8')).strip()

    # catch merp hard errors
    if re.match('^$',data):
        msg = 'No merp output: {0}'.format(err)
        raise RuntimeError(msg)

    # collect 2-ples of (key, value) to build the table row columns
    row_dict = dict()

    # b.c. of merp channel label bug we grab the last four chars of
    # the channel description
    re1 = re.compile('^Channel\s+(?P<chan>.{4})(?:.{4})*\s+Sum of\s+(?P<n>\S+)') # strip double chan bug
    re2 = re.compile(('^.+\n(?P<subject>.{41})(?P<bin>.{40})'
                      '(?P<condition>.{41})(?P<expt>.{40})(?P<measure>.+)\n'))
    re3 = re.compile(r'.+\n.+\n(?P<test>.+?)(?P<data>[\.\d]+)\s(?P<units>\S+$)')

    for regex, matchlen in [ (re1,2), (re2,5), (re3,3) ]:
        line = None
        line = regex.match(data)
        assert line is not None
        assert len(line.groupdict()) == matchlen
        row_dict.update(line.groupdict())

    for k,v in row_dict.items():
        row_dict[k] = v.strip()

    # works float, ints and fails on unconvertable str
    assert type(float(row_dict['data'])) is float

    # handle missing data
    if re.match('.+',err):
        row_dict['data'] = 'NA'
        row_dict['err'] = 1
    else:
        row_dict['err'] = 0
    return(row_dict)

# ------------------------------------------------------------
# !/usr/bin/perl
#
# Usage: merp2R.pl mymerpfile.mcf (-q) mymerpargs
#
# This takes a merp file and optional merp command line arguments as
# input, runs it to generate verbose merp output and then convert it
# to an R style rows = observations, columns = factors format.
#
# The result is dumped to file with merpfile.R.dat name
#
# STDERR is captured when merp is run and the script aborts if any merp
# error ... hard or soft ... is encountered. 
# 
#
#
# T. Urbach 08/25/08
############################################################

perl_version = \
'''
# NAB FILE NAME
unless ($merpf = @ARGV[0]){
    die("ERROR: Specify merp file ");
};

unless (open(MF, $merpf)){
    die("Cannot open file $merpf");
}
close(MF);

# BUILD MERP ARGUMENT STRING ...
$mymerpargs = join(" ", @ARGV[1..(@ARGV)]);

$datf = $merpf.".R.dat";
unless (open(DF, '>', $datf)){
    # IF THE OPEN FAILS, CLOBBER THE OLD VERSION SO YOU DON'T THINK YOU ARE LOOKING
    # AT A FRESH RUN.
    system(sprintf("rm %s", $datf));
    die("Cannot open output datafile $datf");
}

## ##########################################################
## SET COLUMN NAMES FOR THE 17 (CURRENTLY IMPLEMENTED) DATA
## FIELDS.
## ########################################################
@DataCols = 
    (
     "DatFilePrefix",
     "BinNum",
     "BinDesc",
     "ChanNum",
     "ChanDesc",
     "MeasFunc",
     "MeasWindow",
     "Data",
     "MeasUnit",
     "ExptDesc",
     "CondDesc",
     "Sums",
     "MeasDesc",
     "ExtraArgs",
     "DatFName",
     "SubDesc",
     "CmdDesc"
     );

############################################################
# LOAD THE MERP OUTPUT 
############################################################

## THE 2>&1 IS SHELL VOODOO THAT PUMPS STDERR INTO THE OUTPUT 
## STREAM

$sysCmd = sprintf("merp %s %s 2>&1 | ", $mymerpargs, $merpf);
printf("Running merp %s ...", $merpf);
open (MERPOUT, $sysCmd);
@merpOutDat = <MERPOUT>;
$nOutDatLines =  (@merpOutDat);
$currDataRowN = 1;
printf("done\n");

############################################################
# DUMP R TABLE HEADER
############################################################
printf(DF "%s\n", join(",", @DataCols)); 

$nDat = 0;
printf("Writing %s\n", $datf);
for ($l==0;$l<$nOutDatLines;$l++){

    # NAB THE CURRENT LINE 
    $currLine = "";
    $currLine = @merpOutDat[$l];
    $currLine =~ s/\n$//;

    # BAIL OUT ON MERP ERROR 
    if ( $currLine =~ /[Ee][Rr][Rr][Oo][Rr]/){
	$currLine =~ s/(^.+)([Ee][Rr][Rr][Oo][Rr])/\2/;

	printf("############################################################\n");
	printf("merp2R.pl FATAL ERROR ... merp reports:\n\n\t%s\n\n", $currLine);
	printf("############################################################\n");
	system(sprintf("rm %s", $datf));
	die();
    }

    ## TRIGGER PROCESSING ON FIRST WORD CHANNEL
    if ($currLine =~ /Channel/ ){
	
	if (($nDat++ %1000) == 0){
	    printf("Processing line %6d of %6d\n", $l, $nOutDatLines)
	}

	## INITIALIZE ...
	$L1 <- "";
	$L2 <- "";
	$L3 <- "";

	## ##########################################################
	## 1. PROCESS L1: CHANNEL DESC AND SUMS LINE
	## ##########################################################

	## NAB NEXT THREE SUCCESSIVE DATA LINES OF OUTPUT AND PARSE/SPLIT
	$L1 = $currLine;
	$L2 = @merpOutDat[$l+1];
	$L3 = @merpOutDat[$l+2];

	## STRIP COMMAS SO WE CAN OUTPUT CSV DATA
	$L1 =~ s/,/ /g;
	$L2 =~ s/,/ /g;
	$L3 =~ s/,/ /g;

	## printf("L1: %s\n", $L1);
	## printf("L2: %s\n", $L2);
	## printf("L3: %s\n", $L3);

	## NAB CHANNEL DESCRIPTION AND BIN SUMS FROM L1
	$L1 =~ s/Channel//;  # Knock out "Channel" string
	$L1 =~ s/Sum of//; # Knock out "Sum of" string
	$L1 =~ s/[ ]+/ /g;

	@L1vec = ();
	@L1vec = split(" ", $L1);

	$currChanDesc = "";
	$currSums     = "";
	$currChanDesc = @L1vec[0];
	$currSums     = @L1vec[1];

#	$currChanDesc =~ s/ //g;

	## ##########################################################
	## 2. PROCESS L2: DESCRIPTIONS LINE AS ABOVE
	## ##########################################################
	##      SUB DESC        1: 40
	##      BIN DESC       41: 80
	##      COND DESC      81:120
	##      EXPT DESC     121:160
	##      MERP COMMAND  161:LAST
	## ##########################################################

	## ##########################################################
	## BREAK UP L2 INTO 4 each 40 CHAR CHUNKS PLUS WHATEVER IS LEFT FOR THE
	## MERP MEASURE STRING 
	## ##########################################################

	## INIALIZE PAIR LIST OF DESCRIPTIVE INFO W/ THE 40 CHAR CHUNKS OF L2
	$currSubDesc  = substr($L2,   1,  40);
	$currBinDesc  = substr($L2,  41,  40);
	$currCondDesc = substr($L2,  81,  40);
	$currExptDesc = substr($L2, 121,  40);
	$currCmdDesc  = substr($L2, 161,length($L2)-160);

	## TIDY UP LEADING, TRAILING, AND DOUBLE WHITESPACE IN THE STRINGS ...
        $currSubDesc =~ s/^[^[:graph:]]+|[^[:graph:]]+$"//;
        $currSubDesc =~ s/[^[:graph:]]{2,}/ /;

        $currBinDesc =~ s/^[^[:graph:]]+|[^[:graph:]]+$"//;
        $currBinDesc =~ s/[^[:graph:]]{2,}/ /;

        $currCondDesc =~ s/^[^[:graph:]]+|[^[:graph:]]+$"//;
        $currCondDesc =~ s/[^[:graph:]]{2,}/ /;

        $currExptDesc =~ s/^[^[:graph:]]+|[^[:graph:]]+$"//;
        $currExptDesc =~ s/[^[:graph:]]{2,}/ /;

	$currCmdDesc =~ s/\n$//;


	## ##########################################################
	## 3. PROCESS L3: DATA MEASURES IN SIMILAR FASHION TO GET
	##    THE ACTUAL NUMBER ...
	##
	## SIMPLE EXCEPT FOR THE pkla MEASURE WHICH DUMPS TWO
	## NUMBERS AND NEEDS A DIFFERENT PARSE ...
	## ##########################################################

	## INITIALIZE WITH (SINGLE) WHITESPACE SEPARATED STRING 
	$currStr = $L3;
	$currStr =~ s/[^[:graph:]]{2,}/ /g;

	## SPLIT INTO CHARACTER VECTOR OF WORDS, SHOULD LOOK LIKE THIS ...
	## 
	## [1] "mean"      "amplitude" "around"    "peak"      "9.54"      "uVolts"
	##
	@currCharVec = ();
	@currCharVec = split(" ", $currStr);
	$currCharVecLen = (@currCharVec);

	## ##########################################################
	## TWO CASES ...
	##
	## 1. pkla
	##    . LAST ITEM IS MAGNITUDE UNITS
	##    . 2nd TO LAST IS PEAK MAGNITUDE DATA
	##    . 3rd TO LAST IS LATENCY UNITS
	##    . 4th TO LAST IS PEAK LATENCY DATA
	##    . ALL ELSE IS VERBOSE MEASURE DESCRIPTION
	##
	## 2. NON-pkla MEASURES
	##    . LAST ITEM IS UNITS
	##    . 2nd-TO LAST IS NUMERICAL DATA
	##    . ALL ELSE PRECEDING IS VERBOSE MEASURE DESCRIPTION
	##
	##
	## ##########################################################

	if ((@currCharVec)<3){
	    die(sprintf("FATAL ERROR PARSING DATA MEASURE LINE L3: %s ... NOT ENOUGH FIELDS",
			$currStr));
	}

	## INITIALIZE ...
	@currMeasDesc = ();

	## FOR SPECIAL CASE PKLA MEASURES
	$currMeasPKAData = "";
	$currMeasPKAUnit = "";
	$currMeasPKLData = "";
	$currMeasPKLUnit = "";

	## FOR NON-PKLA MEASURES
	$currData        = "";
	$currMeasUnit    = "";
	
	## SWITCH TO HANDLE PKLA SPECIAL CASE ...
	if ($currCmdDesc =~ /pkla/){

	    ## ASSIGN THE VALUES ...
	    $currMeasDesc    = join(" ", @currCharVec[0..($currCharVecLen-5)]);
	    $currMeasPKLData = @currCharVec[$currCharVecLen-4];
	    $currMeasPKLUnit = @currCharVec[$currCharVecLen-3];
	    $currMeasPKAData = @currCharVec[$currCharVecLen-2];
	    $currMeasPKAUnit = @currCharVec[$currCharVecLen-1];

	} else {
        
	    ## ALL OTHER NON-PKLA MEASURES ... SIMPLY ASSIGN THE VALUES 
	    $currMeasDesc = join(" ", @currCharVec[0..($currCharVecLen-3)]);
	    $currData     = @currCharVec[$currCharVecLen-2];
	    $currMeasUnit = @currCharVec[$currCharVecLen-1];
	}
	
 	## ##########################################################
 	## (FINALLY) DONE PARSING L1,L2,L3 ... SO EXTRACT THE EXTRA
 	## INFO ... 
 	## ##########################################################

 	## SPLIT UP THE COMMAND LINE TO GET THE FILE, MEASURE LABEL ETC, E.G. 
 	##      mFunc BinNum ChanNum FName wStart wStop Args=...
 	##      fpl 127 26 ../avg/rtm03y.nrf 0 1000 + .1
      
 	@currCmdStrVec = ();
	@currCmdStrVec = split(" ",$currCmdDesc);

	## ##########################################################
	## MODICUM OF ERROR CHECKING ... 
	## ##########################################################
#       currMerpFuncInfo <- NULL
#       currMerpFuncInfo <- cds.df[which(cds.df$mFunc==currCmdStrVec[1]),]

       ## FIRST, PUTATIVE MERP FUNCTION BETTER BE AMONG KNOWN FUNCTIONS DEFINED ABOVE
#       if (nrow(currMerpFuncInfo)==0){
#         stop(sprintf("FATAL ERROR PARSING MERP COMMAND STRING IN OUTPUT ... MERP FUNC %s NOT RECOGNIZED",
#                      currCmdStrVec[1]))
#       }

#       ## SECOND, THE NUMBER OF ARGUMENTS FOR SPECIFIED FUNC BETTER MATCH ...
#       if (currMerpFuncInfo$mArgs != length(currCmdStrVec)){
#         print(currMerpFuncInfo)
#         print(currCmdStrVec)
#         errMsg<-NULL
#         errMsg<-sprintf("FATAL ERROR PARSING MERP COMMAND STRING IN OUTPUT ...\nMERP FUNC %s WANTS %s ARGS, PARSE OF\n\t%s\nRETURNED %d",
#                         currCmdStrVec[1],
#                         currMerpFuncInfo$mArgs,
#                         descStrs$currCmdDesc,
#                         length(currCmdStrVec)
#                         )
#         stop(errMsg)
#     }


	## INITIALIZE ...
	$currMeasFunc  = "";
	$currBinNum    = "";
	$currChanNum   = "";
	$currDatFName  = "";
	$currWStart    = "";
	$currWStop     = "";
	$currExtraArgs = "";

	$currMeasFunc  = @currCmdStrVec[0];
	$currBinNum    = sprintf("B%s", @currCmdStrVec[1]);
	$currChanNum   = sprintf("C%s", @currCmdStrVec[2]);
	$currDatFName  = @currCmdStrVec[3];
	$currWStart    = @currCmdStrVec[4];
	$currWStop     = @currCmdStrVec[5];

	## NAB EXTRA ARGS IF ANY ... ELSE LEAVE NA
	$tmpArgStr = "";
	$tmpArgStr = join(" ", @currCmdStrVec[6..(@currCmdStrVec)-1]);
	if (length($tmpArgStr)>0){
	    $currExtraArgs = $tmpArgStr;
	} else {
	    $currExtraArgs = "NA";
	}
	    

	## BUILD MEASUREMENT WINDOW LABEL
	$currMeasWindow = "";
	$currMeasWindow = sprintf("W%s_%s", $currWStart,$currWStop);

	## TRY TO EXTRACT PREFIX FROM THE FILE NAME BY REMOVING
	## PATH, LEAVING ONLY THE FILENAME AND THEN DROP EVERYTHING
	## AFTER THE FIRST DOT ... WHEN DATA FILES HAVE SINGLE SUBJECT
	## DATA, THESE MAP ONTO SUBJECT FACTOR LEVELS.
	
	$currDatFilePrefix = "";
	$currDatFilePrefix = $currDatFName;
	$currDatFilePrefix =~ s/.*\///g;
	$currDatFilePrefix =~ s/\..*//g;

	## ##########################################################
	## BUILD THE ROW AND ADD TO MAIN DATAFRAME 
	## ##########################################################

	## INITIALIZE
	%currDatRow = ();

	## BUILD CURRENT DATA ROW ... 

	if ($currMeasFunc eq "pkla"){
	    ## DUMP LATENCY ROW 
	    printf(DF "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n",
		   $currDatFilePrefix, 
		   $currBinNum,        
		   $currBinDesc,       
		   $currChanNum,       
		   $currChanDesc,      
		   "pkl",               
		   $currMeasWindow,    
		   $currMeasPKLData,   
		   $currMeasPKLUnit,   
		   $currExptDesc,      
		   $currCondDesc,      
		   $currSums,          
		   $currMeasDesc,      
		   $currExtraArgs,     
		   $currDatFName,      
		   $currSubDesc,       
		   $currCmdDesc        
		   );


	    ## DUMP AMPLITUDE ROW 
	    printf(DF "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n",
		   $currDatFilePrefix,      
		   $currBinNum,        
		   $currBinDesc,       
		   $currChanNum,       
		   $currChanDesc,      
		   "pka",
		   $currMeasWindow,    
		   $currMeasPKAData,          
		   $currMeasPKAUnit,      
		   $currExptDesc,      
		   $currCondDesc,      
		   $currSums,          
		   $currMeasDesc,      
		   $currExtraArgs,     
		   $currDatFName,      
		   $currSubDesc,       
		   $currCmdDesc        
		   );


	} else {

#	    printf("%12s, %5s, %40s, %8s, %4s, %6s, %12s, %12s, %20s, %20s, %20s, %40s, %40s, %20s, %40s, %128s, %-128s\n",
	    printf(DF "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n",
		   $currDatFilePrefix,
		   $currBinNum,
		   $currBinDesc,
		   $currChanNum,
		   $currChanDesc,
		   $currMeasFunc,
		   $currMeasWindow,
		   $currData,
		   $currMeasUnit,
		   $currExptDesc,
		   $currCondDesc,
		   $currSums,
		   $currMeasDesc,
		   $currExtraArgs,
		   $currDatFName,
		   $currSubDesc,
		   $currCmdDesc        
		   );

	}

    }
}

# CLOSE OUT THE DATA FILE
close(DF);
exit(0);
'''
