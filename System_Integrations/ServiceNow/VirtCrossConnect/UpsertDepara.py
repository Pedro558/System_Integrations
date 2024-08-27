import re, os
import pandas as pd
from unidecode import unidecode
from commons.pandas.utils import *

from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from dotenv import load_dotenv

load_dotenv(override=True)

url_snow = os.getenv("snow_url")

servicenow_client_id = os.getenv("snow_client_id") #get_api_token('servicenow-prd-client-id-oauth')
servicenow_client_secret = os.getenv("snow_client_secret") #get_api_token('servicenow-prd-client-secret-oauth')
service_now_refresh_token = os.getenv("snow_refresh_token") #get_api_token('servicenow-prd-refresh-token-oauth')

token = get_servicenow_auth_token(url_snow, servicenow_client_id, servicenow_client_secret, service_now_refresh_token)

sites = ["RJO1", "SPO1", "POA1", "CTA1", "BSB1", "BSB2"]
path = "C:/Users/filipe.uccelli/source/System_Integration/System_Integrations/ServiceNow/VirtCrossConnect/"
pathImports = f"{path}import/"
columns_to_extract = ["CROSS ID", "Data "]
# df_dh_depara = pd.read_excel(f"{path}De_Para Data Hall.xlsx")

def remove_site_prefix(value:str, sites):
    if not isinstance(value, str): return value

    sites_aux = sites + ["BSB1", "POA2", "SPO"]
    sites_options = "|".join(sites_aux)
    pattern = rf"^({sites_options})-(\d+|T|SS|SL)?-?"
    # pattern = rf"^({sites_options})-(\d+|T|SS|SL)-"

    new_value = value
    # if value.startswith(f"{site}-"): new_value = value.replace(f"{site}-", "")
    match = re.match(pattern, value)
    if match:
        new_value = re.sub(pattern, "", value)

    return new_value

def merge_de_para(df, lookup):
    # merged_df = df.merge(lookup, on=['Site', 'De'], how='left', suffixes=('', '_new'))
    # merged_df = merged_df.drop_duplicates(subset=['Site', 'De', "Para_new"])
    # merged_df = merged_df.reset_index()
    # merged_df['Para'] = merged_df['Para_new'].combine_first(df['Para'])
    # return merged_df[["Site", "De", "Para"]]
    merged_right = df.merge(lookup, on=['Site', 'De'], how='right', suffixes=('', '_new'))
    merged_right['Para'] = merged_right['Para_new'].combine_first(merged_right['Para'])
    final_merged = df.merge(merged_right, on=['Site', 'De'], how='outer', suffixes=('', '_final'))
    final_merged['Para'] = final_merged['Para_final'].combine_first(final_merged['Para'])
    final_merged = final_merged.drop_duplicates(subset=['Site', 'De', "Para"])
    # breakpoint()
    return final_merged[["Site", "De", "Para"]]
     

dataframes = []
for site in sites:
    df = get_df_from_excel(f"{pathImports}{site}/cross_{site}_data.xlsx")
    df["Site"] = site
    dataframes.append(df)

# ===
# Custoemer
# ===
lookup_customer = get_df_from_excel(f"{pathImports}_lookups/de_para_customer.xlsx", {"De": [], "Para": []})
df = combine_data(dataframes, ["Site", "Cliente Ponta A", "Cliente Ponta B", "Cliente Final"])
dict_df = {"Site": [], "De": [], "Para": []}
for row in df.iterrows():
    dict_df["Site"].append(row[1]["Site"])
    dict_df["De"].append(row[1]["Cliente Ponta A"])
    dict_df["Para"].append(None)

    dict_df["Site"].append(row[1]["Site"])
    dict_df["De"].append(row[1]["Cliente Ponta B"])
    dict_df["Para"].append(None)

    dict_df["Site"].append(row[1]["Site"])
    dict_df["De"].append(row[1]["Cliente Final"])
    dict_df["Para"].append(None)

df = pd.DataFrame(dict_df)

snow_accounts = get_servicenow_table_data(url_snow, "customer_account", {}, token)
snow_accounts_names = [x["name"] for x in snow_accounts]

