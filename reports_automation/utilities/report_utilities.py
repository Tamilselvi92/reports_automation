"""
Module with utility functions that can be commonly used for different reports.
"""

import pandas as pd
#import reports_automation.ceo_reports.ranking as ranking
import os
import utilities.file_utilities as file_utilities
import utilities.ranking_utilities as ranking_utilities
import utilities.column_names_utilities as cols

from enums.combine_data_types import CombineDataTypes as combine_data_types

brc_file_name = 'BRC_CRC_Master_V3.xlsx'
brc_master_sheet_name = 'BRC-CRC V3 wo hyphen'

# Columns to be dropped from the BRC mapping sheet
brc_master_drop_cols = ['CRC Udise','CRC School Name', 'BRTE']

# Define the list of columns to group by for rankings
beo_ranking_group_cols = [cols.beo_user, cols.beo_name]
deo_elem_ranking_group_cols = [cols.deo_name_elm]
deo_secnd_ranking_group_cols = [cols.deo_name_sec]


def map_data_with_brc(raw_data, merge_dict):
    """
    Function to map the raw data with BRC CRC mapping. The join is done on
    school UDISE values.

    Parameters
    ----------
    raw_data: Pandas DataFrame
        The raw data to be updated with brc-crc mapping
    merge_dict: dict
        A merge param - merge param value key-value pair to be used to specify the type of merging
        Eg: merge_dict = {
            'on_values' : ['district', 'block','school_name', 'school_category', 'udise_col'],
            'how' : 'outer'
        }

    Returns
    -------
    DataFrame object of given data updated with BRc-CRC mapping
    """

    brc_master_sheet = get_brc_master()
    brc_master_sheet = brc_master_sheet.drop(brc_master_drop_cols, axis=1)
    report_summary = pd.merge(raw_data, brc_master_sheet,on=merge_dict['join_on'],how=merge_dict['merge_type'])
    
    # Rearrage the columns so that DEO and BEO information comes at the begining of the data
    # Define rearranged order of columns
    list_of_cols = [cols.district_name] + [cols.deo_name_sec, cols.deo_name_elm, cols.beo_user, cols.beo_name, cols.school_level, cols.school_category]\
                     +  raw_data.columns.to_list()

    # Get the unique list of columns in the same order
    list_of_cols = pd.unique(pd.Series(list_of_cols)).tolist()

    report_summary = report_summary.reindex(columns=list_of_cols)

    return report_summary

def get_brc_master(sheet_name=brc_master_sheet_name):
    """
    This function would return the master brc-crc file that would be required for merging with the raw data required
    in all other reports- CEO review or otherwise.
    sheet_name: str
        Name of the sheet to read from BRC Master. Default is brc_master_sheet_name.

    Returns:
    -------
    DataFrame object of the BRC-CRC mapping data
    """
    mapping_data_dir = file_utilities.get_mapping_data_dir_path()
    # read from excel, get sub columns
    brc_mapping_file_path = os.path.join(mapping_data_dir, brc_file_name)
    brc_master = pd.read_excel(brc_mapping_file_path,sheet_name=sheet_name)

    return brc_master


