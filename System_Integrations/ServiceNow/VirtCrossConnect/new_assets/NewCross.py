import json
import os
import argparse
import re

from dotenv import load_dotenv
from numpy import iinfo
import pandas as pd

from System_Integrations.utils.compare_utils import is_response_ok
from System_Integrations.utils.mapper import map_to_requests_response
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data, post_to_servicenow_table
from commons.pandas.utils import get_df_from_excel
from .Unveil import pathImports, sites, path as basePath

load_dotenv(override=True)
url_snow = os.getenv("snow_url")

default_virtual_rack_name = "" # "VRACK"
default_virtual_pp_name = "" # "VPP01"
default_virtual_interface_name = "" # "VITF01"
default_company_asset = "ELEA DIGITAL INFRAESTRUTURA E REDES DE T" # "VITF01"

def parse_cross_to_snow(cross):
    return {
        **cross,
        "u_id_cross": cross["ID Cross"], 
        "location": cross["Site"], 
        "u_final_customer": cross["Cliente Final"], 
        "u_activation_date": cross["Data da ativação"], 
        "u_delivery_request": cross["Request"], 
        "u_innerduct_only_tlc": cross["Innerduct (only TLC)"], 
        "u_quantity_innerduct": cross["Quantity Innerduct"], 
        "u_legado": cross["Legado"], 
        "u_active": cross["Active"], 
        "u_type_of_cross": cross["Type of Cross"],
        "u_review_stage": "Pending"
    }

def parse_racks_from_cross(cross):
    def get_rack_info(item, suffix=""):
        return item["source"+suffix], {
            "u_data_hall": item["u_data_hall"+suffix],
            "name": item["u_rack"+suffix],
            "u_review_stage": "Pending"
        }

    yield get_rack_info(cross, suffix="_a")
    yield get_rack_info(cross, suffix="_b")
    for jump in cross["Jumps"]:
        yield get_rack_info(jump)

def generator_assets_from_cross(cross):
    def get_asset_info(item, suffix=""):
        company = default_company_asset
        device_type = get_value(item, lambda x: item["device_type"+suffix], None)
        virtual = False

        if item["device_type"+suffix] == "Virtual":
            company = get_value(item, lambda x: item["u_customer"+suffix], None)
            device_type = "Patch Panel"
            virtual = True

        return item["source"+suffix], {
            "location": cross["Site"],
            "u_rack.u_data_hall": item["u_data_hall"+suffix],
            "u_rack": item["u_rack"+suffix],
            "name": item["u_asset"+suffix],
            "device_type": device_type,
            "u_virtual": virtual,
            "company": company,
            "u_review_stage": "Pending"
        }

    
    yield get_asset_info(cross, suffix="_a")
    yield get_asset_info(cross, suffix="_b")
    for jump in cross["Jumps"]:
        yield get_asset_info(jump)


def generator_interfaces_from_cross(cross):
    def get_interface_info(item, suffix=""):
        return item["source"+suffix], {
            "u_asset.u_rack.u_data_hall": item["u_data_hall"+suffix],
            "u_asset.u_rack": item["u_rack"+suffix],
            "u_asset": item["u_asset"+suffix],
            "interface_name": item["u_interface"+suffix],
            "u_module": item["u_module"+suffix],
            "u_review_stage": "Pending"
        }

    yield get_interface_info(cross, suffix="_a") 
    yield get_interface_info(cross, suffix="_b") 
    for jump in cross["Jumps"]:
        yield get_interface_info(jump) 

def parse_wires_from_cross(cross):
    pass