# combined_lookup_customers = combine_data([df, lookup_customer], ["Site", "De", "Para"])
if not lookup_customer.empty:
    merged_right = df.merge(lookup_customer, on=['Site', 'De'], how='right', suffixes=('', '_new'))
    merged_right['Para'] = merged_right['Para_new'].combine_first(merged_right['Para'])
    final_merged = df.merge(merged_right, on=['Site', 'De'], how='outer', suffixes=('', '_final'))
    final_merged['Para'] = final_merged['Para_final'].combine_first(final_merged['Para'])
    final_merged = final_merged.drop_duplicates(subset=['Site', 'De', "Para"])
    df = final_merged[["Site", "De", "Para"]]



combined_lookup_customers = df
combined_lookup_customers["De"] = combined_lookup_customers["De"].str.strip()
combined_lookup_customers.dropna(subset=['De'])
# combined_lookup_customers["De"] = combined_lookup_customers["De"].apply(remove_acento)
combined_lookup_customers = combined_lookup_customers.drop_duplicates(subset=['Site', 'De', "Para"])
rows_to_delete = combined_lookup_customers['De'].isin(snow_accounts_names)
combined_lookup_customers = combined_lookup_customers[~rows_to_delete]
combined_lookup_customers.to_excel(path+"de_para_customer.xlsx", index=False)



# ===
# Data Hall
# ===
columns_with_data_hall = ["Site", "Data Hall", "Data Hall Ponta B", "Salto 1", "Salto 2", "Salto 3", "Salto 4", "Salto 5"]
df = combine_data(dataframes, columns_with_data_hall)
dict_df = {"Site": [], "De": [], "Para": []}
for row in df.iterrows():
    for column in columns_with_data_hall:
        value = None
        if column in ["Site"]:
            pass
        elif column in ["Data Hall", "Data Hall Ponta B"]:
            value = row[1][column]
        else: # Saltos
            try:
                parts = row[1][column].split(":")
                if len(parts) != 4: raise Exception() # this does not followed correct pattern
                value = parts[0]
            except:
                pass
        
        if value:
            dict_df["Site"].append(row[1]["Site"])
            dict_df["De"].append(value)
            dict_df["Para"].append(None)

df = pd.DataFrame(dict_df)

snow_data_halls = get_servicenow_table_data(url_snow, "u_cmdb_ci_data_hall", {"sysparm_display_value": True}, token)
dict_dh_df = {"Site": [], "De": [], "Para": []}
for dh in snow_data_halls:
    dict_dh_df["Site"].append(get_value(dh, lambda dh: dh["u_site"]["display_value"], None))
    dict_dh_df["De"].append(dh["name"])
    dict_dh_df["Para"].append(None)


lookup_data_hall = get_df_from_excel(f"{pathImports}_lookups/de_para_data_hall.xlsx", {"De": [], "Para": []})
lookup_data_hall["De"] = lookup_data_hall["De"].apply(lambda value: remove_site_prefix(value, sites))

if not lookup_data_hall.empty:
    df = merge_de_para(df, lookup_data_hall)
    # merged_df = df.merge(lookup_data_hall, on=['Site', 'De'], how='left', suffixes=('', '_new'))
    # merged_df = merged_df.drop_duplicates(subset=['Site', 'De', "Para_new"])
    # merged_df = merged_df.reset_index()
    # merged_df['Para'] = merged_df['Para_new'].combine_first(df['Para'])
    # df = merged_df[["Site", "De", "Para"]]

combined_lookup_dh = df
combined_lookup_dh["De"] = combined_lookup_dh["De"].str.strip()
combined_lookup_dh.dropna(subset=['De'])
# combined_lookup_dh["De"] = combined_lookup_dh["De"].apply(remove_acento)
combined_lookup_dh = combined_lookup_dh.drop_duplicates(subset=['Site', 'De', "Para"])

df_to_compare = pd.DataFrame(dict_dh_df)
df_to_compare["Para"] = df_to_compare["De"]
df_to_compare["De"] = df_to_compare["De"].apply(lambda value: remove_site_prefix(value, sites))
# lookup = pd.Series(df_to_compare.Para.values, index=df_to_compare.De).to_dict()

if not df_to_compare.empty:
    combined_lookup_dh = merge_de_para(combined_lookup_dh, df_to_compare)

# combined_lookup_dh['Para'] = combined_lookup_dh['De'].map(lookup).fillna(combined_lookup_dh['De'])
breakpoint()
# merged_df = combined_lookup_dh.merge(df_to_compare[['Site', 'De']], on=['Site', 'De'], how='inner')
# indexes_to_drop = merged_df.index
# combined_lookup_dh = combined_lookup_dh.drop(indexes_to_drop)
# mask = combined_lookup_dh.set_index(['Site', 'De']).index.isin(df_to_compare.set_index(['Site', 'De']).index)
# combined_lookup_dh = combined_lookup_dh[~mask]