def get_elem_ranked_report(df_summary, ranking_args_dict, metric_code, metric_category):

    """
    Function create and return the elementary ranked report on given data by calculating
    the BEO ranking, DEO(Elementary) ranking and updating the data.

    The master ranking data is also updated when this function is called.

    Parameters: 
    -----------

    df_summary: Pandas DataFrame
        The raw processed, summarised and ready for ranking
    ranking_args_dict: dict
        A dictionary of parameter name - parameter value key-value pairs to be used for calculating the rank
        Eg: ranking_args_dict = {
        ranking_type' : 'percent_ranking',
        'agg_dict': {'schools' : 'count', 'students screened' : 'sum'},
        'ranking_val_desc' : '% moved to CP',
        'num_col' : 'class_1',
        'den_col' : 'Total',
        'sort' : True, 
        'ascending' : False
        }
    metric_code: str
        The code of the metric on which the data is ranked
    metric_category: str
        The category of the metric on which the data is ranked
    """

    # If the data is at school level, filter the data to Elementary school type
    if (any(cols.school_level in col_name for col_name in df_summary.columns.to_list())):
        df_summary = df_summary[df_summary[cols.school_level].isin([cols.elem_schl_lvl])]
        # Drop the school level column as it will no longer be needed
        df_summary.drop(columns=[cols.school_level],axis=1, inplace=True)                     

    # Get the ranking for the BEOs
    #beo_ranking = ranking_utilities.calc_ranking(df_summary, beo_ranking_group_cols, ranking_args_dict)

    # Make a copy of the ranking to update master sheet
    #beo_ranking_for_master = beo_ranking.copy()

    # Update the BEO ranked data with designation
    #beo_ranking_for_master[cols.desig] = 'BEO'

    # Rename the BEO name column
    #beo_ranking_for_master.rename(columns={cols.beo_name: cols.name, cols.district_name: cols.district}, inplace = True)

    # Update the master ranking with the BEO ranking
    #ranking_utilities.update_ranking_master(beo_ranking_for_master, metric_code, metric_category, 'Elementary')


    deo_elm_ranking = ranking_utilities.calc_ranking(df_summary, deo_elem_ranking_group_cols, ranking_args_dict)



    # Make a copy of the ranking to update master sheet
    deo_elm_ranking_for_master = deo_elm_ranking.copy()

    # Update the DEO ranked data with designation
    deo_elm_ranking_for_master[cols.desig] = 'DEO'

    # Rename the DEO name column
    deo_elm_ranking_for_master.rename(columns={cols.deo_name_elm: cols.name}, inplace = True)

    # Update the master ranking with the BEO ranking
    ranking_utilities.update_ranking_master(deo_elm_ranking_for_master, metric_code, metric_category, 'Elementary')

    # Merge the data with the ranks

    # Take only subset columns of BEO ranked data
    #beo_ranking = beo_ranking[[cols.beo_user, cols.beo_name, cols.rank_col]]
    # Rename the rank column
    #beo_ranking.rename(columns={cols.rank_col: cols.beo_rank}, inplace=True)

    # Take only subset columns of DEO ranked data
    deo_elm_ranking = deo_elm_ranking[[cols.deo_name_elm, cols.rank_col]]
    # Rename the rank column
    deo_elm_ranking.rename(columns={cols.rank_col: cols.deo_elem_rank}, inplace=True)

    # Since the ranking values will be grouped to beo level, the ranking values of each individual row
    # of data before being grouped and ranked is missed. That data will be more useful for review.
    # That data is inserted here. Not a clean way of doing things. Yes.
    data_level_ranking = ranking_utilities.calc_ranking(df_summary, deo_elem_ranking_group_cols + [cols.block_name], ranking_args_dict)

    # Drop the ranking value and ranking description column
    data_level_ranking.drop(columns={cols.rank_col, cols.ranking_value_desc}, inplace=True)


    # Add the data level ranking value
    #elementary_report = pd.merge(df_summary, data_level_ranking[[cols.deo_name_elm, \
                #cols.school_category, cols.ranking_value]], on=[cols.school_category, cols.deo_name_elm])
    #elementary_report = pd.merge(elementary_report, beo_ranking, on=[cols.beo_user, cols.beo_name])
    #elementary_report = pd.merge(elementary_report, deo_elm_ranking, on=[cols.deo_name_elm])
    

    # Replace the two lines below with the three lines above when beo ranking is enabled
    # Add the data level ranking value
    elementary_report = pd.merge(df_summary, data_level_ranking[[cols.block_name, cols.deo_name_elm, \
            cols.ranking_value]], on=[cols.deo_name_elm, cols.block_name])

    elementary_report = pd.merge(elementary_report, deo_elm_ranking, on=[cols.deo_name_elm])
    

    # Rename the name of the column: ranking value to description of the ranking value
    elementary_report.rename(columns = {cols.ranking_value: ranking_args_dict['ranking_val_desc']}, inplace=True)

    # Sort the data by district and rank
    #elementary_report.sort_values(by=[cols.deo_elem_rank, cols.deo_name_elm, cols.beo_rank], ascending=True, inplace=True)
    # Replace the line above with the line below when beo ranking is done
    elementary_report.sort_values(by=[cols.deo_elem_rank, cols.deo_name_elm], ascending=True, inplace=True)


    # Drop duplicate columns
    elementary_report = elementary_report.T.drop_duplicates().T

    return elementary_report


