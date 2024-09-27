import json
import re, os
from turtle import back
import pandas as pd
from unidecode import unidecode
from commons.pandas.utils import *
import numpy as np

from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from dotenv import load_dotenv

load_dotenv(override=True)

sites = ["RJO1", "SPO1", "POA1", "CTA1", "BSB1", "BSB2"]
path = "C:/Users/filipe.uccelli/source/System_Integration/System_Integrations/ServiceNow/VirtCrossConnect/new_assets/"
pathImports = f"{path}import_data/"
columns_to_extract = ["CROSS ID", "Data "]


def extract_info_as_dict(df, mapping, target=None, source=""):
    if not target:
        target = {}
        for key, value in mapping.items(): target[key] = []

    if "source" not in target: target['source'] = []
    if "success" not in target: target['success'] = []
    if "origin_value" not in target: target['origin_value'] = []

    for row in df.iterrows():
        target["source"].append(source)
        target["origin_value"].append("")
        success = True
        for key, value in mapping.items():
            try:
                # breakpoint()
                if value: 
                    target[key].append(row[1][value])
                else: target[key].append("")
            
            except:
                success = False

        target["success"].append(success)
    return target

def extract_info_from_hop(row, hop_column, source=""):
    err = False
    dict_info = {}

    try:
        if column not in row[1]: return None, dict_info
        value = row[1][hop_column]
        if str(value) == "nan": return False, dict_info

        parts = str(value).split(":")
        dict_info["ID Cross"] = get_value(row, lambda x: x[1]["ID Cross"], "")
        dict_info["Cliente"] = ""
        dict_info["Data Hall"] = get_value(parts, lambda x: x[0], "")
        dict_info["Rack"] = get_value(parts, lambda x: x[1], "")
        dict_info["Asset"] = get_value(parts, lambda x: x[2], "")
        dict_info["Interface"] = get_value(parts, lambda x: x[3], "")
        dict_info["Classificação"] = ""
        dict_info["source"] = source
        dict_info["origin_value"] = value
        if len(parts) != 4: raise Exception() # this does not follows correct pattern

    except Exception as e:
        err = True


    # if len(dict_info.keys()) < 9: breakpoint()
    dict_info["success"] = not err

    return err, dict_info

def merge_de_para_assets(df, lookup, columns_to_keep):
    merged_right = df.merge(lookup, on=[*columns_to_keep, 'De'], how='right', suffixes=('', '_new'))
    merged_right['Para'] = merged_right['Para_new'].combine_first(merged_right['Para'])
    final_merged = df.merge(merged_right, on=[*columns_to_keep, 'De'], how='outer', suffixes=('', '_final'))
    final_merged['Para'] = final_merged['Para_final'].combine_first(final_merged['Para'])
    final_merged = final_merged.drop_duplicates(subset=[*columns_to_keep, 'De', "Para"])
    return final_merged[[*columns_to_keep, "De", "Para"]]

def apply_lookup(df, dict_lookup, target_column, fillna=None):
    if not fillna: fillna = target_column

    return df[target_column].map(dict_lookup).replace("", np.nan).fillna(df[fillna])

def create_concat_column(df, column_to_concat, sep="-"):
    return df[column_to_concat].fillna("").astype(str).agg(sep.join, axis=1)

