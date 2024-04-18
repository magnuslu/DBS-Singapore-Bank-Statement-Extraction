import os
import pdfplumber
import re
import datetime
import sys
#from datetime import datetime

def convert_date_format(date_str):
    # Convert the date string to a datetime object
    date_obj = datetime.strptime(date_str, "%d %b %Y")
    # Format the datetime object to the desired format
    formatted_date = date_obj.strftime("%Y-%m-%d")
    return formatted_date

import re

def extract_date_for_credit_card(line):

    if "PayLah" in line:
        file_type = "PayLah"
    elif "Credit Cards" in line or "credit cards " in line or "will be levied on each card account":
        file_type = "Credit Card"
    else:
        print("No Credit Cards or PayLah")
        return None

    # Define the regular expression pattern to match the date
    date_pattern = r'\b(0?[1-9]|[12]\d|3[01]) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (20\d{2}|2099)\b'

    # Search for the first occurrence of the date pattern in the line
    date_match = re.search(date_pattern, line)

    # If a match is found, extract the matched date
    if date_match:
        matched_date = date_match.group(0)
        
        # Parse the matched date string into a datetime object
        date_obj = datetime.datetime.strptime(matched_date, '%d %b %Y')

        # Format the datetime object as YYYY-MM
        formatted_date = date_obj.strftime('%Y-%m')
        return file_type + " Statement - " + formatted_date + ".pdf"
    else:
        print("No date found")
        return None

def rename_statements(directory):
    # Iterate over each PDF file in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            # Open the PDF file
            with pdfplumber.open(os.path.join(directory, filename)) as pdf:
                print(filename)
                # Extract text from the first page
                first_page_text = pdf.pages[0].extract_text()

                # Split the text into lines
                lines = first_page_text.split('\n')
                
                # credit_card_file_name = extract_date_for_credit_card(first_page_text, pdf.pages[0].extract_table())
                credit_card_file_name = extract_date_for_credit_card(first_page_text)

                if credit_card_file_name != None:
                    # Close the PDF file before renaming
                    pdf.close()
                    # Rename the file to "Consolidated Statement - <appended_text>.pdf"
                    new_filename = credit_card_file_name
                    os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename))
                    print(f"Renamed {filename} to {new_filename}")

                else:
                    # Flag to indicate if we've found "Account Summary" and "Consolidated Statement"
                    account_summary_found = False
                    consolidated_statement_found = False
                    appended_text = ""
                    
                    # Iterate over each line in the text
                    for line in lines:
                        # Check if "Account Summary" is present
                        if "Account Summary" in line or "ACCOUNT SUMMARY" in line:
                            account_summary_found = True
                        
                        # Extract the appended text
                        match = re.search(r'as at (.+)', line)
                        if match:
                            appended_text = match.group(1)
                            print(appended_text)
                            formatted_date = convert_date_format(appended_text)
                            print(formatted_date)
                            appended_text = formatted_date
                    
                        # Extract the appended text
                        match = re.search(r'As at (.+)', line)
                        if match:
                            appended_text = match.group(1)
                            print(appended_text)
                            formatted_date = convert_date_format(appended_text)
                            print(formatted_date)
                            appended_text = formatted_date

                    # Check if both "Account Summary" was found
                    if account_summary_found:
                        # Close the PDF file before renaming
                        pdf.close()
                        # Rename the file to "Consolidated Statement - <appended_text>.pdf"
                        new_filename = f"Consolidated Statement - {appended_text}.pdf"
                        os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename))
                        print(f"Renamed {filename} to {new_filename}")


# Example usage:
if __name__ == "__main__":
    # Check if the correct number of command-line arguments are provided
    if len(sys.argv) != 2:
        print("Usage: python dbs_rename_statements.py DIRECTORY.")
        sys.exit(1)

    directory = "DBS Statements/Credit Cards"

    # Extract PDF file path and page number from command-line arguments
    directory = sys.argv[1]

    # Call the function to extract data from the PDF file
    rename_statements(directory)