def post_to_snow(newStructure):
    servicenow_client_id = os.getenv("snow_client_id") #get_api_token('servicenow-prd-client-id-oauth')
    servicenow_client_secret = os.getenv("snow_client_secret") #get_api_token('servicenow-prd-client-secret-oauth')
    service_now_refresh_token = os.getenv("snow_refresh_token") #get_api_token('servicenow-prd-refresh-token-oauth')

    token = get_servicenow_auth_token(url_snow, servicenow_client_id, servicenow_client_secret, service_now_refresh_token)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+token,
    }
    params = {"sysparm_input_display_value":"true"}

    get_display_value = lambda item: get_value(item, lambda x: x["display_value"], item)
    def parse_values(arr):
        return [
            {key: get_display_value(value) for key, value in item.items()} for item in arr
        ]
    
         

    cross_fields = ["u_id_cross", "name", "sys_id"
                    "location",
                    "u_customer_a", "u_data_hall_a", "u_rack_a", "u_interface_a",
                    "u_customer_b", "u_data_hall_b", "u_rack_b", "u_interface_b",
                ]
    
    snow_cross = get_servicenow_table_data(url_snow, "u_cmdb_ci_bs_cross_connect", {"sysparm_display_value": True, "sysparm_fields":", ".join(cross_fields)}, token)
    snow_cross = parse_values(snow_cross)
    # dh_fields = []
    # snow_data_halls = get_servicenow_table_data(url_snow, "u_cmdb_ci_data_hall", {"sysparm_display_value": True}, token)

    rack_fields = ["u_data_hall", "company", "name", "sys_id"]
    snow_racks = get_servicenow_table_data(url_snow, "cmdb_ci_rack", {"sysparm_display_value": True, "sysparm_fields":", ".join(rack_fields)}, token)
    snow_racks = parse_values(snow_racks)

    asset_fields = ["location", "device_type", "name", "u_rack", "u_rack.u_data_hall", "sys_id"]
    snow_assets = get_servicenow_table_data(url_snow, "cmdb_ci_netgear", {"sysparm_display_value": True, "sysparm_fields":", ".join(asset_fields)}, token)
    snow_assets = parse_values(snow_assets)

    interface_fields = ["name", "u_asset.u_rack.u_data_hall",  "u_asset.u_rack", "u_asset", "u_module", "interface_name", "sys_id"]
    snow_interfaces = get_servicenow_table_data(url_snow, "dscy_switchport", {"sysparm_display_value": True, "sysparm_fields":", ".join(interface_fields)}, token)
    snow_interfaces = parse_values(snow_interfaces)


    results = []
    for newCross in newStructure:
        if newCross["ID Cross"] != "ID-RJO1-00046": continue

        default_result = {
            "post_status": "ok",
            # "post_status_error_while": "",
            "post_error": "" 
        }

        cross = parse_cross_to_snow(newCross)
        if cross["u_id_cross"] in [x["u_id_cross"] for x in snow_cross]: continue

        # racks = parse_racks_from_cross(newCross)
        # assets = parse_assets_from_cross(newCross)
        # interfaces = parse_interfaces_from_cross(newCross)
        wires = parse_wires_from_cross(newCross)


        # try:
        # for origin, rack in parse_racks_from_cross(newCross):
        #     rackLocal = (rack["u_data_hall"], rack["name"])

        #     corr_rack = next((x for x in snow_racks if rackLocal == (x["u_data_hall"], x["name"])), None)
        #     if corr_rack: continue


        #     breakpoint()
        #     response = post_to_servicenow_table(url_snow, "cmdb_ci_rack", rack, token, params)
        #     if response["error"]:
        #         rack["post_status"] = "error"
        #         rack["post_error"] = response["errorMsg"]
        #         print(f"Error creating rack {rack['name']} \n {response['errorMsg']}")
        #         continue
            
        #     rack = {**rack, **default_result}
        #     rack["sys_id"] = get_value(response, lambda x: x["response_http"].json()["result"]["sys_id"], None)
        #     snow_racks.append(rack)

        for source, asset in generator_assets_from_cross(newCross):
            assetLocal = (asset["u_rack.u_data_hall"], asset["u_rack"], asset["name"])

            corr_asset = next((x for x in snow_assets if assetLocal == (x["u_rack.u_data_hall"], x["u_rack"], x["name"])), None)
            if corr_asset: continue
            elif site == "RJO1" and "Jump" in source:
                # TODO AVALAIR CASOS DO RJO1 EM QUE SALTOS POSSUEM PREENCHIMENTO DIFERENTE PARA ESPELHAMENTO
                snow_rack = next((x for x in snow_racks if x["name"] == asset["u_rack"]), None)
                if not snow_rack: continue
                if snow_rack["u_data_hall"] != asset["u_rack.u_data_hall"]:
                    asset["u_anotacoes"] = "Identificado como espelhamento"
                    asset["u_espelhamento"] = True 
                
            if "Jump" in source and asset["device_type"] in ["Patch Panel", "DIO"]: asset["u_backbone"] = True
            asset["u_rack"] = next((x["sys_id"] for x in snow_racks if x["name"] == asset["u_rack"] and x["u_data_hall"] == asset["u_rack.u_data_hall"]), asset["u_rack"])

            breakpoint()
            response = post_to_servicenow_table(url_snow, "cmdb_ci_netgear", asset, token, params) 
            if response["error"]:
                asset["post_status"] = "error"
                asset["post_error"] = response["errorMsg"]
                print(f"Error creating asset {asset['name']} \n {response['errorMsg']}")
                continue
            
            asset = {**asset, **default_result}
            asset["sys_id"] = get_value(response, lambda x: x["response_http"].json()["result"]["sys_id"], None)
            snow_assets.append(asset)


        for source, interface in generator_interfaces_from_cross(newCross):
            interfaceLocal = (interface["u_asset.u_rack.u_data_hall"], interface["u_asset.u_rack"], interface["u_asset"], interface["interface_name"])

            corr_interface = next((x for x in snow_interfaces if interfaceLocal == (x["u_asset.u_rack.u_data_hall"], x["u_asset.u_rack"], x["u_asset"], x["interface_name"])), None)
            if corr_interface: continue

            is_the_same_asset = lambda a,b: (a["u_rack.u_data_hall"] == b["u_asset.u_rack.u_data_hall"] 
                                                and a["u_rack"] == b["u_asset.u_rack"] 
                                                and a["name"] == b["u_asset"]
                                            )

            interface["u_asset"] = next((x["sys_id"] for x in snow_assets if is_the_same_asset(x, interface)), interface["u_asset"])

            breakpoint()
            response = post_to_servicenow_table(url_snow, "dscy_switchport", interface, token, params) 
            if response["error"]:
                interface["post_status"] = "error"
                interface["post_error"] = response["errorMsg"]
                print(f"Error creating interface {interface['name']} \n {response['errorMsg']}")
                continue
            
            interface = {**interface, **default_result}
            interface["sys_id"] = get_value(response, lambda x: x["response_http"].json()["result"]["sys_id"], None)
            snow_interfaces.append(interface)


           

    # except Exception as e:
        #     pass

        breakpoint()

        is_same_interface = lambda a,b,suffix: (a["interface_name"] == b["u_interface"+suffix] 
                                                and a["u_asset"] == b["u_asset"+suffix] 
                                                and a["u_asset.u_rack"] == b["u_rack"+suffix] 
                                                and a["u_asset.u_rack.u_data_hall"] == b["u_data_hall"+suffix])
        
        # test = lambda a,b,suffix: print(f"TESTE \n\n {a} \n\n {b} \n\n {suffix}")

        # inte = [x for x in snow_interfaces if (x["u_asset"] == cross["u_asset_a"] and x["u_asset.u_rack"] == cross["u_rack_a"])]
        # breakpoint()

        cross["u_interface_a"] = next((x["sys_id"] for x in snow_interfaces if is_same_interface(x, cross, "_a")), cross["u_interface_a"])
        cross["u_interface_b"] = next((x["sys_id"] for x in snow_interfaces if is_same_interface(x, cross, "_b")), cross["u_interface_b"])

        breakpoint()
        response = post_to_servicenow_table(url_snow, "u_cmdb_ci_bs_cross_connect", cross, token, params)  
    
        if response["error"]:
            cross["post_status"] = "error"
            cross["post_error"] = response["errorMsg"]
            print(f"Error creating cross {cross['u_id_cross']} \n {response['errorMsg']}")
            continue
        
        breakpoint()
        cross = {**cross, **default_result}
        cross["sys_id"] = get_value(response, lambda x: x["response_http"].json()["result"]["sys_id"], None)
        snow_cross.append(cross)


