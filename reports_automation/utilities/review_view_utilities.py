"""
Module with utility functions to format the reports for reviews

The module will call the following utilities:
    - subtotal_utilities, to subtotal the data at different levels
    - outlines_utilities to apply Excel outlines on the data
    - format_utilities to apply different formatting styles on the data
"""

import os
import sys
sys.path.append('../')

import pandas as pd
import numpy as np
import utilities.file_utilities as file_utilities
import utilities.subtotal_utilities as subtotal_utilities
import utilities.outlines_utilities as outlines_utilities
import utilities.format_utilities as format_utilities
import utilities.column_names_utilities as cols

import xlsxwriter

from datetime import datetime

def prepare_report_for_review(df, format_config, ranking_args_dict, sheet_name, file_name, dir_path):
    """
    Function to prepare the final report for viewing by:
        - computing subtotals
        - Applying Excel outlines
        - formatting the data
        - Saving the data
    Parameters:
    ----------
    df: Pandas DataFrame
        The report data that needs to be prepared
    format_config: dict
        A dictionary of format configuration to be used for computing subtotals, applying outlines and formatting
        Eg: "format_config" : {
                "subtotal_outlines_dict" : {
                    "level_subtotal_cols_dict" : {"1" : "cols.deo_name_sec"},
                    "agg_cols_func_dict" : {
                        "cols.cwsn_tot": "sum",
                        "cols.nid_count": "sum",
                        "cols.udid_count": "sum",
                        "cols.deo_sec_rank": "mean"
                    },
                    "text_append_dict" : {"cols.deo_name_sec": "Summary"}
                },
                "format_dict" : {
                    "conditional_format" : {
                        "columns" : ["cols.perc_fully_mapped"],
                        "format": {"type": "3_color_scale"}
                    },
                    "format_cells" : {
                        "columns" : ["cols.perc_fully_mapped"],
                        "format" : {"num_format": "0.00%"}
        
                    }
                }
            }
    ranking_args_dict: dict
        A dictionary of parameter name - parameter value key-value pairs to be used for calculating the rank
        Eg: ranking_args_dict = {
        'group_levels' : ['district', 'name', 'designation'],
        'agg_dict': {'schools' : 'count', 'students screened' : 'sum'},
        'ranking_val_desc' : '% moved to CP',
        'num_col' : 'class_1',
        'den_col' : 'Total',
        'sort' : True, 
        'ascending' : False
        }
    sheet_name: str
        The name of the sheet to save the data in.
    file_name: str
        The name of the file to save the data sheet in.
    dir_path: str
        The directory in which to save the file in.
    """

    # Get the subtotal and outlines specific configurations
    subtotal_outlines_dict = _update_subtotal_outlines_dict(format_config['subtotal_outlines_dict'])
    level_subtotal_cols_dict = subtotal_outlines_dict['level_subtotal_cols_dict']
    agg_cols_func_dict = subtotal_outlines_dict['agg_cols_func_dict']
    text_append_dict = subtotal_outlines_dict['text_append_dict']

    # Compute sub-totals and insert into provided dataframe
    subtotals_result_dict = subtotal_utilities.compute_insert_subtotals(df, format_config, ranking_args_dict)

    # Get the updated DataFrame object - with the subtotals inserted
    updated_df = subtotals_result_dict['updated_df']
    # Get only the subtotal rows
    df_subtotal_rows = subtotals_result_dict['subtotals']

    # Get and update the data frame with a grand total row at the bottom of the data set  
    grand_total_row = _get_grand_total_row(df, ranking_args_dict)
    print('grand_total_row: ', grand_total_row)
    updated_df.loc['Grand Total'] = grand_total_row
    

    # Remove rank for rows other than subtotal rows - commented as this needs to be fixed
    #appended_col = list(text_append_dict.keys())[0]
    #if (appended_col == cols.deo_name_elm):
        #updated_df[~updated_df[appended_col].str.contains(text_append_dict[appended_col])][cols.deo_elem_rank] = ''
        #updated_df.loc[updated_df[~updated_df[appended_col].str.contains(text_append_dict[appended_col])] == True][cols.deo_elem_rank] = ''
        #updated_df[cols.deo_elem_rank] = np.where(~updated_df[appended_col].str.contains(text_append_dict[appended_col]), '', updated_df[cols.deo_elem_rank])

    # Build outlines levels and ranges dictionary
    level_outline_ranges_dict = outlines_utilities.build_level_outline_ranges_dict(
        updated_df, df_subtotal_rows, level_subtotal_cols_dict, agg_cols_func_dict)

    
    # Shift the data by 1 row down - To create space for report heading
    df = df.shift(periods=1, fill_value=0)

    # Extracting the column names for renaming
    col_names = updated_df.columns.to_list()
    # Checking if the report is elementary or secondary
    if col_names[0] == cols.deo_name_elm:
        updated_df.rename(columns={
            cols.deo_name_elm: cols.deo_name_elementary,
            cols.block_name: cols.block_name_output
        }, inplace=True
        )
    elif col_names[0] == cols.deo_name_sec:
        updated_df.rename(columns={
            cols.deo_name_sec: cols.deo_name_secondary,
            cols.block_name: cols.block_name_output
        }, inplace=True
        )

    # Update any other column names given to be renamed
    if 'columns_rename_dict' in format_config and bool(format_config['columns_rename_dict']):
        
        columns_rename_dict = cols.update_dictionary(format_config['columns_rename_dict'])
        updated_df.rename(columns=columns_rename_dict, inplace=True)

    # Drop any columns configured to be dropped
    if 'columns_to_drop' in format_config and bool(format_config['columns_to_drop']):
        cols_to_drop = cols.get_values(format_config['columns_to_drop'])
        updated_df.drop(columns=cols_to_drop, inplace=True)


    # Correspondingly update the outline ranges as data has been shifted down
    level_outline_ranges_dict = outlines_utilities.push_outline_ranges_for_formatting(level_outline_ranges_dict, 1)

    # Get the XlsxWriter object
    writer = file_utilities.get_xlsxwriter_obj({sheet_name: updated_df}, file_name, file_path=dir_path)

    # Get a XlsxWriter workbook and worksheet object
    workbook = writer.book
    worksheet = workbook.get_worksheet_by_name(sheet_name)
    
    # Apply the outlines function to the work sheet for the given levels and ranges
    outlines_utilities.apply_outlines(worksheet, level_outline_ranges_dict)

    # Insert heading
    # Get the heading to be inserted
    heading = format_config['heading']
    date = datetime.now().strftime('%d %h %y')
    full_heading = heading + ' - ' + date
    format_utilities.insert_heading(updated_df, full_heading, worksheet, workbook)

    # Apply border to the entire data
    format_utilities.apply_border(updated_df, worksheet, workbook)

    # Apply formatting for columns as specified in the JSON configuration
    format_dicts_list = format_config['format_dicts']
    format_utilities.apply_formatting(format_dicts_list, updated_df, worksheet, workbook)

    # Apply formatting to the subtotal rows
    subtotal_row_indices = subtotals_result_dict['subtotal_row_indices']
    subtotal_utilities.format_subtotal_rows(worksheet, workbook, updated_df, subtotal_row_indices)

    # correct the formatting loss from applying subtotal row formatting
    subtotal_utilities.correct_col_formatting_loss(worksheet, workbook, updated_df, subtotal_row_indices, format_dicts_list)

    # Format the grand total row
    _format_grand_total_row(worksheet, workbook, updated_df)

    # correct the formatting loss in grand total row from applying grand total row formatting
    _correct_grand_total_col_frmt_loss(worksheet, workbook, updated_df, format_dicts_list)

    # Format the header
    format_utilities.format_col_header(updated_df, worksheet, workbook)

    # Save the formatted data
    writer.close()




