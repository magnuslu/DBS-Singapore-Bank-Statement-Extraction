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


        page.extract_text(x_tolerance=3, x_tolerance_ratio=None, y_tolerance=3, layout=False, x_density=7.25, y_density=13, line_dir_render=None, char_dir_render=None, **kwargs)

        # ts = {
        #     "vertical_strategy": "lines",
        #     "horizontal_strategy": "text",
        #     "snap_tolerance": 5,
        #     "intersection_tolerance": 15,
        # }

        # Extract text from the page
        text = page.extract_text()
        text_lines = text.split('\n')
        print(text)
        # # Extract tables from the page
        # tables = page.extract_tables(table_settings=ts)
        tables = page.extract_tables()

        # Remove empty sublists
#        tables = [sublist for sublist in tables if any(item != '' for item in sublist)]
#        tables = [sublist for sublist in tables if sublist != ['', '', '', '', '', '']]
#        tables = list(filter(lambda x: x != ['', '', '', '', '', ''], tables))
#        tables = [sublist for sublist in tables if sublist != ['', '', '', '', '', '']]
#        while [''] * 6 in tables:
#            tables.remove([''] * 6)

        im = page.to_image()
#        im.show()
        im.reset().debug_tablefinder().show()
        cleaned_dataset = []
        # for sublist in tables:
        #     for subsublist in sublist:
        #         if subsublist != ['', '', '', '', '', ''] and subsublist != ['', '', '', '', '']:
        #             cleaned_dataset.append(subsublist)

        print(tables.count)
        for subsublist in tables[2]:
            if subsublist != ['', '', '', '', '', ''] and subsublist != ['', '', '', '', '']:
                cleaned_dataset.append(subsublist)

        tables = cleaned_dataset
#        print(tables)

        for row in tables:
            filtered_row = [str(cell) for cell in row if cell is not None]
#            txt_file.write('\t'.join(filtered_row) + '\n')
            print(filtered_row)

#        print(tables)
        

#        print(page.extract_tables(table_settings=ts))

        
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
#                            print(row)
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
