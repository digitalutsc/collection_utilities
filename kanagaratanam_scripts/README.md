# kanagaratanam_scripts

## `generate_inject_csv`

This script takes an input CSV such as [this one](https://docs.google.com/spreadsheets/d/1G87sfj3088CYs-ziHVHOkfryWg-MkkjWHy5dQ2cjBec/edit#gid=552474195) and outputs one with each row representing either "Paged Content" or a "Page" of the Paged Content. It expands each row according to its "Associated Image #s" in the input CSV. The output CSV can then be used to ingest the paged content into Islandora.

See the description of the script (in the script file) for details.

## `rotate`

This multithreaded script takes an input CSV such as [this one](https://docs.google.com/spreadsheets/d/1G87sfj3088CYs-ziHVHOkfryWg-MkkjWHy5dQ2cjBec/edit#gid=1645501301) and, for every row in the CSV, rotates the image described in that row by a certain rotation factor (also in the row). 

See the description of the script (in the script file) for details.