def create_new_structure(path, fileName, oldCross):
    df = get_df_from_excel(path+fileName).fillna("")
    df_old_cross = get_df_from_excel(path+oldCross)
    
    if df.empty: 
        print(f"File {fileName} not found")
        return
    
    def _get_interface_info(asset):
        interface = get_value(asset, lambda x: x["Interface"], default_virtual_interface_name)
        mod = ""
        matches = re.findall(r"MODX|MOD\d+", interface)
        if matches:
            mod = matches[0].replace("MOD", "")
            interface = interface.replace("MOD", "")
    
        return mod, interface

    def extract_side(side, dict_info):
        suffix = "a" if "a" in side.lower() else "b"
        side = next((x for x in dict_info if x["source"] == side), None)

        mod, interface = _get_interface_info(side)

        side = {
            "u_customer_"+suffix: get_value(side, lambda x: x["Cliente"], None),
            "u_data_hall_"+suffix:  get_value(side, lambda x: x["Data Hall"], None),
            "u_rack_"+suffix: get_value(side, lambda x: x["Rack"], default_virtual_rack_name),
            "u_asset_"+suffix: get_value(side, lambda x: x["Asset"], default_virtual_pp_name),
            "u_interface_"+suffix: interface,
            "u_module_"+suffix: mod,
            "comments_"+suffix: get_value(dict_old_cross, lambda x: x[0]["Comments A"], ""),
            "device_type_"+suffix: get_value(side, lambda x: x["Classificação"], default_virtual_interface_name),
            "source_"+suffix: get_value(side, lambda x: x["source"], None),
        }


        # side = {
        #     "Cliente": get_value(side, lambda x: x["Cliente"], None),
        #     "u_data_hall":  get_value(side, lambda x: x["u_data_hall"], None),
        #     "u_rack": get_value(side, lambda x: x["u_rack"], default_virtual_rack_name),
        #     "u_asset": get_value(side, lambda x: x["u_asset"], default_virtual_pp_name),
        #     "u_module": mod,
        #     "u_interface": interface,
        #     "Comments": get_value(dict_old_cross, lambda x: x[0]["Comments"], ""),
        #     "device_type": get_value(side, lambda x: x["device_type"], default_virtual_interface_name),
        # }

        return side

    def extract_hop(asset):
        mod, interface = _get_interface_info(asset)

        hop = {
            # "Cliente": get_value(side, lambda x: x["Cliente"], None),
            "u_data_hall":  get_value(asset, lambda x: x["Data Hall"], None),
            "u_rack": get_value(asset, lambda x: x["Rack"], default_virtual_rack_name),
            "u_asset": get_value(asset, lambda x: x["Asset"], default_virtual_pp_name),
            "u_module": mod,
            "u_interface": interface,
            # "Comments A": get_value(dict_old_cross, lambda x: x[0]["Comments A"], ""),
            "device_type": get_value(asset, lambda x: x["Classificação"], default_virtual_interface_name),
            "source": get_value(asset, lambda x: x["source"], None),
        }

        return hop 


    newStructure = []
    dict_old_crosses = df_old_cross.to_dict(orient="records")
    for idCross in df["ID Cross"].unique():
        df_info = df[df["ID Cross"] == idCross]    
        dict_info = df_info.to_dict(orient="records")
        # old_cross = df_old_cross[df_old_cross["ID Cross"] == idCross]
        dict_old_cross = next((x for x in dict_old_crosses if x["ID Cross"] == idCross), None)

        data_ativacao = get_value(dict_old_cross, lambda x: x["Activation Date"], None)
        if pd.isnull(data_ativacao): data_ativacao = None
        else: data_ativacao = data_ativacao.isoformat()

        request = get_value(dict_old_cross, lambda x: x["Request"], None)
        if pd.isna(request): request = None

        cross = {
            "ID Cross": idCross,
            "Site": get_value(dict_old_cross, lambda x: x["Site"], None),
            "Cliente Final": get_value(dict_old_cross, lambda x: x["Final Customer"], None),
            "Data da ativação": data_ativacao,
            "Request": request,
            "Innerduct (only TLC)": get_value(dict_old_cross, lambda x: x["Innerduct (only TLC)"], 0),
            "Quantity Innerduct": get_value(dict_old_cross, lambda x: x["Quantity Innerduct"], 0),
            "Legado": get_value(dict_old_cross, lambda x: x["Legado"], False),
            "Active": get_value(dict_old_cross, lambda x: x["Active"], True),
            "Type of Cross": get_value(dict_old_cross, lambda x: x["Type of Cross"], None),
            "Media type": get_value(dict_old_cross, lambda x: x["Media type"], None),
            **extract_side("Side A", dict_info),
            **extract_side("Side B", dict_info),
            "Jumps": [
                extract_hop(x) for x in dict_info if "Jump" in x["source"] 
            ]
        }

        newStructure.append(cross)

    return newStructure



 

parser = argparse.ArgumentParser(description="process some flags.")
parser.add_argument('-s', '--site', type=str, help='site to perform the processing (uses the <site>_assets.json file)')
parser.add_argument('-p', '--preview', action='store_true', default=False, help='process data no matter token count')
# parser.add_argument('-do', '--do', action='store_true', default=False, help='parses existing processed json file to xlsx')

if __name__ == '__main__':

    args = parser.parse_args()
    site = args.site
    # do = args.do
    preview = args.preview

    path = f"{pathImports}{site}"
    # pathfile = f"{path}/{site}_assets.json"
    pathFile = f"{path}/{site}_assets.json"


    if site not in sites:
        print(f"Site {site} not supported, must be one of: {', '.join(sites)}")
        exit()

    newStructure = create_new_structure(f"{path}/", f"{site}_assets.xlsx", f"snow_cross_{site}_data.xlsx")
    
    with open(f"{path}/{site}_new_cross.json", 'w', encoding='utf-8') as f:
        json.dump(newStructure, f, ensure_ascii=False, indent=4)

        
    if not preview and (newStructure):
        pass
        df_result = post_to_snow(newStructure)
        # df_result.to_excel(f"{path}/{site}_post_result.xls", index=False)