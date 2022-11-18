"""

Module with functions to:
- Update records of total schools count for each day the script is run on.
- Collate and track UDISE codes for each day the script is run on.

"""
import sys
sys.path.append('../')

import utilities.utilities as utilities
import utilities.file_utilities as file_utilities
import utilities.dbutilities as dbutilities

import pandas as pd
import os
from datetime import date
from pathlib import Path

def day_wise_school_count_tracking(master_file_name, sheet_name, df_today, group_levels, udise_col):
    """
    Function to track the number of schools at given grouping levels on the day the script is run.
    The day's count is updated in the master tracking excel file.

    Parameters:
    -----------
    master_file_name: str
        Name of the master file with schools count data
    sheet_name: str
        The name of the sheet with the day wise count of schools    
    df_today: DataFrame
        Data of school UDISE codes fetched today
    group_levels: str
        The columns in the data to group by (Eg: district/educational district/block)
    udise_col: str
        The name of the column in the sheet with UDISE values 
    """

    # Get the full file path to the master trends tracking file - assuming in generated reports folder
    master_file_path = os.path.join(file_utilities.get_gen_reports_dir_path(), master_file_name)

    # Group the data fetched for today by grouping level, counting the number of UDISE codes
    df_today_grouped = df_today.groupby(group_levels)[udise_col].count().reset_index()

    # Calculate and insert grand total of UDISE codes for the day
    df_today_grouped.loc['Grand Total'] = ['Grand Total', df_today_grouped[udise_col].sum()]

    # Rename the UDISE column with date + count string
    df_today_grouped.rename(columns={udise_col: utilities.get_today_date() + ' count'}, inplace=True)

    if(os.path.exists(master_file_path)):
        # If the file exists, update and save the data with today's count
        df_master = pd.read_excel(master_file_path, sheet_name=sheet_name)

        # Merge the data for the day with the master data
        df_master = df_master.merge(df_today_grouped)
    
    else:
        # If file doesnt exist, create data and save for day 1
        df_master = df_today_grouped
    return df_master



def day_wise_tracking(master_file_name, sheet_name, df_today, dist_col, udise_col):
    """
    Function to track the presence/absence of UDISE codes on the day the script is run.
    The function also updates the master tracking excel file with any new UDISE codes found.

    Parameters:
    -----------
    master_file_name: str
        Name of the master file with the day wise tracking of UDISE code
    sheet_name: str
        Name of the sheet with the data
    df_today: DataFrame
        Data of school UDISE codes fetched today
    dist_col: str
        The name of the column in the sheet with District names
    udise_col: str
        The name of the column in the sheet with UDISE values 
    Returns:
    -------
    DataFrame Object of UDISE sheet data updated with the days' UDISE code tracking

    """

    # Get the full file path to the master trends tracking file - assuming in generated reports folder
    master_file_path = os.path.join(file_utilities.get_gen_reports_dir_path(), master_file_name)
    # Get today's date
    today_date = utilities.get_today_date()

    # Update df_today to be the subset of district and UDISE columns
    df_today = df_today[dist_col, udise_col]

    # If file does not exist
    if not os.path.exists(master_file_path):
        # The master data will be today's data as there is no previous data
        df_master = df_today.copy()
        # Create a new column to mark the presence of all UDISes fetched today as TRUE
        df_master[today_date] = 'True'

    else:
        # Read the master data
        df_master = pd.read_excel(master_file_path, sheet_name=sheet_name)
        
        # Get a True/False series of all UDISES that are present in currently fetched data but not in master (True)
        udise_present_today_not_in_master = ~df_today[udise_col].isin(df_master[udise_col])
        df_new_UDISEs = df_today[udise_present_today_not_in_master].dropna()

        # Create a column in df_new_UDISEs marking all new UDISEs present today as TRUE
        df_new_UDISEs[today_date] = 'True'

        # Concatenate the new UDISES found for today with the master data, filling FALSE for previous days
        df_master = pd.concat([df_master, df_new_UDISEs], axis=0).fillna('False')

        # The concatenation of new UDISEs to the master data will mark the presence of rest of UDISES as FALSE
        # in the new column (with today's date)
        # This is updated by checking those UDISEs present both in master and today and marking them as TRUE
        df_master[today_date] = df_master[udise_col].isin(df_today[udise_col])

    # Rename the column with today's date
    df_master.rename(columns={today_date: today_date + ' present'}, inplace=True)
    # Sort the data
    df_master.sort_values(by=[dist_col, udise_col], ascending=[True, True], inplace=True)
    return df_master


def main():
    
    # Read the database connection credentials
    credentials_dict = dbutilities.read_conn_credentials('db_credentials.json')

    # Get the latest students and teachers count
    df_report = dbutilities.fetch_data_as_df(credentials_dict, 'students_school_child_count.sql')

    print('df_report fetched from db: ', df_report)


    # Alternatively
    # Ask the user to select the School enrollment abstract excel file.
    #school_enrollment_abstract = file_utilities.user_sel_excel_filename()
    #df_report = pd.read_excel(school_enrollment_abstract, sheet_name='Report')


    # Get a data frame updated with the latest school count
    df_school_count = day_wise_school_count_tracking('school_count_trends.xlsx', 'school_count_tracking', df_report,['District'],'UDISE_Code')

    # Get a data frame updated with latest UDISE tracking (present/absent)
    df_daywise_tracking = day_wise_tracking('school_count_trends.xlsx', 'daywise_UDISE_tracking', df_report, 'District', 'UDISE_Code')

    # Save the updated master data
    df_sheet_dict = {
        'school_count_tracking': df_school_count,
        'daywise_UDISE_tracking': df_daywise_tracking
        }
    file_utilities.save_to_excel(df_sheet_dict, 'school_count_trends.xlsx')


if __name__ == "__main__":
    main()