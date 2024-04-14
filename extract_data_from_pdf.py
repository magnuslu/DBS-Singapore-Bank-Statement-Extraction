import pdfplumber
import os
import sys

def extract_data_from_pdf(page_number, pdf_file_path):

    print("extract_data_from_pdf")
    print(page_number)
    print(pdf_file_path)
    # Open the PDF file
    with pdfplumber.open(pdf_file_path) as pdf:
        # Get the specified page
        page = pdf.pages[page_number - 1]
        
        # Extract tables from the page
        tables = page.extract_tables()
        print(tables)
        
        # Extract text from the page
        text = page.extract_text()
        text_lines = text.split('\n')
        
        # Create a text file with the same name as the PDF file but with a txt extension
        txt_file_path = os.path.splitext(pdf_file_path)[0] + '.txt'
        
        with open(txt_file_path, 'w') as txt_file:
            print(txt_file_path)
            # Write table data to the text file
            for table_number, table in enumerate(tables, start=1):
                txt_file.write(f"Table {table_number}:\n")
                if table is not None:
                    for row in table:
                        if row is not None:
                            print(row)
                            filtered_row = [str(cell) for cell in row if cell is not None]
                            txt_file.write('\t'.join(filtered_row) + '\n')
                    txt_file.write('\n\n')
            
            # Write extracted text to the text file with line numbers
            for line_number, line in enumerate(text_lines, start=1):
                txt_file.write(f"Line {line_number}: {line}\n")

# Example usage:
if __name__ == "__main__":
    # Check if the correct number of command-line arguments are provided
    if len(sys.argv) != 3:
        print("Usage: python script.py PAGE_NUMBER PDF_FILE_PATH.")
        sys.exit(1)

    # Extract PDF file path and page number from command-line arguments
    page_number = int(sys.argv[1])
    pdf_file_path = sys.argv[2]

    # Call the function to extract data from the PDF file
    extract_data_from_pdf(page_number, pdf_file_path)
