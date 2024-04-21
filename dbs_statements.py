import os
import pdfplumber
import re
import csv
import sys
from enum import Enum
import time

class ReadingState(Enum):
    NONE = 0
    CPF_ACCOUNT = 1
    SRS_ACCOUNT = 2
    MULTIPLIER_ACCOUNT = 3
    SAVINGS_ACCOUNT = 4
    CREDIT_CARD = 5
    PAYLAH = 6
    FIXED_DEPOSIT = 7

def check_credit_card_file(line):
    if "Credit Cards" in line or "credit cards " in line or "will be levied on each card account" in line:
        return True
    else:
        return False

def check_paylah_file(line):
    if "PayLah!" in line:
        return True
    else:
        return False

def get_date_and_amount_and_description(line, current_line, current_state, sign, year):
    parts = line.split()
    date = ' '.join(parts[:2])  # Combine the first two parts (date and month) into a single date

    # If year is available, add it to the date
    if year:
        date += f" {year}"
    
    if current_state == ReadingState.SRS_ACCOUNT:
        # Description is everything between the date and the second last part (amount)
        description = ' '.join(parts[2:-2])
        # Amount is the second last part
        amount = parts[-2]
        # Due to a bug in the December 2018 statement, we might have to look for a different field for the amount
        # Remove commas from the string
        if float(amount.replace(',', '')) == 0:
            amount = parts[-3]
            description = ' '.join(parts[2:-3])

    elif current_state == ReadingState.CPF_ACCOUNT:
        # Description is everything between the date and the second last part (amount)
        description = ' '.join(parts[2:-1])
        # Amount is the second last part
        amount = parts[-1]

    elif current_state == ReadingState.CREDIT_CARD:
        # Description is everything between the date and the second last part (amount)
        description = ' '.join(parts[2:-1])
        # Amount is the second last part
        amount = sign + parts[-1]

    elif current_state == ReadingState.PAYLAH:
        # Description is everything between the date and the third last part (amount)
        description = ' '.join(parts[2:-1])
        # Amount is the second last part
        amount = sign + parts[-1]
    
    return date, amount, description, current_line


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


def has_regex_match(current_state, text):
    if current_state == ReadingState.CREDIT_CARD:
        pattern = r'^\d{1,2} [a-zA-Z]{3}.*\d+\.\d{2}(?:(?: ?(?:CR|DB))(?!\S))?$'
    elif current_state == ReadingState.PAYLAH:
        pattern = r'^\d{1,2} [a-zA-Z]{3}.*\d+\.\d{2}'
    elif current_state in [ReadingState.SRS_ACCOUNT, ReadingState.CPF_ACCOUNT]:
        pattern = r'^\d{1,2} [a-zA-Z]{3} '
    else:
        return False
    
    return bool(re.search(pattern, text))

def extract_product_name(description, transaction_type):

    if transaction_type in ("Buy", "Sell"):
        # Define the pattern to match the product name
        pattern = r'(\d{2,}\s.*?)(?=\bref\b)'
        # Search for the pattern in the description
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
        return product_name
    else:
        return ""

