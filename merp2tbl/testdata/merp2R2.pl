#!/usr/bin/perl
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
# T. Urbach 04/09/18 patched to handle measurement errors
############################################################

# use this value for measurement errors
$missing_data = "NA";

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
    system(sprintf("rm -f %s", $datf));
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



$mydat = qx(merp test_mixed.mcf 2>&1);
print($mydat);
exit(0);

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

# print(@merpOutDat);


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

    # lookahead for error lines and set missing data
    $meas_error = 0; # hope for the best ...
    if ($l < $nOutDatLines-1){
	$nextLine = @merpOutDat[$l+1]; 
    } else {
	$nextLine = ''
    }
       
    if ( $nextLine =~ /[Ee][Rr][Rr][Oo][Rr]/){
	$errLine =~ s/(^.+)([Ee][Rr][Rr][Oo][Rr])/\2/;
	printf("warning measurement error: data value is %s ... %s\n", $missing_data, $errLine);
	$meas_error = 1; 
	# die();
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

	printf("MEAS ERROR HERE: %d\n", $meas_error);


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

	    # hack in missing data
	    if ($meas_error == 1){
		$currMeasPKLData = $missing_data;
		$currMeasPKAData = $missing_data;
	    }
		
	} else {
        
	    ## ALL OTHER NON-PKLA MEASURES ... SIMPLY ASSIGN THE VALUES 
	    $currMeasDesc = join(" ", @currCharVec[0..($currCharVecLen-3)]);
	    $currData     = @currCharVec[$currCharVecLen-2];
	    $currMeasUnit = @currCharVec[$currCharVecLen-1];

	    if ($meas_error == 1){
		die('data error');
		$currData = $missing_data;
	    }
	    $currData = $meas_error;
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
