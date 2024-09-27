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

# def merge_de_para(df, lookup):
#     # merged_df = df.merge(lookup, on=['Site', 'De'], how='left', suffixes=('', '_new'))
#     # merged_df = merged_df.drop_duplicates(subset=['Site', 'De', "Para_new"])
#     # merged_df = merged_df.reset_index()
#     # merged_df['Para'] = merged_df['Para_new'].combine_first(df['Para'])
#     # return merged_df[["Site", "De", "Para"]]
#     merged_right = df.merge(lookup, on=['Site', 'De'], how='right', suffixes=('', '_new'))
#     merged_right['Para'] = merged_right['Para_new'].combine_first(merged_right['Para'])
#     final_merged = df.merge(merged_right, on=['Site', 'De'], how='outer', suffixes=('', '_final'))
#     final_merged['Para'] = final_merged['Para_final'].combine_first(final_merged['Para'])
#     final_merged = final_merged.drop_duplicates(subset=['Site', 'De', "Para"])
#     # breakpoint()
#     return final_merged[["Site", "De", "Para"]]

def merge_de_para(df, lookup, columns_to_keep=[]):
    merged_right = df.merge(lookup, on=[*columns_to_keep, 'De'], how='right', suffixes=('', '_new'))
    merged_right['Para'] = merged_right['Para_new'].combine_first(merged_right['Para'])
    final_merged = df.merge(merged_right, on=[*columns_to_keep, 'De'], how='outer', suffixes=('', '_final'))
    final_merged['Para'] = final_merged['Para_final'].combine_first(final_merged['Para'])
    final_merged = final_merged.drop_duplicates(subset=[*columns_to_keep, 'De', "Para"])
    return final_merged[[*columns_to_keep, "De", "Para"]]

def apply_de_para(lookup, df, match={}, apply={}):
    """
    Parameters
    ----------
    lookup : DataFrame
    df : DataFrame
    match : dict
        key-value will be used as column in lookup => column in df when matching
        example: 
            {"Site": "Site", "Data Hall": "Data Hall", "De": "Rack"}
            Means that: lookup ["Site", "Data Hall", "De"] will be matched with df ["Site", "Data Hall", "Rack"]
    columns_to_apply : dict
        key-value that will be used as column in lookup => column in df when overriting
        example: 
            {"Para": "Rack"}
            Means that: lookup ["Para"] will overrite df ["Rack"] on matches
    """
    original_columns = df.columns
    df_copy = df

    # match_equal_name = {key + suffix_match: value for key, value in match.items()}
    # apply = {key + suffix_match: value for key, value in apply.items()}

    suffix_match = "__TO_MATCH"
    map_match = {}
    for key, value in match.items():
        map_match[key] = key+suffix_match # was key now is key+suffix_match
        # makes the data be store in a column with the same name in both tables
        lookup[key+suffix_match] = lookup[key]
        df_copy[key+suffix_match] = df_copy[value]
    
    # suffix_apply = "__TO_APPLY"
    # suffix_overrite = "__TO_OVERRITE"
    # map_apply = {}
    # map_overrite = {}
    # for key, value in apply.items():
    #     map_apply[key] = key+suffix_apply # was key now is key+suffix_apply
    #     map_overrite[value] = value+suffix_overrite # was key now is key+suffix_apply
    #     # makes the data be store in a column with the same name in both tables
    #     lookup[key+suffix_apply] = lookup[key]
    #     df_copy[value+suffix_overrite] = df_copy[value]

    on = [
        *list(map_match.values()), # column that must be equal to apply the lookup in a row
    ]

    lookup = lookup.drop(columns=["Observação"])
    
    df_copy = pd.merge(df_copy, lookup, how="left", on=on, suffixes=('', '_new'))
    for key, value in apply.items():
        key_name = key+"_new" if key+"_new" in df_copy.columns else key
        df_copy[value] = df_copy[key_name].fillna(df_copy[value])

    df_copy = df_copy.drop_duplicates(subset=["ID Cross"], keep='first')

    return df_copy[original_columns]
     
