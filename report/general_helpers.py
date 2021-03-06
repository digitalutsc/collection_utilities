import numpy as np
import pandas as pd
import os
import re
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import math
def DoesPIDExist(df, colValue):
    if len(df[df["PID"]==colValue].index.values) > 0:
        return True
    else:
        return False
def reshape_column_row(df, column_name, new_name):
    df_reshape = \
    (df.set_index(df.columns.drop(column_name,1).tolist())
       .loc[:, column_name].str.split(',', expand=True)
       .stack()
       .reset_index()
       .rename(columns={0:column_name})
       .loc[:, df.columns]
    )
    df_reshape.rename(columns={column_name:new_name}, inplace=True)
    return df_reshape
def GetMembers(df, df_collection_members, collection, b_include_pages):
    is_collection_member =  df['isMemberOfCollection'] == collection
    member_list = df[is_collection_member]
    
    if b_include_pages == True:
        is_part_of_book =  df['isPageOf'] == collection
        is_part_of_const = df['isConstituentOf'] == collection
        member_list_pages = df[is_part_of_book]
        member_list_const = df[is_part_of_const]
        member_list = member_list.append(member_list_pages,ignore_index=True)
        member_list = member_list.append(member_list_const,ignore_index=True)
        
    ## Loop through each member, if it is a collection model, then call this again!
    for index, row in member_list.iterrows():
        pid = row["PID"]
        cmodel = row["cmodel"]
        is_member_of_collection = row["isMemberOfCollection"]
        if cmodel == "info:fedora/islandora:bookCModel":
            df_collection_members = GetMembers(df, df_collection_members, "info:fedora/"+pid, b_include_pages)
        
    df_collection_members = df_collection_members.append(member_list,ignore_index=True)
    return df_collection_members

def ConvertCSVNameToName(string, regex, dictionary):
    name = re.search(regex, string).group(1).capitalize()+" "+re.search(regex, string).group(2)
    dictionary[string] = name
    return name

def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])

def GetSizeForCollection(df):
    df_datastreams_report = reshape_column_row(df, "size_list", "size")
    df_versions = reshape_column_row(df, "datastream_versions", "num_versions")
    df_datastreams_report["num_versions"] = df_versions["num_versions"]
    del df_datastreams_report["datastream_versions"]
    df_datastreams_report['size'] = df_datastreams_report['size'].apply(lambda x: x.strip())
    df_datastreams_report['size'].replace("not_set", '0', inplace=True)
    df_datastreams_report["size"].fillna(0, inplace = True) 
    df_datastreams_report = df_datastreams_report.astype({"size": np.int64})
    df_datastreams_report = df_datastreams_report.astype({"num_versions": np.int64})
    df_datastreams_report['total_size'] = df_datastreams_report['size'] * df_datastreams_report['num_versions']
    #print(df_datastreams_report.groupby(["isMemberOfCollection"])['total_size'].agg('sum').values[0])
    return df_datastreams_report['total_size'].sum()