def detect_end_of_account_transactions(line, current_status):
    end_of_account_transactions_conditions = {
        (ReadingState.MULTIPLIER_ACCOUNT, ReadingState.SAVINGS_ACCOUNT): 
            ["Total Balance", "Balance Carried Forward", "Total ", "ELIGIBLE TRANSACTIONS FOR", "Eligible Credit Card Billings", "TOTAL TRANSACTION AMOUNT", "DATE DESCRIPTION DETAILS AMOUNT"],
        (ReadingState.CPF_ACCOUNT, ReadingState.SRS_ACCOUNT):
            ["Balance Carried Forward", "Total Balance Carried Forward:"],
        (ReadingState.PAYLAH,):# Note the comma to make it a tuple
            ["Total "],
        (ReadingState.CREDIT_CARD,):# Note the comma to make it a tuple
            ["GRAND TOTAL FOR ALL CARD ACCOUNTS", "NEW TRANSACTIONS"]
    }

    for states, conditions in end_of_account_transactions_conditions.items():
        if current_status in states:
            for condition in conditions:
                # if line.startswith(condition):
                if condition in line:
                    return True
    
    return False

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
                data.append({"Date": date, "Description": description, "Amount": amount, "Currency": "SGD", "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})
            parsing_data = False
            processing_row = False
        
        # If we are currently parsing data rows
        if parsing_data:
            # Condition 2: Look for lines that begin with a date in the format "DD/MM/YYYY"
            if re.match(r'\d{2}/\d{2}/\d{4}', line):

                if processing_row:

                    product_name = extract_product_name(description, transaction_type)

                    # Append data to the list
                    data.append({"Date": date, "Description": description, "Amount": amount, "Currency": "SGD", "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})
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

def extract_savings_account_data(lines, start_index, current_state, currency, year):
    i = start_index
    transactions = []

    while i < len(lines):
        line = lines[i]
        if detect_end_of_account_transactions(lines[i], current_state):
        # if re.search(r"(Balance Carried Forward|Total Balance Carried Forward)", line):
            break

        # Extract currency
        if re.search(r"CURRENCY: (.+)", line):
            currency_mapping = {
                "SINGAPORE DOLLAR": "SGD",
                "UNITED STATES DOLLAR": "USD",
                "STERLING POUND": "GBP",
                "EUROPEAN UNION EURO": "EUR",
                "SWEDISH KRONER": "SEK",
                "JAPANESE YEN": "JPY"
            }
            currency = re.search(r"CURRENCY: (.+)", line).group(1).strip()
            currency = currency_mapping.get(currency, currency)
            i += 1
            continue

        # # Match lines starting with date format
        date_pattern = r'\b(0?[1-9]|[12]\d|3[01]) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?: (20\d{2}|2099))?\b'

        match = re.match(date_pattern, line, re.IGNORECASE)
        if match:
            date = match.group()  # Extract the matched date
            transaction_details = line[len(date):].split()  # Split the remaining part after the date

            #Add the year in case it is not already included
            if len(match.groups()) == 3:
                date = date + " " + str(year)

            # Look ahead to see if there is another line for the description
            next_line_index = i + 1
            description_lines = []

            if 'HOME LOAN' in line:
                b = True

            while next_line_index < len(lines) and not re.search(date_pattern, lines[next_line_index]) and not detect_end_of_account_transactions(lines[next_line_index], current_state):
                description_lines.append(lines[next_line_index].strip())
                next_line_index += 1

            description = " ".join(description_lines)
            # Determine the amount and transaction details
            if len(transaction_details) > 1:
                # Check if both the last and second-to-last elements are numbers
                if all(word.replace(',', '').replace('.', '').isdigit() for word in transaction_details[-2:]):
                    amount = transaction_details[-2]
                    transaction_detail_text = " ".join(transaction_details[:-2])
                # Check if only the last element is a number
                elif transaction_details[-1].replace(',', '').replace('.', '').isdigit():
                    amount = transaction_details[-1]
                    transaction_detail_text = " ".join(transaction_details[:-1])
                else:
                    # If neither condition is met, assume the last word is the amount
                    amount = transaction_details[-1]
                    transaction_detail_text = " ".join(transaction_details[:-1])
            else:
                # If there's only one word (amount), set it as amount and leave transaction_detail_text empty
                amount = transaction_details[0]
                transaction_detail_text = ""

            if current_state == ReadingState.MULTIPLIER_ACCOUNT:
                account_type = "DBS Multiplier Account"
            elif current_state == ReadingState.SAVINGS_ACCOUNT:
                account_type = "DBS Savings Account"

            if amount == "0.60":
                b = True

            transactions.append({
                        "Account Type": account_type,
                        "Date": date.strip(),
                        "Transaction Type": transaction_detail_text,
                        "Amount": amount,
                        "Description": description,
                        "Currency": currency
                    })
        
            i = next_line_index
            continue

        i += 1

    return transactions, i, currency

def extract_data_old_format(text, keyword, year):

    # Split the text into lines
    lines = text.split('\n')
    
    # Flag to indicate if we are currently parsing data rows
    current_state = ReadingState.NONE
    current_line = 0
    product_name = "" #Defaulting as it's only applicable to CPF_ACCOUNT and SRS_ACCOUNT
    currency = "SGD" #Default currency

    # Variables to store data
    data = []
    
    # Iterate over each line in the text
    # for line in lines:
    while current_line < len(lines):
        line = lines[current_line]
        # print(line)

        # Check for DBS Multiplier or Savings Account number
        if line.startswith("DBS Multiplier Account Account No"):
            current_state = ReadingState.MULTIPLIER_ACCOUNT
            extracted_transactions, current_line, currency = extract_savings_account_data(lines, current_line, current_state, currency, year)
            # print(extracted_transactions)
            data.extend(extracted_transactions)
            current_state = ReadingState.NONE

        elif line.startswith("DBS Savings Account Account No"):
            current_state = ReadingState.SAVINGS_ACCOUNT
            extracted_transactions, current_line, currency = extract_savings_account_data(lines, current_line, current_state, currency, year)
            # print(extracted_transactions)
            data.extend(extracted_transactions)
            current_state = ReadingState.NONE

        # Condition 1: Look for a line that starts with "SRS Account"
        elif line.startswith("SRS Account"):
            current_state = ReadingState.SRS_ACCOUNT
            account_type = "SRS"
            currency = "SGD" #Default currency
            transaction_type = ""
            quantity = ""

        # Condition 1: Look for a line that starts with "CPF Investment Account"
        elif line.startswith("CPF Investment Account"):
            current_state = ReadingState.CPF_ACCOUNT
            account_type = "CPF"
            currency = "SGD" #Default currency
            transaction_type = ""
            quantity = ""

        # Condition 1:  for Credit Card pages
        elif keyword == "Credit Card":
            current_state = ReadingState.CREDIT_CARD
            account_type = "Credit Card"
            currency = "SGD" #Default currency
            transaction_type = ""
            quantity = ""

        # Condition 1:  for PayLah pages
        elif keyword == "PayLah":
            current_state = ReadingState.PAYLAH
            account_type = "PayLah"
            currency = "SGD" #Default currency
            transaction_type = ""
            quantity = ""

        # End the search when you reach the end
        if detect_end_of_account_transactions(line, current_state):
            current_state = ReadingState.NONE
       
        # If we are currently parsing data rows
        if current_state in (ReadingState.CPF_ACCOUNT, ReadingState.SRS_ACCOUNT, ReadingState.PAYLAH, ReadingState.CREDIT_CARD):
            # Condition 2: Look for lines that start with a date in the format "DD MMM"

            if has_regex_match(current_state, line):
                sign = "+"
                # If the line ends with CR, it's a negative value, and remove "CR"
                if re.match(r".*CR$", line):
                    # Remove the "CR"
                    line = re.sub(r"CR$", "", line)
                elif re.match(r".*DB$", line):
                    # Remove the "DB"
                    line = re.sub(r"DB$", "", line)
                    sign = "-"
                else:
                    sign = "-"

                date, amount, description, current_line = get_date_and_amount_and_description(line, current_line, current_state, sign, year)

                # Condition 5: Ignore any row that only has a date followed by an amount, meaning, description is empty
                if current_state in (ReadingState.CPF_ACCOUNT, ReadingState.SRS_ACCOUNT):
                    if description != "":
                        # Condition 7: Setting Transaction Type based on description
                        transaction_type, quantity = extract_from_description(description)
                        product_name = extract_product_name(description, transaction_type)

                # Append data to the list
                data.append({"Date": date, "Description": description, "Amount": amount, "Currency": currency, "Account Type": account_type, "Transaction Type": transaction_type, "Quantity": quantity, "Price": calculate_price(amount, quantity), "Product Name": product_name})
        current_line = current_line + 1

    return data

def extract_dbs_statement_data(directory, output_file):
    # Open CSV file for writing
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        # CSV writer
        writer = csv.DictWriter(csvfile, fieldnames=["Date", "Description", "Amount", "Currency", "Account Type", "Transaction Type", "Quantity", "Price", "Product Name"])
        writer.writeheader()

        # Iterate over each PDF file in the directory
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                print(filename)
                # Open the PDF file
                with pdfplumber.open(os.path.join(directory, filename)) as pdf:

                    is_credit_card_file = check_credit_card_file(pdf.pages[0].extract_text())

                    if not is_credit_card_file:
                        is_paylah_file = check_paylah_file(pdf.pages[0].extract_text())

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
                        elif is_paylah_file:
                            # Extract PayLah! data
                            extracted_data = extract_data_old_format(text, "PayLah", year)

                        else: # Consolidated Statement
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

    start_time = time.time()

    # Call the function to extract data from the PDF file
    extract_dbs_statement_data(directory, output_file)
    print(output_file)

    end_time = time.time()

    execution_time_seconds = end_time - start_time
    execution_time_minutes = int(execution_time_seconds // 60)
    execution_time_seconds = int(execution_time_seconds % 60)

    execution_time_formatted = "{:02d}:{:02d}".format(execution_time_minutes, execution_time_seconds)
    print("Execution time:", execution_time_formatted)

