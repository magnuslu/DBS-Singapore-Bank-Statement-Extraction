import os
import pdfplumber
import re
import csv
import sys

def check_credit_card_file(line):
    if "Credit Cards" in line or "credit cards " in line or "will be levied on each card account" in line:
        return True
    else:
        return False

def extract_from_description(description):
    transaction_type = "Others"
    quantity = ""
    if "DIV" in description or "DIST" in description:
        transaction_type = "Dividend"
    elif "INTEREST" in description:
        transaction_type = "Interest"
    elif "SVC" in description or "SERVICE" in description or "GST" in description or "FEE" in description:
        transaction_type = "Charges"
    elif "CONTRIBUTION" in description:
        transaction_type = "Contribution"
    elif "BUY" in description:
        transaction_type = "Buy"
        quantity = extract_quantity(description)
    elif "SELL" in description:
        transaction_type = "Sell"
        quantity = extract_quantity(description)
    elif "TRANSFER" in description or "TRF TO CPFB" in description:
        transaction_type = "Transfer"
    return transaction_type, quantity


def has_regex_match(keyword, text):
    if keyword == "Credit Card":
        pattern = r'^\d{1,2} [a-zA-Z]{3}.*\d+\.\d{2}$'
    elif keyword in ["Supplementary Retirement Scheme Account", "CPF Investment Scheme"]:
        pattern = r'^\d{1,2} [a-zA-Z]{3} '
    else:
        return False

    return bool(re.search(pattern, text))

def extract_product_name(description, transaction_type):

    if transaction_type in ("Buy", "Sell"):
        # Define the pattern to match the product name
        pattern = r'(\d{2,}\s.*?)(?=\bref\b)'
        # Search for the pattern in the description
        print(description)
        match = re.search(pattern, description, flags=re.IGNORECASE)
        if match:
            # Extract the captured substring (product name)
            product_name = match.group(1).strip()
            return product_name
        else:
            return None
    elif transaction_type in ("Dividend", "Others"):
        product_name = description.replace(' CAPDIST', '')
        product_name = product_name.replace('CAP DIST', '')
        product_name = product_name.replace('DIV : ', '')
        product_name = product_name.replace('REIT-', '')
        product_name = product_name.replace('REIT - ', '')
        product_name = product_name.strip()
        # Define the pattern to match "Total" and any characters following it
        pattern = r'Total.*'
        # Use re.sub() to replace all occurrences of the pattern with an empty string
        product_name = re.sub(pattern, '', product_name, flags=re.IGNORECASE)
        print(product_name)
        return product_name
    else:
        return ""

def extract_quantity(description):
    # Define the pattern to match a numeric value after "BUY" or "SELL"
    pattern = r'(?:BUY|SELL).+?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'    
    # Search for the pattern in the description
    match = re.search(pattern, description)
    if match:
        # Extract the numeric value
        quantity = match.group(1)
        return quantity
    else:
        return None

def calculate_price(amount, quantity):
    # Check if quantity is an empty string
    if quantity == '':
        return None
        
    # Remove commas from the string
    quantity = quantity.replace(',', '')
    # Convert quantity to float
    quantity = float(quantity)
    
    if amount == '':
        return None
    # Remove commas from the string
    amount = amount.replace(',', '')
    # Convert quantity to float
    amount = float(amount)
    
    if quantity != 0:
        # Calculate the price rounded to 4 decimals
        price = round(amount / quantity, 4)
        return price
    else:
        return None
        