def get_sec_ranked_report(df_summary, ranking_args_dict, metric_code, metric_category):
    """
    Function create and return the ranked secondary report on given data by calculating
    the DEO (Secondary) ranking and updating the data.

    The master ranking data is also updated when this function is called.

    Parameters: 
    -----------

    df_summary: Pandas DataFrame
        The raw processed, summarised and ready for ranking
    ranking_args_dict: dict
        A dictionary of parameter name - parameter value key-value pairs to be used for calculating the rank
        Eg: ranking_args_dict = {
        ranking_type' : 'percent_ranking',
        'agg_dict': {'schools' : 'count', 'students screened' : 'sum'},
        'ranking_val_desc' : '% moved to CP',
        'num_col' : 'class_1',
        'den_col' : 'Total',
        'sort' : True, 
        'ascending' : False
        }
    metric_code: str
        The code of the metric on which the data is ranked
    metric_category: str
        The category of the metric on which the data is ranked
    """

    # If the data is at school level, filter the data to Secondary school type
    if (any(cols.school_level in col_name for col_name in df_summary.columns.to_list())):
        df_summary = df_summary[df_summary[cols.school_level].isin([cols.scnd_schl_lvl])]
        # Drop the school level column as it will no longer be needed
        df_summary.drop(columns=[cols.school_level], inplace=True)

    # Get the ranking for the secondary DEOs
    deo_sec_ranking = ranking_utilities.calc_ranking(df_summary, deo_secnd_ranking_group_cols, ranking_args_dict)

    # Make a copy of the ranking to update master sheet
    deo_sec_ranking_for_master = deo_sec_ranking.copy()

    # Update the DEO ranked data with designation
    deo_sec_ranking_for_master[cols.desig] = 'DEO'

    # Rename the DEO name column
    deo_sec_ranking_for_master.rename(columns={cols.deo_name_sec: cols.name, cols.district_name: cols.district}, inplace = True)

    # Update the master ranking with the DEOs ranking
    ranking_utilities.update_ranking_master(deo_sec_ranking_for_master, metric_code, metric_category, 'Secondary')

    #secondary_report = pd.append([report_summary, deo_sec_ranking], axis=1)

    # Take only subset columns of DEO ranked data
    deo_sec_ranking = deo_sec_ranking[[cols.deo_name_sec, cols.rank_col]]
    # Rename the rank column
    deo_sec_ranking.rename(columns={cols.rank_col: cols.deo_sec_rank}, inplace=True)

    # Since the ranking values will be grouped to DEO level, the ranking values of each individual row
    # of data before being grouped and ranked is missed. That data will be more useful for review.
    # That data is inserted here. Not a clean way of doing things. Yes.
    data_level_ranking = ranking_utilities.calc_ranking(df_summary, deo_secnd_ranking_group_cols + [cols.block_name], ranking_args_dict)


    # Add the data level ranking value
    secondary_report = pd.merge(df_summary, data_level_ranking[[cols.block_name, cols.deo_name_sec, cols.ranking_value]],\
                                 on=[cols.deo_name_sec, cols.block_name])

    # Rename the name of the column: ranking value to description of the ranking value
    secondary_report.rename(columns = {cols.ranking_value: ranking_args_dict['ranking_val_desc']}, inplace=True)

    # Add the DEO level ranks
    secondary_report = pd.merge(secondary_report, deo_sec_ranking, on=[cols.deo_name_sec])

    # Sort the data by district and rank
    secondary_report.sort_values(by=[cols.deo_sec_rank, cols.deo_name_sec], ascending=True, inplace=True)

    # Drop duplicate columns
    secondary_report = secondary_report.T.drop_duplicates().T

    return secondary_report



def combine_multiple_datasets(df_data_set:dict, combine_type:str, combine_data_configs:dict):
    """ 
    Function to combine multiple datasets into a single data frame object.

    Parameters:
    -----------
    df_data_set: dict
        Dictionary of datasets with the keys being the name of the data and value being the data
    combine_data_configs: dict
        Dictionary of configurations to combine the data on 

    Returns: Pandas DataFrame
        The combined data as a single dataframe object
    """

    if combine_type == combine_data_types.MERGE.value:
        # Merge the data

        # Initially set the merged data to the primary data
        df_combined = df_data_set['primary_data']

        for key in combine_data_configs.keys():
            # Get the merge config
            merge_config = combine_data_configs[key]
            # Get the data for the key in merge config and merge it
            df_combined = df_combined.merge(df_data_set[key], how=merge_config['merge_type'], on=merge_config['join_on'])

    elif combine_type == combine_data_types.CONCAT.value:
        # Concatenate the data

        # Initially set the merged data to empty dataframe object
        df_combined = pd.DataFrame()
        for key in combine_data_configs.keys():
            # Get the concatenation config
            concat_config = combine_data_configs[key]
            # Get the data for the key in concat config and concatenate it
            df_combined = pd.concat([df_combined, df_data_set[key]], join=concat_config['join']) 

    return df_combined