if __name__ == '__main__':

    for site in sites:
        df = get_df_from_excel(f"{pathImports}{site}/snow_cross_{site}_data.xlsx")
        df_depara = get_df_from_excel(f"{pathImports}{site}/{site}_de_para_assets.xlsx")
        if df.empty: continue

        mapping_side_a = {"ID Cross": "ID Cross", "Cliente":"Tip A customer", "Data Hall": "Datahall tip A", "Rack": "A tip rack", "Asset": "Patch Panel tip A", "Interface": "Tip port A", "Classificação": "Control Tip A"}
        mapping_side_b = {"ID Cross": "ID Cross", "Cliente":"Tip B customer", "Data Hall": "Datahall tip B", "Rack": "Tip B rack", "Asset": "Patch Panel tip B", "Interface": "Tip port B", "Classificação": "Control Tip B"}

        assets_df = extract_info_as_dict(df, mapping_side_a, source="Side A")
        assets_df = extract_info_as_dict(df, mapping_side_b, assets_df, source="Side B")
        errors = []
        hops_columns = ["Jump 1", "Jump 2", "Jump 3", "Jump 4", "Jump 5", "Jump 6", "Jump 7"]

        for row in df.iterrows():
            for column in hops_columns:
                err, asset = extract_info_from_hop(row, column, source=column)
                if err: 
                    id_cross = get_value(row, lambda x: x[1]["ID Cross"], "")
                    value = get_value(row, lambda x: x[1][column], "")
                    errors.append((id_cross, column, value))
                    if not asset or "ID Cross" not in asset: 
                        continue
                    # continue
                
                for key in asset.keys():
                    assets_df[key].append(asset[key])

                # if asset: breakpoint()
        
        # breakpoint()
        df = pd.DataFrame(assets_df)
        
        # a partir desse df, vamos gerar dois de paras: 1 focado em padronizar nome de asset, e outro focado em padronizar nomes de interface
        
        # de para assets
        localization_columns_asset = ["Cliente", "Data Hall", "Rack"]
        columns_to_keep = [*localization_columns_asset, "Classificação"]
        df_lookup_assets = df[columns_to_keep]
        df_lookup_assets["De"] = df["Asset"]
        df_lookup_assets["Para"] = ""
        df_lookup_assets["De"] = df_lookup_assets["De"].str.strip()
        # df_lookup_assets = df_lookup_assets.dropna(subset=['De'])
        df_lookup_assets = df_lookup_assets.drop_duplicates(subset=[*localization_columns_asset, "De"])

        old_df_lookup_assets = get_df_from_excel(f"{pathImports}/{site}/{site}_de_para_assets.xlsx")
        if not old_df_lookup_assets.empty:
            df_lookup_assets = merge_de_para_assets(df_lookup_assets, old_df_lookup_assets, columns_to_keep=columns_to_keep)

        df_lookup_assets.to_excel(f"{pathImports}/{site}/{site}_de_para_assets.xlsx", index=False)

        # rules to auto fill lookup

        # analisar por localização e asset
        # localization_columns_asset_minus_client = [x for x in localization_columns_asset if x != "Cliente"]
        # df_lookup_assets["concat_local"] = create_concat_column(df_lookup_assets, column_to_concat=localization_columns_asset_minus_client, sep="[-]")
        # list_assets = df_lookup_assets.to_dict(orient='records')
        # list_assets_de = [x for x in list_assets if isinstance(x["De"], str)]

        # list_assets = [x for x in list_assets if "DIO" in get_value(x, lambda x: x["De"], "")]
        # breakpoint()

        # de para interfaces
        localization_columns_interface = ["Cliente", "Data Hall", "Rack", "Asset"]
        columns_to_keep = ["ID Cross", *localization_columns_interface]
        df_lookup_interfaces = df[columns_to_keep]
        df_lookup_interfaces["De"] = df["Interface"]
        df_lookup_interfaces["Para"] = ""

        old_df_lookup_interfaces = get_df_from_excel(f"{pathImports}/{site}/{site}_de_para_interfaces.xlsx")
        if not old_df_lookup_interfaces.empty:
            df_lookup_interfaces = merge_de_para_assets(df_lookup_interfaces, old_df_lookup_interfaces, columns_to_keep=columns_to_keep)
        
        list_interfaces = df_lookup_interfaces.to_dict(orient='records')

        # breakpoint()

        # aplica de para em df interfaces

        # df_lookup_assets["concat_de"] = df_lookup_assets[[*localization_columns_asset, "De"]].fillna("").astype(str).agg("[-]".join, axis=1)
        # lookup_asset_dict = pd.Series(df_lookup_assets.Para.values, index=df_lookup_assets.concat_de).to_dict()
        # df_lookup_interfaces["Asset"] = df[localization_columns_interface].fillna("").astype(str).agg("[-]".join, axis=1)
        # df_lookup_interfaces["Asset"] = apply_lookup(df_lookup_interfaces, lookup_asset_dict, target_column="Asset")

        df_lookup_interfaces.to_excel(f"{pathImports}/{site}/{site}_de_para_interfaces.xlsx", index=False)

        # aplica de para de interfaces
        df_lookup_interfaces["concat_de"] = df_lookup_interfaces[[*localization_columns_interface, "De"]].fillna("").astype(str).agg("[-]".join, axis=1)
        df["concat_interface"] = df[[*localization_columns_interface, "Interface"]].fillna("").astype(str).agg("[-]".join, axis=1)
        lookup_interface_dict = pd.Series(df_lookup_interfaces.Para.values, index=df_lookup_interfaces.concat_de).to_dict()
        df["Interface"] = apply_lookup(df, lookup_interface_dict, target_column="concat_interface", fillna="Interface")

        # aplica de para em df assets
        df_lookup_assets["concat_de"] = df_lookup_assets[[*localization_columns_asset, "De"]].fillna("").astype(str).agg("[-]".join, axis=1)
        lookup_asset_dict = pd.Series(df_lookup_assets.Para.values, index=df_lookup_assets.concat_de).to_dict()
        df["concat_asset"] = df[[*localization_columns_asset, "Asset"]].fillna("").astype(str).agg("[-]".join, axis=1)
        df["Asset"] = apply_lookup(df, lookup_asset_dict, target_column="concat_asset", fillna="Asset")

        df_lookup_assets["key"] = df_lookup_assets["concat_de"]
        df["key"] = df["concat_asset"]
        merged_df = pd.merge(df, df_lookup_assets[['key', 'Classificação']], on='key', how='left', suffixes=('', '_lookup'))
        df['Classificação'] = merged_df['Classificação_lookup'].combine_first(df['Classificação'])

        # a partir do de para de assets, encontra o nome antigo do de para de interface
        df = df.drop(columns=["concat_asset", "concat_interface", "key"])

        df = df.sort_values(by="ID Cross").reset_index(drop=True)

        # empty_mapping = {"SOLTO": ""}
        # breakpoint()
        # df["Rack"] = df["Rack"].map(empty_mapping) # .fillna(df["Rack"])
        # df["Asset"] = df["Asset"].map(empty_mapping) # .fillna(df["Asset"])
        # df["Interface"] = df["Interface"].map(empty_mapping) # .fillna(df["Interface"])
        df["Rack"] = df["Rack"].replace("SOLTO", "") # .fillna(df["Rack"])
        df["Asset"] = df["Asset"].replace("SOLTO", "") # .fillna(df["Asset"])
        df["Interface"] = df["Interface"].replace("SOLTO", "") # .fillna(df["Interface"])


        if site == "POA1": breakpoint()

        df.to_excel(f"{pathImports}{site}/{site}_assets.xlsx", index=True)

        list_assets = df.replace(np.nan, "").to_dict(orient='records', index=True)
        if list_assets:
            for index, asset in enumerate(list_assets):
                asset["index"] = index
            
            with open(f"{pathImports}{site}/{site}_assets.json", 'w', encoding='utf-8') as f:
                json.dump(list_assets, f, ensure_ascii=False, indent=4)
        