def _update_subtotal_outlines_dict(subtotal_outlines_dict:dict):
    """
    Internal function to update subtotal outline dict keys and values.
    
    When JSON configuration with variable keys and variable values are read
    as a dict, the variable resolution does not manually happen. 
    
    This utility function resolves the keys and values in the subtotal outlines dict
    
    Parameters:
    -----------
    subtotal_outlines_dict: dict
        The subtotal and outlines configuration dictionary fetched from JSON
    
    Returns:
    --------
    The updated subtotal outlines dictionary
    """

    # Update the subtotal level values
    level_subtotal_cols_dict = subtotal_outlines_dict['level_subtotal_cols_dict']
    for key in level_subtotal_cols_dict.keys():
        var_val = level_subtotal_cols_dict[key]
        updated_val = cols.get_value(var_val)
        level_subtotal_cols_dict[key] = updated_val

    # Update the aggregate columns function dictionary
    updated_agg_cols_func_dict = cols.update_dictionary_var_strs(subtotal_outlines_dict['agg_cols_func_dict'])
    subtotal_outlines_dict['agg_cols_func_dict'] = updated_agg_cols_func_dict

    # Update text append dict
    updated_text_append_dict = cols.update_dictionary_var_strs(subtotal_outlines_dict['text_append_dict'])
    subtotal_outlines_dict['text_append_dict'] = updated_text_append_dict

    return subtotal_outlines_dict
    

