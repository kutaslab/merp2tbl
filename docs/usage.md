# How to ...

convert verbose merp output to standard data interchange formats 
## Example:

```bash
[mkresearch1@mkgpu1 turbach]$ merp2table
usage: merp2table [-h] [-columns COLUMNS [COLUMNS ...]] [-format format]
                  [-tagf tagf] [-debug]
                  mcf
merp2table: error: the following arguments are required: mcf

```
extra commands must be in the order above for merp2table to run
if you are only using one of the extra commands, it must go after the mcf argument or merp2table will not run
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

## Merge rows of other data with merp output
create a yaml file with the columns you would like to create to add information to each row (example in testdata) 
> variable_name:  --> name of the column 

> after colon and space  --> data to apply in that column to each row 

> use a comma delimited list after the colon to add different values to each row 
YAML is very picky about spaces and indentation, line breaks are OK 

### singleton tags: add a column of data with all rows having the same value (no indentation at beginning of line) 
```
task_tag: pict mem 
filter_tag: low pass 15 
baseline_tag: merp default 
experimenter_id: 17 
```
### tag sequences length > 1: must align 1-1 exactly with merp measurments in order (pick one of two formats)
long tag --> column name on first line followed by a colon, row names on proceding lines with each item on a line preceded by 2 spaces, a hyphen, and 1 space 
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

if you want a more condensed file, you can also use a wide tag

wide tag  --> column name on first line followed by a colon, row names on proceding lines, comma separated, starting with 2 spaces and an open bracket '[' and ending with a closed braket ']' 

wide_row_tag:  
  [tagA, tagB, tagC, tagD, tagE, tagF, tagG, tagH, tagI, tagJ,
  tagK, tagL, tagM, tagN, tagO, tagP, tagQ, tagR, tagS, tagT, 
  tagU, tagV, tagW, tagX] 



### to validate a YAML file on linux run
yamllint filename.yml 

and edit the text until the error messages are gone


## Choose tabluar vs document output format

