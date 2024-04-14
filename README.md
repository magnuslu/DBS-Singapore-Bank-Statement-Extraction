# DBS Statements Extraction
This is my first GitHub project for the extraction of data from DBS Bank (Singapore) statements to a CSV file.

So far it works for CPF, SRS and Credit Card accounts only.

There are three main python files.

extract_data_from_pdf.py
This is a generic function to extract tables and text from a PDF file. It works on any PDF file, not only DBS bank statements.
Parameters:
[1] The page number to extract
[2] The full path the the PDF to extract text and tables from

dbs_rename_statements.py
This will rename DBS statements from the file name they get when they are first downloaded, which is something link jfw9u34falskfw09u23f.pdf. The new name will be:
For credit card statements: Credit Cards Statement - YYYY-MM.pdf
For consolidated statements: Consolidated Statement - YYYY-MM-DD.pdf
Parameters:
[1] Full path to the directory where the PDF files are stored

dbs_statement.py
This is the main function here. It will go throgh all the DBS Bank Statements in the source folder and extract transasction information for SRS accounts, CPF accounts and Credit Card accounts.

It will have the following data:
Date, Description, Amount, Account Type, Transaction Type, Quantity, Price, Product Name

Parameters:
[1] Full path to the directory where the PDF files can be found
[2] Full path, incl. name, of the csv file to be generated. Do include the .csv extension.



