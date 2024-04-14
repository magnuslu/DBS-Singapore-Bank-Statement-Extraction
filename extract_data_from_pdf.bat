@echo off
rem Call the Python script with the specified arguments
echo %1
echo %2
python extract_data_from_pdf.py %1 %2

pause
