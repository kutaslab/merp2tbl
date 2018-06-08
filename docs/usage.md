# How to ...

usage: merp2table [-h] [-columns COLUMNS [COLUMNS ...]] [-format format] <br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [-tagf tagf] [-debug] <br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; mcf <br>
<br>
convert verbose merp output to standard data interchange formats <br>
<br>
positional arguments:<br>
&nbsp;&nbsp;&nbsp;&nbsp;  mcf  --> merp command file<br>
<br>
optional arguments: <br>
&nbsp;&nbsp;&nbsp;&nbsp;  -h, --help --> show this help message and exit<br>
&nbsp;&nbsp;&nbsp;&nbsp;  -columns COLUMNS [COLUMNS ...] --> names of columns to select for the output<br>
&nbsp;&nbsp;&nbsp;&nbsp; -format format --> 'tsv' for tab-separated rows x columns or 'yaml' for YAML document output<br>
&nbsp;&nbsp;&nbsp;&nbsp;  -tagf tagf --> tagf.yml YAML file with additional column data to merge with the output<br>
&nbsp;&nbsp;&nbsp;&nbsp;  -debug --> -debug mode shows command file parse before running merp<br>
<br>

## Example:

```
[mkresearch1@mkgpu1 turbach]$ merp2table
usage: merp2table [-h] [-columns COLUMNS [COLUMNS ...]] [-format format]
                  [-tagf tagf] [-debug]
                  mcf
merp2table: error: the following arguments are required: mcf

```

> extra commands must be in the order above for merp2table to run

## Select specific columns for viewing
add the -columns option and type the names of the columns you want (lowercase, no spaces in between)

## Merge rows of other data with merp output
create a yaml file with the columns you would like to create to add information to each row (example in testdata) <br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; variable_name:  --> name of the column <br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; after colon and space  --> data to apply in that column to each row <br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; use a comma delimited list after the colon to add different values to each row <br>
YAML is very picky about spaces and indentation, line breaks are OK <br>

### singleton tags: add a column of data with all rows having the same value (no indentation at beginning of line) <br>
task_tag: pict mem <br>
filter_tag: low pass 15 <br>
baseline_tag: merp default <br>
experimenter_id: 17 <br>

### tag sequences length > 1: must align 1-1 exactly with merp measurments in order (pick one of two formats)
wide tag  --> column name on first line followed by a colon, row names on proceding lines, comma separated, starting with 2 spaces and an open bracket '[' and ending with a closed braket ']' <br>
<br>
wide_row_tag:  <br>
&nbsp;&nbsp;  [tagA, tagB, tagC, tagD, tagE, tagF, tagG, tagH, tagI, tagJ,<br>
&nbsp;&nbsp;&nbsp;  tagK, tagL, tagM, tagN, tagO, tagP, tagQ, tagR, tagS, tagT, <br>
&nbsp;&nbsp;&nbsp;  tagU, tagV, tagW, tagX] <br>

long tag --> column name on first line followed by a colon, row names on proceding lines with each item on a line preceded by 2 spaces, a hyphen, and 1 space <br>
<br>
long_row_tag:  <br>
&nbsp;&nbsp;  - tagA <br>
&nbsp;&nbsp;  - tagB <br>
&nbsp;&nbsp;  - tagC <br>
&nbsp;&nbsp;  - tagD <br>
&nbsp;&nbsp;  - tagE <br>
&nbsp;&nbsp;  - tagF <br>
&nbsp;&nbsp;  - tagG <br>
&nbsp;&nbsp;  - tagH <br>
&nbsp;&nbsp;  - tagI <br>
&nbsp;&nbsp;  - tagJ <br>
&nbsp;&nbsp;  - tagK <br>
&nbsp;&nbsp;  - tagL <br>
&nbsp;&nbsp;  - tagM <br>
&nbsp;&nbsp;  - tagN <br>
&nbsp;&nbsp;  - tagO <br>
&nbsp;&nbsp;  - tagP <br>
&nbsp;&nbsp;  - tagQ <br>
&nbsp;&nbsp;  - tagR <br>
&nbsp;&nbsp;  - tagS <br>
&nbsp;&nbsp;  - tagT <br>
&nbsp;&nbsp;  - tagU <br>
&nbsp;&nbsp;  - tagV <br>
&nbsp;&nbsp;  - tagW <br>
&nbsp;&nbsp;  - tagX <br>

### to validate a YAML file on linux run
yamllint filename.yml <br>
<br>
and edit the text until the error messages are gone


## Choose tabluar vs document output format