if __name__ == '__main__':
        
    dataframes = []
    for site in sites:
        df = get_df_from_excel(f"{pathImports}{site}/cross_{site}_data.xlsx")
        df["Site"] = site
        dataframes.append(df)

    # ===
    # Customer
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
        df = merge_de_para(df, lookup_data_hall, ["Site"])

    df["De"] = df["De"].apply(lambda value: remove_site_prefix(value, sites))
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
        combined_lookup_dh = merge_de_para(combined_lookup_dh, df_to_compare, ["Site"])

    combined_lookup_dh.to_excel(path+"de_para_data_hall.xlsx", index=False)


    # ===
    # Racks
    # ===
    columns_with_rack = ["Site", "Data Hall", "Data Hall Ponta B", "Rack Ponta A", "Rack Ponta B", "Salto 1", "Salto 2", "Salto 3", "Salto 4", "Salto 5"]
    df = combine_data(dataframes, columns_with_rack)
    # breakpoint()
    dict_df = {"Site": [], "Data Hall": [], "De": [], "Para": []}
    list_cross = df.to_dict(orient="records")

    def get_dh_rack(columns, row):
        dh = None
        rack = None

        if "salto" in columns:
            try:
                # if row[columns["salto"]] == "DH03:T6:DG TI-M2 DIO.M2:PT9/10": breakpoint()
                parts = row[columns["salto"]].split(":")
                if len(parts) != 4: raise Exception() # this does not followed correct pattern
                dh = parts[0]
                rack = parts[1]
            except:
                pass
        else:
            dh = row[columns["dh"]]
            rack = row[columns["rack"]]

        return dh, rack


    combination_to_extract = [
        {"dh": "Data Hall", "rack": "Rack Ponta A"},
        {"dh": "Data Hall Ponta B", "rack": "Rack Ponta B"},
        {"salto": "Salto 1"},
        {"salto": "Salto 2"},
        {"salto": "Salto 3"},
        {"salto": "Salto 4"},
        {"salto": "Salto 5"},
        # {"salto": "Salto 6"},
        # {"salto": "Salto 7"}
    ]

    for row in list_cross:
        for combination in combination_to_extract:
            dict_df["Site"].append(row["Site"])
            dh, rack = get_dh_rack(combination, row)
            dict_df["Data Hall"].append(dh)
            dict_df["De"].append(rack)
            dict_df["Para"].append("")

    df = pd.DataFrame(dict_df)
    snow_racks = get_servicenow_table_data(url_snow, "cmdb_ci_rack", {"sysparm_display_value": True, "sysparm_fields":"u_data_hall.u_site.name, u_data_hall.name, name"}, token)
    dict_rack_df = {"Site": [], "Data Hall": [], "De": [], "Para": []}

    # breakpoint()

    for rack in snow_racks:
        if not rack["u_data_hall.name"]: continue
        dict_rack_df["Site"].append(get_value(rack, lambda rack: rack["u_data_hall.u_site.name"], None))
        dict_rack_df["Data Hall"].append(rack["u_data_hall.name"])
        dict_rack_df["De"].append(rack["name"])
        dict_rack_df["Para"].append(None)

    lookup_rack = get_df_from_excel(f"{pathImports}_lookups/de_para_rack.xlsx", {"Data Hall":[], "De": [], "Para": [], "Observação": []})
    lookup_rack["De"] = lookup_rack["De"].apply(lambda value: remove_site_prefix(value, sites))

    df['Data Hall'] = df['Data Hall'].str.strip()

    df = apply_de_para(combined_lookup_dh, df, 
                    match={"Site": "Site", "De": "Data Hall"}, # site must match site, De must match Data Hall
                    apply={"Para": "Data Hall"} # on matches, apply content of Para on Data Hall
                    )

    df = df.drop_duplicates(subset=['Site', 'Data Hall', 'De'])

    if 'Data Hall' not in lookup_rack.columns:
        lookup_rack.insert(1, 'Data Hall', None)
        # Merge on 'Site' and 'De'
        df_merged = pd.merge(df, lookup_rack[['Site', 'De', 'Para', "Observação"]], on=['Site', 'De'], how='left')

        # Apply a function to keep the first match and leave the rest as blank
        def fill_first_match(group):
            # group['Para_x'] = group['Para_y'].fillna(method='ffill').where(group['Para_x'].notna())
            # group['Para_x'] = group['Para_x'].mask(group.duplicated(subset=['Site', 'De']), None)
            # return group
            # if group["De"].isin(["MINI RACK - DH3401"]).any(): breakpoint()
            group.loc[group.index[0], 'Para_x'] = group.loc[group.index[0], 'Para_y']
            return group

        # Apply the logic to each group of 'Site' and 'De'
        df_merged = df_merged.groupby(['Site', 'De'], group_keys=False).apply(fill_first_match)
        # df["Para"] = df["Para_x"]
        # df = df.drop(columns=["Para_x", "Para_y"])
        df = df_merged.drop(columns='Para_y').rename(columns={'Para_x': 'Para'})
        lookup_rack = lookup_rack.drop(columns=["Data Hall"])

    if not lookup_rack.empty and 'Data Hall' in lookup_rack.columns:
        if 'Observação' not in df.columns: df.insert(1, 'Observação', None)
        df = merge_de_para(df, lookup_rack, ["Site", "Data Hall", "Observação"])
        df = df[["Site", "Data Hall", "De", "Para", "Observação"]]


    lookup_data_hall_dict = pd.Series(combined_lookup_dh.Para.values, index=combined_lookup_dh.De).to_dict()

    combined_lookup_rack = df
    combined_lookup_rack["De"] = combined_lookup_rack["De"].str.strip()
    combined_lookup_rack.dropna(subset=['Site', 'Data Hall', 'De'])
    # combined_lookup_rack["De"] = combined_lookup_rack["De"].apply(remove_acento)
    combined_lookup_rack = combined_lookup_rack.drop_duplicates(subset=['Site', 'Data Hall', 'De', "Para"])


    df_to_compare = pd.DataFrame(dict_rack_df)

    df_to_compare = df_to_compare.drop_duplicates(subset=['Site', 'Data Hall', 'De', "Para"])

    # merged_df = combined_lookup_rack.merge(df_to_compare[['Site', 'De']], on=['Site', 'De'], how='inner')
    # indexes_to_drop = merged_df.index
    # combined_lookup_rack = combined_lookup_rack.drop(indexes_to_drop)
    mask = combined_lookup_rack.set_index(['Site', 'Data Hall', 'De']).index.isin(df_to_compare.set_index(['Site', 'Data Hall', 'De']).index)
    combined_lookup_rack = combined_lookup_rack[~mask]

    # combined_lookup_rack = combined_lookup_rack[combined_lookup_rack["Site"] == "POA1"]

    combined_lookup_rack.to_excel(path+"de_para_rack.xlsx", index=False)

        
