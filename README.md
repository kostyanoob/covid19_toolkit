# covid19_toolkit
 Goal: Optimally select people for COVID19 testing. If you're running an organization and you can pick only a limited number of people for a daily test, this software will select the optimal subset of people that minimizes the risk of an outbreak in your organization.

 
![Screenshot of the software](HighLevel.PNG)
 
# Preparations
You are required to create a "Solvers" directory to contain at least one solver software. We recommend downloading the free GLPK:
http://guix.gnu.org/packages/glpk-4.65

The information about your organization should be written within the spreadsheet files inside "Spreadsheets" directory. You can fill in the information that fits your organization according to the following rules:
1) For each date, a separate excel file (.xlsx) will the describe the full state of the organization. This file must have the filename format YYYY_MM_DD_main.xlsx, and it must contain at least two sheets: "Organization" and "Risk".
1) In the "Organization" and in the "Risk" sheets there should be an identical list of people.
2) In the "Organization" sheet you are only obliged to the first 4 columns storing the details of the person. The rest of the columns you can add as you wish. These columns are the departments of the organization. Use binary indicator to associate each person (row) with the departments the person visits.
3) In the "Risk" sheet you can add as many risk factors as you wish, and each person should have scores 0-5 for each one of the risk factors you defined.

# Usage
You can either run:
```
python COVID19-Toolkit.py
```
Or you can create an executable by following the instruction in "Pyhton to EXE instructions.txt".

Once you run the software you need to:
1) Choose a date for which the computation will be made. For that date the a file of the form Spreadsheet/date_main.xlsx will be loaded.
2) Choose a risk profile - this will determine how a person's risk (i.e. his/her probability of getting an infection) is computed based on his risk factors and based on his most recent test date.
3) Run the optimization for a desired range of test budgets (test budget is a number of people that can be tested in that day) - this initiates a separate optimization solution for each of the budgets. A graphical budget erxplorer will then pop up to show you how the risk is reduced as a function of tested people. Once you select the desired budget in the budget explorer - you can export the people that were selected for this budget to a checklist excel sheet.
4) Use the checklist to mark the people that were actually tested (mark a V sign next to their names)
5) (next day) Run the software again, the software will automatically *merge* the checklist and the main XLSX file of the previous day (creating a new XLSX file carrying the selected date) And then go to step (2).

# Assumptions
1) all the results are negative. Since if they were positive, a special protocol should be applied in the organization, which is beyond the scope of this software.