combined_lookup_dh.to_excel(path+"de_para_data_hall.xlsx", index=False)


# ===
# Racks
# ===
columns_with_rack = ["Site", "Rack Ponta A", "Rack Ponta B", "Salto 1", "Salto 2", "Salto 3", "Salto 4", "Salto 5"]
df = combine_data(dataframes, columns_with_rack)
dict_df = {"Site": [], "De": [], "Para": []}
for row in df.iterrows():
    for column in columns_with_rack:
        value = None
        if column in ["Site"]:
            pass
        elif column in ["Rack Ponta A", "Rack Ponta B"]:
            value = row[1][column]

        else: # Saltos
            try:
                parts = row[1][column].split(":")
                if len(parts) != 4: raise Exception() # this does not followed correct pattern
                value = parts[1]
            except:
                pass

        if value:
            # if value == "MINI RACK - DH3401": breakpoint()
            dict_df["Site"].append(row[1]["Site"])
            dict_df["De"].append(value)
            dict_df["Para"].append(None)

    

df = pd.DataFrame(dict_df)
snow_racks = get_servicenow_table_data(url_snow, "cmdb_ci_rack", {"sysparm_display_value": True, "sysparm_fields":"u_data_hall.u_site.name,name"}, token)
dict_rack_df = {"Site": [], "De": [], "Para": []}

for rack in snow_racks:
    dict_rack_df["Site"].append(get_value(rack, lambda rack: rack["u_data_hall.u_site.name"], None))
    dict_rack_df["De"].append(rack["name"])
    dict_rack_df["Para"].append(None)


lookup_rack = get_df_from_excel(f"{pathImports}_lookups/de_para_rack.xlsx", {"De": [], "Para": []})
lookup_rack["De"] = lookup_rack["De"].apply(lambda value: remove_site_prefix(value, sites))

if not lookup_data_hall.empty:
    df = merge_de_para(df, lookup_rack)

# if not lookup_rack.empty:
#     merged_df = df.merge(lookup_rack, on=['Site', 'De'], how='right', suffixes=('', '_new'))
#     merged_df = merged_df.drop_duplicates(subset=['Site', 'De', "Para_new"])
#     merged_df = merged_df.reset_index()
#     merged_df['Para'] = merged_df['Para_new'].combine_first(df['Para'])
#     df = merged_df[["Site", "De", "Para"]]


combined_lookup_rack = df
combined_lookup_rack["De"] = combined_lookup_rack["De"].str.strip()
combined_lookup_rack.dropna(subset=['De'])
# combined_lookup_rack["De"] = combined_lookup_rack["De"].apply(remove_acento)
combined_lookup_rack = combined_lookup_rack.drop_duplicates(subset=['Site', 'De', "Para"])

df_to_compare = pd.DataFrame(dict_rack_df)
df_to_compare = df_to_compare.drop_duplicates(subset=['Site', 'De', "Para"])

# merged_df = combined_lookup_rack.merge(df_to_compare[['Site', 'De']], on=['Site', 'De'], how='inner')
# indexes_to_drop = merged_df.index
# combined_lookup_rack = combined_lookup_rack.drop(indexes_to_drop)
mask = combined_lookup_rack.set_index(['Site', 'De']).index.isin(df_to_compare.set_index(['Site', 'De']).index)
combined_lookup_rack = combined_lookup_rack[~mask]

combined_lookup_rack.to_excel(path+"de_para_rack.xlsx", index=False)

exit()
new_data_df = pd.concat(dataframes, ignore_index=True)

# lookup_dh = pd.Series(df_dh_depara["De"].values, df_dh_depara["Data Hall"].values)
filtered_dh = df_dh_depara[df_dh_depara["Site"] == site]
filtered_dh["De"] = filtered_dh["De"].str.split("-").str[-1]
lookup_dh = pd.Series(filtered_dh["Data Hall"].values, filtered_dh["De"].values).to_dict()

breakpoint()

df_origin["Data Hall"] = df_origin["Data Hall"].replace(lookup_dh) 
df_origin["Data Hall Ponta B"] = df_origin["Data Hall Ponta B"].replace(lookup_dh)

breakpoint()
    
