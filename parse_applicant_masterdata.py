#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 24 10:58:07 2017

@author: srikant
"""
import json
import sys
import os

import pandas as pd

import get_github_details as ghd
import get_stackoverflow_details as sod


MASTER_DIR = "master_data"
MASTER_FILE = "Applicant Master Data 2017.xlsx"
OUTPUT_FILE = MASTER_FILE.replace('Master', 'Github and Stackoverflow')

def read_master_data(filepath):
    '''Read Applicant Master Data,
    drop rows where either emailid or name is missing,
    return dataframe of master data.
    '''
    # read master appliant information
    try:
        master_df_raw = pd.read_excel(filepath, sheetname='Sheet1')
    except FileNotFoundError as err:
        print("\nCouldnt find '{}' \n".format(filepath))
        sys.exit(0)
    master_df_raw.columns = master_df_raw.columns.str.lower()
    # offset for consistency in row numbers
    offset = 2
    master_df_raw.index = master_df_raw.index + offset
    # drop rows where both names or emails are available
    name_and_email_available = master_df_raw['name'].notnull() & master_df_raw['email'].notnull()
    master_df = master_df_raw[name_and_email_available]
    return master_df


def write_df_to_excel(df, filepath):
    '''write df to excelfile in a proper order
    '''
    # order of columns for excel output
    cols_order = [
            'master_details',
            'github_id_details',
            'stackoverflow_id_details',
            'github_overall_rating',
            'stackoverflow_overall_rating',
            'github_expertise_ratings',
            'stackoverflow_expertise_ratings'
    ]
    # keep columns that are in df
    ordered_df_list = []
    for col_name in cols_order:
        try:
            ordered_df_list.append(df[[col_name]].sortlevel(axis=1))
        except (KeyError,IndexError):
            continue
    ordered_df = pd.concat(ordered_df_list, axis=1)
    # write dataframe to excel file
    ordered_df.to_excel(filepath, index_label='index')



def get_master_details(row):
    '''get a few id details from master data
    '''
    user_name = row['name']
    user_email = row['email'].split('|')[0]
    # applicant master details
    master_details_dict = {
            ('master_details','name'): user_name,
            ('master_details','email'): user_email
    }
    return master_details_dict

    
def get_github_details(g, user_name, user_email):
    '''get github details
    '''
    # search in Github for user matching the email_id
    search_string = user_email
    github_matches = ghd.find_matching_users(g, search_string)
    try:
        # get github data for the matching user
        github_details = ghd.get_github_profiles(github_matches, search_string)
    except SystemExit:
        github_details = {}
    # get the github ratings df
    github_ratings_df = github_details.get(search_string,{}).get('overall_rating', pd.DataFrame())
    # convert df to dict
    github_ratings_dict = github_ratings_df.to_dict().get('value',{})
    return github_ratings_dict


def get_stackoverflow_details(so, user_name, user_email):
    '''get stackoverflow details
    '''
    # use fullname as search string
    search_string = user_name
    search_kw = {'inname':search_string}
    # find matching stackoverflow users, use the first match
    stackovf_matches = sod.find_matching_users(so, search_kw)[0:1]
    try:
        # get stackoverflow details for the first user
        stackovf_details = sod.get_stackoverflow_profiles(stackovf_matches, search_kw)
    except SystemExit:
        stackovf_details = {}
    # get statckoverflow ratings df
    stackovf_ratings_df = stackovf_details.get(search_string,{}).get('ratings_df', pd.DataFrame())
    # convert df to dict
    stackovf_ratings_dict = stackovf_ratings_df.to_dict().get('value',{})
    return stackovf_ratings_dict


def get_github_stackorf_details(g, so, master_data_df):
    '''get github and stackoverflow details for each of the applicant in the master_data_df
    '''
    all_details_dict = {}
    master_details_dict = {}
    github_ratings_dict = {}
    stackovf_ratings_dict = {}
    ratings_dict = {}
    # for each applicant get Github, Stackoverflow and Master Data, do this for all applicants
    for i,row in master_data_df.iterrows():
        print('\nSl.No {:3d}: [{}], [{}]'.format(i, row['name'], row['email']) )
        # applicant master details
        master_details_dict[i] = get_master_details(row)
        user_name = master_details_dict[i].get(('master_details','name'),'')
        user_email = master_details_dict[i].get(('master_details','email'),'')
        # search in Github for user matching the email_id
        github_ratings_dict[i] = get_github_details(g, user_name, user_email)
        # search in Stackoverflow for user matching the user_name
        stackovf_ratings_dict[i] = get_stackoverflow_details(so, user_name, user_email)
        # append all ratings df to applicant master details
        ratings_dict[i] = {
                **master_details_dict[i],
                **github_ratings_dict[i],
                **stackovf_ratings_dict[i]
        }
    # dictionary of combined as well as individual ratings
    all_details_dict = {
            'ratings_dict': ratings_dict,
            'master_details_dict': master_details_dict,
            'github_ratings_dict': github_ratings_dict,
            'stackovf_ratings_dict': stackovf_ratings_dict
    }
    return all_details_dict


if __name__ == '__main__':
    # read master data from excel file
    master_data_df = read_master_data(filepath = os.path.join(MASTER_DIR, MASTER_FILE))
    # initialize github object
    g = ghd.init_github_object()
    # initialize stackoverflow object
    so = sod.init_stackoverflow_object()
    # get applicant github stackoverflow data
    sample = True
    if sample:
        data_df = master_data_df.sample(10)
        suffix = "Sample "
    else:
        data_df = master_data_df
        suffix = ""
    all_details_dict = get_github_stackorf_details(g, so, data_df)
    ratings_details = all_details_dict['ratings_dict']
    # convert dict of all applicant details to a dataframe
    applicants_df = pd.DataFrame.from_dict(ratings_details, orient='index')
    # write to excel file
    output_file = os.path.join(MASTER_DIR, suffix + OUTPUT_FILE)
    write_df_to_excel(applicants_df, output_file)