# Function to extract data from text based on specified conditions
def extract_data(text, keyword):
    # Split the text into lines
    lines = text.split('\n')
    
    # Flag to indicate if we are currently parsing data rows
    parsing_data = False
    processing_row = False
    
    # Variables to store data
    data = []
    current_date = ""
    current_description = ""
    
    # Iterate over each line in the text
    for line in lines:
    
        # Condition 1: Find the first line that contains the specified keyword
        if keyword in line:
            parsing_data = True
            processing_row = False

        # Condition 6: Stop looking for data rows once the text "Balance Carried Forward" has been found
        if "Balance Carried Forward" in line:
            if processing_row:
                product_name = extract_product_name(description, transaction_type)
                    
                # Append data to the list
                data.append({"Date": date, "Description": description, "Amount": amount, "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})
            parsing_data = False
            processing_row = False
        
        # If we are currently parsing data rows
        if parsing_data:
            # Condition 2: Look for lines that begin with a date in the format "DD/MM/YYYY"
            if re.match(r'\d{2}/\d{2}/\d{4}', line):

                if processing_row:

                    product_name = extract_product_name(description, transaction_type)

                    # Append data to the list
                    data.append({"Date": date, "Description": description, "Amount": amount, "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})
                processing_row = True
            
                # Extract date, description, and amount
                parts = line.split()
                date = parts[0]
                description = ' '.join(parts[1:-2])
                # Extract the last amount for "CPF Investment Scheme" and the second last amount for "Supplementary Retirement Scheme Account"
                if keyword == "CPF Investment Scheme":
                    description = ' '.join(parts[1:-1])  # Exclude the last part for CPF
                    amount = parts[-1]
                    account_type = "CPF"
                elif keyword == "Supplementary Retirement Scheme Account":
                    description = ' '.join(parts[1:-2])  # Exclude the last two parts for SRS
                    amount = parts[-2]
                    # Due to a bug in the December 2018 statement, we might have to look for a different field for the amount
                    # Remove commas from the string
                    if float(amount.replace(',', '')) == 0:
                        amount = parts[-3]
                        description = ' '.join(parts[2:-3])
                    account_type = "SRS"
                    
                # Condition 5: Ignore any row that only has a date followed by an amount
                if description:
                    transaction_type, quantity = extract_from_description(description)

                else:                    
                # If there is no description, we're not processing a valid row
                    processing_row = False

            elif processing_row:
                description += line

    return data

import re

def extract_data_old_format(text, keyword, year):

    # Split the text into lines
    lines = text.split('\n')
    
    # Flag to indicate if we are currently parsing data rows
    parsing_data = False
    processing_row = False
    
    # Variables to store data
    data = []
    
    # Iterate over each line in the text
    for line in lines:
        # Condition 1: Look for a line that starts with "SRS Account"
        if line.startswith("SRS Account"):
            parsing_data = True
            processing_row = False
            account_type = "SRS"
        
        # Condition 1: Look for a line that starts with "CPF Investment Account"
        if line.startswith("CPF Investment Account"):
            parsing_data = True
            processing_row = False
            account_type = "CPF"

        # Condition 1: Look for a line that starts with "NEW TRANSACTIONS" for Credit Card pages
        if keyword == "Credit Card":
            parsing_data = True
            account_type = "Credit Card"
            transaction_type = ""
            quantity = ""

        # Condition 4: End the search when you find "Balance Carried Forward" at the beginning of a line and start looking for "SRS Account" again.
        if line.startswith("Balance Carried Forward") or line.startswith("SUB-TOTAL:") or line.startswith("TOTAL:") or line.startswith("Total Balance Carried Forward:") or line.startswith("Total ") or line.startswith("Page "):
            if processing_row:
                product_name = extract_product_name(description, transaction_type)
                    
                # Append data to the list
                data.append({"Date": date, "Description": description, "Amount": amount, "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})
            parsing_data = False
            processing_row = False
        
        # Condition 4: End the search when you find "Balance Carried Forward" at the beginning of a line and start looking for "SRS Account" again.
        if line.startswith("GRAND TOTAL FOR ALL CARD ACCOUNTS"):
            if processing_row:
                # Append data to the list
                data.append({"Date": date, "Description": description, "Amount": amount, "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})
            parsing_data = False
            processing_row = False
        
        # If we are currently parsing data rows
        if parsing_data:
            # Condition 2: Look for lines that start with a date in the format "DD MMM"
            if has_regex_match(keyword, line):
                sign = ""
                # If the line ends with CR, it's a negative value, and remove "CR"
                if re.match(r".*CR$", line):
                    # Remove the "CR"
                    print("CREDIT", line)
                    line = re.sub(r"CR$", "", line)
                    sign = "-"

                if processing_row:

                    product_name = extract_product_name(description, transaction_type)

                    # Append data to the list
                    data.append({"Date": date, "Description": description, "Amount": amount, "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})
                processing_row = True

                # Extract date, description, and amount
                parts = line.split()
                date = ' '.join(parts[:2])  # Combine the first two parts (date and month) into a single date

                # If year is available, add it to the date
                if year:
                    date += f" {year}"
                
                if account_type == "SRS":
                    # Description is everything between the date and the second last part (amount)
                    description = ' '.join(parts[2:-2])
                    # Amount is the second last part
                    amount = parts[-2]
                    # Due to a bug in the December 2018 statement, we might have to look for a different field for the amount
                    # Remove commas from the string
                    if float(amount.replace(',', '')) == 0:
                        amount = parts[-3]
                        description = ' '.join(parts[2:-3])

                if account_type == "CPF":
                    # Description is everything between the date and the second last part (amount)
                    description = ' '.join(parts[2:-1])
                    # Amount is the second last part
                    amount = parts[-1]

                if account_type == "Credit Card":
                    # Description is everything between the date and the second last part (amount)
                    description = ' '.join(parts[2:-1])
                    # Amount is the second last part
                    amount = parts[-1]

                # Condition 5: Ignore any row that only has a date followed by an amount, meaning, description is empty
                if account_type in ("CPF", "SRS"):
                    if description:
                        # Condition 7: Setting Transaction Type based on description
                        # Not applicable for Credit Cards
                        transaction_type, quantity = extract_from_description(description)

                    else:
                    # If there is no description, we're not processing a valid row
                        print(line)
                        processing_row = False

            elif processing_row:
                description += line

    # In order not to miss the last line of the statement    
    if processing_row:
        product_name = extract_product_name(description, transaction_type)
            
        # Append data to the list
        data.append({"Date": date, "Description": description, "Amount": amount, "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})

    return data

def extract_dbs_statement_data(directory, output_file):
    # Open CSV file for writing
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        # CSV writer
        writer = csv.DictWriter(csvfile, fieldnames=["Date", "Description", "Amount", "Account Type", "Transaction Type", "Quantity", "Price", "Product Name"])
        writer.writeheader()
        
        # Iterate over each PDF file in the directory
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                print(filename)
                # Open the PDF file
                with pdfplumber.open(os.path.join(directory, filename)) as pdf:

                    is_credit_card_file = check_credit_card_file(pdf.pages[0].extract_text())

                    # Iterate over each page in the PDF
                    for page_number, page in enumerate(pdf.pages, start=1):
                        # Extract text from the page
                        text = page.extract_text()
                        
                        # Get the year from the first page
                        if (page_number == 1):
                            # Extract year from "As at DD MMM YYYY"
                            year_match = re.search(r'As at \d{1,2} \w{3} (\d{4})', text)
                            if year_match:
                                year = year_match.group(1)
                            else:
                                year = None                    
                        
                        # Get the year from the first page
                        if (page_number == 1):
                            # Extract year from "DD MMM YYYY"
                            year_match = re.search(r'\d{1,2} [a-zA-Z]{3} (\d{4})', text)
                            if year_match:
                                year = year_match.group(1)
                            else:
                                year = None                    
                        
                        if is_credit_card_file:
                            # Extract credit card data
                            extracted_data = extract_data_old_format(text, "Credit Card", year)

                        else:
                            # Extract data for CPF Investment Scheme
                            cpf_data = extract_data(text, "CPF Investment Scheme")
                            
                            # Extract data for Supplementary Retirement Scheme Account
                            supplementary_data = extract_data(text, "Supplementary Retirement Scheme Account")
                            supplementary_data_2 = extract_data_old_format(text, "Supplementary Retirement Scheme Account", year)
                        
                        # Combine cpf_data and supplementary_data into a single list
                            extracted_data = cpf_data + supplementary_data + supplementary_data_2
                    
                        # Write the combined data to CSV file
                        for row in extracted_data:
                            writer.writerow(row)

    print("Data extracted and saved to ", output_file)

# Example usage:
if __name__ == "__main__":
    # Check if the correct number of command-line arguments are provided
    if len(sys.argv) != 3:
        print("Usage: python dbs_statements.py DIRECTORY_OF_PDF_FILES CSV_OUTPUT_FILE_NAME.")
        sys.exit(1)

    # Directory containing PDF files
    directory = "DBS Statements/Credit Cards"

    # Output CSV file
    output_file = "extracted_data.csv"

    # Extract PDF file path and page number from command-line arguments
    directory = sys.argv[1]
    output_file = sys.argv[2]

    # Call the function to extract data from the PDF file
    extract_dbs_statement_data(directory, output_file)