def _get_grand_total_row(df, ranking_args_dict):
    """
    Internal function to create a grand total row to insert at the bottom of the data set.

    Parameters:
    ----------
    df: Pandas DataFrame
        The data for which a grand total row has to be created
    ranking_args_dict: dict
        The ranking arguments dictionary that is reused to get the columns and aggregate functions
        to calculate the grand total

    Returns:
    -------
    The grand total row to insert
    """
    # Get the aggregate dictionary
    agg_dict = ranking_args_dict['agg_dict']
    no_of_columns = len(df.columns.to_list())
    
    # First set first cell as grand total and all cells in row to empty string. 
    grand_total_row = []
    for i in range(0, no_of_columns - 1):
        if i == 0:
            grand_total_row.append('Grand Total')
        # Set all other cells to blank
        grand_total_row.append('')
    
    # Then update specific cells present in agg_dict
    for key in agg_dict.keys():
        agg_func = agg_dict[key]
        if agg_func == 'sum':
            cell_total = df[key].sum()
        elif agg_func == 'mean':
            cell_total = df[key].mean()
        elif agg_func == 'count':
            cell_total = df[key].count()
        elif agg_func == 'median':
            cell_total = df[key].median()
        
        # Update the cell value for this column in grand total row
        grand_total_row[df.columns.get_loc(key)] = cell_total

    # Add the ranking value average to the row
    ranking_val_desc_col  = ranking_args_dict['ranking_val_desc']
    grand_total_row[df.columns.get_loc(ranking_val_desc_col)] = df[ranking_val_desc_col].mean()

    return grand_total_row


def _format_grand_total_row(worksheet, workbook, df):
    """
    Internal helper function to format the Grand total row which will be the last row
    in the data

    Parameters:
    -----------
    worksheet: Worksheet
        An XlsxWriter worksheet object
    workbook: Workbook
        An XlsxWriter workbook object
    df: DataFrame
        The data containing the grand total row at the end
    """

    # Get the index of the last row
    row_index = df.shape[0]

    # Define the formatting to apply for all subtotal rows
    cell_format = workbook.add_format()
    # Set the subtotal rows to bold
    cell_format.set_bold() 
    # Set the subtotal row background to grey
    cell_format.set_bg_color('#a9a8a8')
    # Set the border for the subtotal row
    cell_format.set_border(1)
    # Set the alignment of the text
    cell_format.set_align('center')

    # Rewrite the grand total, but with formatting
    # Add 1 to row index location as report heading will have been inserted at the top
    worksheet.write_row(row_index+1, 0, df.iloc[row_index - 1], cell_format)


def _correct_grand_total_col_frmt_loss(worksheet, workbook, df, format_dicts_list):
    """
    Helper function to re-apply the column formatting previously applied
    and lost when the subtatol row is formatted.

    Parameters:
    ----------
    worksheet: Worksheet
        An XlsxWriter worksheet object
    workbook: Workbook
        An XlsxWriter workbook object
    df: DataFrame
        The data containing the grand total row at the end
    format_dicts_list: list
        List of dictionaries where each dictionary item contains list of columns to apply a formatting on
    """

    # Get the index of the last row
    row_index = df.shape[0]

    for format_dict in format_dicts_list:
    
        # Get the column name variables
        columns = format_dict['columns']
        # Get the resolved column name values
        columns = cols.get_values(columns)

        format = format_dict['format']

        # update format with the cell format
        #format.update(cell_format)
        cell_format = workbook.add_format(format)

        # Add the cell formats that were applied in subtotaling
        
        # Set the subtotal rows to bold
        cell_format.set_bold() 
        # Set the subtotal row background to grey
        cell_format.set_bg_color('#a9a8a8')
        # Set the border for the subtotal row
        cell_format.set_border(1)
        # Set the alignment of the text
        cell_format.set_align('center')

        # For each column
        for column in columns:
            
            col_index = df.columns.get_loc(column)
            # Rewrite the grand total row columns with lost formatting
            # Add 1 to row index location as report heading will have been inserted at the top
            worksheet.write(row_index+1, col_index, df.iloc[row_index-1, col_index], cell_format)
