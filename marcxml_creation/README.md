# Collection Utilities CSV to MARC XML Scripts

These scripts are for converting CSV's into MARC records, in XML format. Specifically, these are for the University of Toronto Scarborough's Tamil collections.

# Running the script

To use the script, simply use the generate_xml() function. It takes the input file and output file name as follows:
generate_xml('[output file name]', '[input csv name]')

for instance:
generate_xml('my-marc-xml', 'simple-example.csv')

# How it reads your CSV (important!)

How does it work?

1. Each row (for the exception of the title row) of the CSV is one record, which will be generated as an XML file.

2. The header of each column should show where the content of the column will end up in the MARC.

For example, a header could be: '100 $a'. This would mean whatever is in that column goes in the '100' field and 'a' subfield. This can be seen with 'simple-example.csv' in the examples folder. 

3. If a column header is empty, it will not be included in the MARC XML. If no subfield character is provided (ex. '100' instead of '100 $a') it will be entered in a subfield with an 'a'.

4. Any column with '(Tamil)' in the header will be transliterated, and the original Tamil content will be put in a corresponding feild with tag 880. A subfield with code '6' will show which '880' field was generated for it.


