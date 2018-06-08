# How to ...

convert verbose merp output to standard data interchange formats 
## Example:

```bash
[astoermann@mkgpu1 Merp]$ merp2table
usage: merp2table [-h] [-columns COLUMNS [COLUMNS ...]] [-format format]
                  [-tagf tagf] [-debug]
                  mcf
merp2table: error: the following arguments are required: mcf

```
extra commands must be in the order above for merp2table to run

if you are only using one of the extra commands, it must go after the mcf argument or merp2table will not run

output is always organized alphabetically by variable name with capital letters appearing first
```
positional arguments:
  mcf                   merp command file

optional arguments:
  -h, --help            show this help message and exit
  -columns COLUMNS [COLUMNS ...]
                        names of columns to select for the output
  -format format        'tsv' for tab-separated rows x columns or 'yaml' for
                        YAML document output
  -tagf tagf            tagf.yml YAML file with additional column data to
                        merge with the output
  -debug                -debug mode shows command file parse before running
                        merp
```

## Select specific columns for viewing
add the -columns option and type the names of the columns you want (lowercase, no spaces in between)
### Example:
```
[astoermann@mkgpu1 Merp]$ merp2table s001pm.mcf -columns bin_desc chan_desc win_start win_stop meas_label
bin_desc	chan_desc	win_start	win_stop	meas_label
Hit minus CR	Fz	200.0	400.0	meana
Hit minus CR	F3	200.0	400.0	meana
Hit minus CR	F4	200.0	400.0	meana
```
Tip: you can pipe the output to the column command to make viewing easier since the output is tab delimited 
```
[astoermann@mkgpu1 Merp]$ merp2table s001pm.mcf -columns bin_desc chan_desc win_start win_stop meas_label | column -s $'\t' -t 
bin_desc                   chan_desc  win_start  win_stop  meas_label
Hit minus CR               Fz         200.0      400.0     meana
Hit minus CR               F3         200.0      400.0     meana
Hit minus CR               F4         200.0      400.0     meana
```

## Merge rows of other data with merp output
Use a yaml file to add metadata to the output of merp2table
### Example useage:
```
[astoermann@mkgpu1 Merp]$ merp2table s001pm.mcf -tagf test_PicMem.yml 
MainMeasuresLabels	baseline	baseline_tag	bin	bin_desc	chan	chan_desc	condition	epochs	erp_md5	erpfile	experimenter_id	expt	filter_tag	meas_args	meas_desc	meas_label	merp_error	merpfile	subject	task_tag	units	value	win_start	win_stop
```
Combine with columns command to see the new labels added (see below for creating the file)
```
[astoermann@mkgpu1 Merp]$ merp2table s001pm.mcf -columns bin_desc chan_desc win_start win_stop meas_label MainMeasuresLabels -tagf test_PicMem.yml | column -s $'\t' -t 
bin_desc                   chan_desc  win_start  win_stop  meas_label  MainMeasuresLabels
Hit minus CR               Fz         200.0      400.0     meana       FPma_HCdif_200_400_Fz
Hit minus CR               F3         200.0      400.0     meana       FPma_HCdif_200_400_F3
Hit minus CR               F4         200.0      400.0     meana       FPma_HCdif_200_400_F4
```
create a yaml file with the columns you would like to create to add information to each row (example in testdata) 
> variable_name:  --> name of the column 

> after colon and space  --> data to apply in that column to each row 

> use a comma delimited list after the colon to add different values to each row 

YAML is very picky about spaces and indentation, line breaks are OK 

### Singleton Tags 
add a column of data with all rows having the same value (no indentation at beginning of line) 
```
task_tag: pict mem 
filter_tag: low pass 15 
baseline_tag: merp default 
experimenter_id: 17 
```
### Tag Sequences Length > 1 
must align 1-1 exactly with merp measurments in order (pick one of two formats)

#### long tag 
> column name on first line followed by a colon

> row values on proceding lines with each item on a line preceded by 2 spaces, a hyphen, and 1 space 
```
long_row_tag:  
  - tagA 
  - tagB 
  - tagC 
  - tagD 
  - tagE 
  - tagF 
  - tagG 
  - tagH 
  - tagI 
  - tagJ 
  - tagK 
  - tagL 
  - tagM 
  - tagN 
  - tagO 
  - tagP 
  - tagQ 
  - tagR 
  - tagS 
  - tagT 
  - tagU 
  - tagV 
  - tagW 
  - tagX 
```


#### wide tag  
for a more condensed file, you can use a wide tag instead of the long tag

> column name on first line followed by a colon

> proceeding line starts with 2 spaces and an open square bracket 

> row names listed after the square bracket, comma separated (can add line breaks if you wish)

> ending with a closed square bracket 
```
wide_row_tag:  
  [tagA, tagB, tagC, tagD, tagE, tagF, tagG, tagH, tagI, tagJ,
  tagK, tagL, tagM, tagN, tagO, tagP, tagQ, tagR, tagS, tagT, 
  tagU, tagV, tagW, tagX] 
```


### to validate a YAML file on linux run
yamllint filename.yml 

and edit the text until the error messages are gone


## Choose tabluar vs document output format

