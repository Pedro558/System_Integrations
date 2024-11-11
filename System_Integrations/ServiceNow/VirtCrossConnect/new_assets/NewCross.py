import array
from datetime import datetime
import json
import os
import argparse
import re
import traceback

from dotenv import load_dotenv
from numpy import iinfo
import pandas as pd
import test

from System_Integrations.utils.compare_utils import is_response_ok
from System_Integrations.utils.mapper import map_to_requests_response
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data, patch_servicenow_record, post_to_servicenow_table
from commons.pandas.utils import get_df_from_excel
from commons.utils.logging import save_file
from .Unveil import pathImports, sites, path as basePath
from ..CreateImports import pathImports as oldImportPath

load_dotenv(override=True)
url_snow = os.getenv("snow_url")

default_virtual_rack_name = "" # "VRACK"
default_virtual_pp_name = "" # "VPP01"
default_virtual_interface_name = "" # "VITF01"
default_company_asset = "ELEA DIGITAL INFRAESTRUTURA E REDES DE T" # "VITF01"

is_test = False
cross_to_test = {
    "RJO1": ["ID-RJO1-00001", "ID-RJO1-00002"]
    # "RJO1": ["ID-RJO1-00490"]
    # "BSB1": [ "ID-BSB1-00006" ]
}

source_translation = {
    "Side A": "Ponta A",
    "Side B": "Ponta B",
    "Jump 1": "Salto 1",
    "Jump 2": "Salto 2",
    "Jump 3": "Salto 3",
    "Jump 4": "Salto 4",
    "Jump 5": "Salto 5",
    "Jump 6": "Salto 6",
}

def parse_cross_to_snow(cross):
    type_of_cross_translation = {
        "Externo": "External",
        "Interno": "Internal"
    }

    for key in cross.keys():
        if isinstance(cross[key], list): continue 
        cross[key] = cross[key] if not pd.isna(cross[key]) else ""
    

    return {
        **cross,
        "sys_id": cross["sys_id"], 
        "u_id_cross": cross["ID Cross"].replace("-CTA-", "-CTA1-"), 
        "location": cross["Site"], 
        "company": cross["Cliente Final"], 
        "u_activation_date": cross["Data da ativação"], 
        "u_delivery_request": cross["Request"], 
        "u_innerduct_only_tlc": cross["Innerduct (only TLC)"], 
        "u_quantity_innerduct": cross["Quantity Innerduct"], 
        "u_legado": cross["Legado"], 
        "u_status": "Active" if cross["Active"] else "Deactive", 
        "u_type_of_cross": type_of_cross_translation.get(cross["Type of Cross"]), 
        "u_media_type": cross["Media type"],
        "u_review_stage": "Pending",
        "u_review": ""
    }

def parse_racks_from_cross(cross):
    def get_rack_info(item, suffix=""):
        return item["source"+suffix], {
            "u_data_hall": item["u_data_hall"+suffix],
            "name": item["u_rack"+suffix],
            "u_review_stage": "Pending",
            "u_review": ""
        }

    yield get_rack_info(cross, suffix="_a")
    for jump in cross["Jumps"]:
        yield get_rack_info(jump)
    yield get_rack_info(cross, suffix="_b")

def generator_assets_from_cross(cross):
    def get_asset_info(item, suffix=""):
        company = default_company_asset
        device_type = get_value(item, lambda x: item["device_type"+suffix], None)
        virtual = False

        if item["device_type"+suffix] == "Virtual":
            company = get_value(item, lambda x: item["u_customer"+suffix], None)
            device_type = "Patch Panel"
            virtual = True

        name = item["u_asset"+suffix]
        if ("ACX" in name or "QFX" in name) and company == "ELEA DIGITAL INFRAESTRUTURA E REDES DE T":
            name = name.replace(":", "-")

        if device_type in ["Patch Panel", "DIO"]:
            pattern = r'/(MOD|SLOT)\d+'
            name = re.sub(pattern, '', name)

        # update cross object so information matches with future extractions (e.g. u_asset in interface will match the name treated here)
        cross["u_asset"+suffix] = name
        cross["device_type"+suffix] = device_type

        return item["source"+suffix], cross,  {
            "location": cross["Site"],
            "u_rack.u_data_hall": item["u_data_hall"+suffix],
            "u_rack": item["u_rack"+suffix],
            "name": name,
            "device_type": device_type,
            "u_virtual": virtual,
            "u_company": company,
            "u_review_stage": "Pending",
            "u_review": "",
            "u_created_from_cross": cross["ID Cross"],
            "u_created_from_cross_source": item["source"+suffix],
            "origin_value": get_value(item, lambda x: x["origin_value"], None),
        }

    
    yield get_asset_info(cross, suffix="_a")
    for jump in cross["Jumps"]:
        yield get_asset_info(jump)
    yield get_asset_info(cross, suffix="_b")


def generator_interfaces_from_cross(cross):
    def get_interface_info(item, suffix=""):
        return item["source"+suffix], cross, {
            "location": cross["Site"],
            "u_asset.u_rack.u_data_hall": item["u_data_hall"+suffix],
            "u_asset.u_rack": item["u_rack"+suffix],
            "u_asset": item["u_asset"+suffix],
            "interface_name": item["u_interface"+suffix],
            "u_module": item["u_module"+suffix],
            "u_review_stage": "Pending",
            "u_review": "",
            "u_created_from_cross": cross["ID Cross"],
            "u_created_from_cross_source": item["source"+suffix]
        }

    yield get_interface_info(cross, suffix="_a") 
    for jump in cross["Jumps"]:
        yield get_interface_info(jump) 
    yield get_interface_info(cross, suffix="_b") 

def generator_wires_from_interfaces(cross, interfaces):
    # def _get_info(interface):

    sideA = next((x for x in interfaces if x[0] == "Side A"), None) 
    sideB = next((x for x in interfaces if x[0] == "Side B"), None) 

    try: 
        # Removes duplicate jumps 
        same_wire = lambda w1,w2: (
            "Jump" in w1[0] # w1 is the wire being analyzed, w2 is the sideA or sideB we are looking for duplicates of 
            and w1[1]["u_asset.u_rack.u_data_hall"] == w2[1]["u_asset.u_rack.u_data_hall"]
            and w1[1]["u_asset.u_rack"] == w2[1]["u_asset.u_rack"]
            and w1[1]["u_asset.name"] == w2[1]["u_asset.name"]
            and w1[1]["interface_name"] == w2[1]["interface_name"]
        )

        if sideA:
            interfaces = [x for x in interfaces if not same_wire(x, sideA)]
        if sideB:
            interfaces = [x for x in interfaces if not same_wire(x, sideB)]

    except Exception as error:
        print(traceback.format_exc())
        breakpoint()

    for index, current in enumerate(interfaces):
        proximo = interfaces[index+1] if index+1 < len(interfaces) else None
        if not proximo: continue
        source_a = current[0]
        current = current[1]
        source_b = proximo[0]
        proximo = proximo[1]

        u_review_stage = (
            "Problem Identified" if 
                get_value(current, lambda x: x["error"], False) 
                or 
                get_value(proximo, lambda x: x["error"], False)
            else "Pending"
        )

        # u_review = (
        #         get_value(current, lambda x: x["error"], False) 
        #         or 
        #         get_value(proximo, lambda x: x["error"], False)
        # )

        def report_error(source, side):
            msg = ""
            if "error" in side and side["error"]:
                reviewError = get_value(side, lambda x: x["crossReviewComment"], {"source":None, "origin_value":None, "msg": ""})
                msg += "---------"
                msg += f"\n{source} pendente"
                msg += f"\nOrigem: {source_translation.get(side['source'])}"
                if reviewError:  
                    if reviewError["origin_value"]: msg += f"\nValor: {reviewError['origin_value']}"
                    msg += f"\nAnálise: {reviewError['msg']}" 

                if "asset_not_found" in side:
                    msg += f"\nData Hall: {side['data_hall']}" 
                    msg += f"\nRack: {side['rack']}" 
                    msg += f"\nEquipamento: não informado." 
                    msg += f"\nInterface: {side['interface_name']} (Não criado automaticamente)" 

                msg += "\n---------"

            return msg
        
        u_review = report_error("Ponta A", current)
        u_review += report_error("Ponta B", proximo) 

        yield source_a, source_b, {
            "location": cross["Site"],
            "u_cross_connect": cross["u_id_cross"], 
            "u_cross_connect.sys_id": cross["sys_id"], 
            "u_cross_connect.u_id_cross": cross["u_id_cross"], 
            "u_created_from_cross": cross["u_id_cross"], 
            "u_created_from_cross_source": f"{source_a} => {source_b}", 
            "u_data_hall_a": get_value(current, lambda x: x["u_asset.u_rack.u_data_hall"], None),
            "u_rack_a": get_value(current, lambda x: x["u_asset.u_rack"], None),
            "u_asset_a": get_value(current, lambda x: x["u_asset"], None),
            "u_interface_a": get_value(current, lambda x: x["sys_id"], None),
            "u_interface_a.name": get_value(current, lambda x: x["interface_name"], None),
            "u_data_hall_b": get_value(proximo, lambda x: x["u_asset.u_rack.u_data_hall"], None),
            "u_rack_b": get_value(proximo, lambda x: x["u_asset.u_rack"], None),
            "u_asset_b": get_value(proximo, lambda x: x["u_asset"], None),
            "u_interface_b": get_value(proximo, lambda x: x["sys_id"], None),
            "u_interface_b.name": get_value(proximo, lambda x: x["interface_name"], None),
            "u_status": cross["u_status"],
            "u_review_stage": u_review_stage,
            "u_review": u_review,
            "u_index": index*10,
            "name": "#ERROR" if u_review_stage == "Problem Identified" else None
            # "created_from_cross": cross["u_id_cross"],
            # "created_from_cross_source": source 
        }

def validade_cross(headers, params, body):

    return
 


def post_to_snow(newStructure, logger=None):
    if not logger: logger = lambda x: print(x)

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
    
         

    cross_fields = ["u_id_cross", "name", "sys_id",
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

    asset_fields = ["location", "device_type", "name", "u_rack", "u_rack.name", "u_rack.u_data_hall", "sys_id"]
    snow_assets = get_servicenow_table_data(url_snow, "cmdb_ci_netgear", {"sysparm_display_value": True, "sysparm_fields":", ".join(asset_fields)}, token)
    snow_assets = parse_values(snow_assets)
    
    interface_fields = ["name", "u_asset.u_rack.u_data_hall",  "u_asset.u_rack", "u_asset", "u_asset.name", "u_asset.sys_id", "u_module", "interface_name", "sys_id"]
    snow_interfaces = get_servicenow_table_data(url_snow, "dscy_switchport", {"sysparm_display_value": True, "sysparm_fields":", ".join(interface_fields)}, token)
    snow_interfaces = parse_values(snow_interfaces)
    # breakpoint()

    wire_fields = ["name", "u_cross_connect", "u_cross_connect.sys_id", "u_cross_connect.u_id_cross", 
                   "sys_id", "u_created_from_cross", "u_created_from_cross_source",
                   "u_review_stage", "u_review",
                   "u_interface_a", "u_interface_a.sys_id", "u_interface_a.u_asset", "u_face_a", 
                   "u_interface_b", "u_interface_b.sys_id", "u_interface_b.u_asset", "u_face_b",
                   ]
    snow_wires = get_servicenow_table_data(url_snow, "dscy_net_wire", {"sysparm_display_value": True, "sysparm_fields":", ".join(wire_fields)}, token)
    snow_wires = parse_values(snow_wires)

    results = []
    # newStructure = newStructure[0:200]
    creation_resume = []
    for newCross in newStructure:
        problemIdentified = False 
        crossReviewComment = []
        if not newCross["Site"]: continue 
        if is_test and newCross["ID Cross"] not in cross_to_test.get(site): continue

        default_result = {
            "post_status": "ok",
            # "post_status_error_while": "",
            "post_error": "" 
        }

        corr_cross = next((x for x in snow_cross if x["u_id_cross"] == newCross["ID Cross"]), None)
        newCross["sys_id"] = corr_cross["sys_id"] if corr_cross else ""
        cross = parse_cross_to_snow(newCross)
        # if cross["u_id_cross"] in [x["u_id_cross"] for x in snow_cross]: continue

        logger(f"\n-> Working on cross {cross['u_id_cross']}")

        assets_created = []
        interfaces_created = []
        wires_created = []
        interfaces_of_cross = []
        logger(f"\tAssets")
        for source, n_cross, asset in generator_assets_from_cross(newCross):
            if not asset["name"]: 
                continue 

            cross = {**cross, **n_cross} # cross with updated properties, important to match info when creating cross (e.g. device name)
            assetLocal = (asset["u_rack.u_data_hall"], asset["u_rack"], asset["name"])
            
            corr_asset = next((x for x in snow_assets if assetLocal == (x["u_rack.u_data_hall"], x["u_rack.name"], x["name"])), None)
            if corr_asset: 
                assets_created.append(corr_asset)
                continue
            elif site == "RJO1" and "Jump" in source:
                # TODO AVALAIR CASOS DO RJO1 EM QUE SALTOS POSSUEM PREENCHIMENTO DIFERENTE PARA ESPELHAMENTO
                snow_rack = next((x for x in snow_racks if x["name"] == asset["u_rack"]), None)
                if not snow_rack: continue
                if snow_rack["u_data_hall"] != asset["u_rack.u_data_hall"]:
                    asset["u_anotacoes"] = "Identificado como espelhamento"
                    asset["u_espelhamento"] = True 


            if "Jump" in source and asset["device_type"] in ["Patch Panel", "DIO"]: asset["u_backbone"] = True
                
            asset["u_rack.name"] = asset["u_rack"]
            u_rack_sys_id =  next((x["sys_id"] for x in snow_racks if x["name"] == asset["u_rack.name"] and x["u_data_hall"] == asset["u_rack.u_data_hall"]), None)
            asset["u_rack"] = u_rack_sys_id  

            if not u_rack_sys_id:
                source_msg = f"{source_translation.get(source)}"
                if asset["origin_value"]: source_msg += f" => {asset['origin_value']}"
                error_msg = f"Rack {asset['u_rack.name']} não encontrado dentro de Data Hall {asset['u_rack.u_data_hall']}"
                msg = f"({source_msg}) {error_msg}"

                asset["u_review_stage"] = "Problem identified"
                asset["u_review"] += msg 
                cross["u_review_stage"] = "Problem identified"
                cross["u_review"] += msg 

            # if asset["u_rack.name"] == "AQ07": breakpoint()

            error = False
            errorMsg = ""
            if not asset["u_rack"]:
                error = True
                errorMsg += f"Rack {asset['u_rack.name']} não encontrado dentro de Data Hall {asset['u_rack.u_data_hall']}"

            # if not asset["name"] and asset["interface"]:

            if error:
                problemIdentified = True
                crossReviewComment.append({
                    "source": source,
                    "origin_value": asset["origin_value"],
                    "msg": errorMsg, 
                })


            # if asset["name"] == "SW MIKROTIK": breakpoint()
            if not error:
                # breakpoint()
                logger(f"\t\tCreating {asset['name']}")
                response = post_to_servicenow_table(url_snow, "cmdb_ci_netgear", asset, token, params) 
                if response["error"]:
                    asset["post_status"] = "error"
                    asset["post_error"] = response["errorMsg"]
                    logger(f"Error creating asset {asset['name']} \n {response['errorMsg']}")
                    continue
                
                asset = {**asset, **default_result}
                asset["sys_id"] = get_value(response, lambda x: x["response_http"].json()["result"]["sys_id"], None)
                snow_assets.append(asset)
                assets_created.append(asset)

        logger(f"\tInterfaces")
        for source, n_cross, interface in generator_interfaces_from_cross(newCross):
            if not interface["interface_name"]: continue

            cross = {**cross, **n_cross} # cross with updated properties, important to match info when creating cross (e.g. device name)
            interfaceLocal = (interface["u_asset.u_rack.u_data_hall"], interface["u_asset.u_rack"], interface["u_asset"], interface["interface_name"])

            # breakpoint()
            corr_interface = next((x for x in snow_interfaces if interfaceLocal == (x["u_asset.u_rack.u_data_hall"], x["u_asset.u_rack"], x["u_asset.name"], x["interface_name"])), None)
            if corr_interface:
                if "data_hall" in corr_interface:
                    corr_interface["u_asset.u_rack.u_data_hall"] = corr_interface["data_hall"] 
                    corr_interface["u_asset.u_rack.u_data_hall"] = corr_interface["data_hall"] 
                    corr_interface["u_asset.u_rack.u_data_hall"] = corr_interface["data_hall"] 
                    breakpoint()
                interfaces_of_cross.append((source, corr_interface))
                continue

            is_the_same_asset = lambda a,b: (a["u_rack.u_data_hall"] == b["u_asset.u_rack.u_data_hall"] 
                                                and a["u_rack.name"] == b["u_asset.u_rack"] 
                                                and a["name"] == b["u_asset"]
                                            )

            u_asset_name = interface["u_asset"]
            # if u_asset_name == "SW MIKROTIK": breakpoint()
            asset = next((x for x in snow_assets if is_the_same_asset(x, interface)), None)
            if not asset:
                interfaces_of_cross.append(( source, {
                    "error": True,
                    "source": source,
                    "asset_not_found": u_asset_name,
                    "u_asset.name": u_asset_name,
                    "data_hall": interface["u_asset.u_rack.u_data_hall"],
                    "u_asset.u_rack.u_data_hall": interface["u_asset.u_rack.u_data_hall"],
                    "rack": interface["u_asset.u_rack"],
                    "u_asset.u_rack": interface["u_asset.u_rack"],
                    "interface_name": interface["interface_name"],
                    "crossReviewComment": next((x for x in crossReviewComment if x["source"] == source), None)
                }))
                continue

            interface["u_asset.name"] = u_asset_name
            interface["u_asset"] = asset["sys_id"] if asset else None 
            interface["u_asset.sys_id"] = interface["u_asset"]

            # breakpoint()
            logger(f"\t\tCreating interface {interface['interface_name']}")
            response = post_to_servicenow_table(url_snow, "dscy_switchport", interface, token, params) 
            if response["error"]:
                interface["post_status"] = "error"
                interface["post_error"] = response["errorMsg"]
                logger(f"Error creating interface {interface['interface_name']} \n {response['errorMsg']}")
                continue

            # if source == "Side A": cross["u_asset_a"] = interface["u_asset"]
            # if source == "Side B": cross["u_asset_b"] = interface["u_asset"]

            interface = {**interface, **default_result}
            interface["sys_id"] = get_value(response, lambda x: x["response_http"].json()["result"]["sys_id"], None)
            interface["u_asset.u_rack.u_data_hall"] = asset["u_rack.u_data_hall"]
            interface["u_asset.u_rack"] = asset["u_rack.name"]
            interface["u_asset.u_rack"] = asset["u_rack.name"]
            snow_interfaces.append(interface)

            interfaces_created.append(interface)
            interfaces_of_cross.append((source, interface))
           

        is_same_rack = lambda a,b,suffix: (a["name"] == b["u_rack"+suffix] 
                                            and a["u_data_hall"] == b["u_data_hall"+suffix])

        is_same_asset = lambda a,b,suffix: (a["name"] == b["u_asset"+suffix] 
                                            and a["u_rack.name"] == b[f"u_rack{suffix}.name"] 
                                            and a["u_rack.u_data_hall"] == b["u_data_hall"+suffix])

        is_same_interface = lambda a,b,suffix: (a["interface_name"] == b["u_interface"+suffix] 
                                            and a["u_asset.name"] == b[f"u_asset{suffix}.name"] 
                                            and a["u_asset.u_rack"] == b[f"u_rack{suffix}.name"] 
                                            and a["u_asset.u_rack.u_data_hall"] == b["u_data_hall"+suffix])

        if not corr_cross: 
            cross["u_rack_a.name"] = cross["u_rack_a"]
            cross["u_rack_a"] = next((x["sys_id"] for x in snow_racks if is_same_rack(x, cross, "_a")), cross["u_rack_a"])
            cross["u_rack_b.name"] = cross["u_rack_b"]
            cross["u_rack_b"] = next((x["sys_id"] for x in snow_racks if is_same_rack(x, cross, "_b")), cross["u_rack_b"])

            cross["u_asset_a.name"] = cross["u_asset_a"]
            cross["u_asset_a"] = next((x["sys_id"] for x in snow_assets if is_same_asset(x, cross, "_a")), cross["u_asset_a"])
            cross["u_asset_b.name"] = cross["u_asset_b"]
            cross["u_asset_b"] = next((x["sys_id"] for x in snow_assets if is_same_asset(x, cross, "_b")), cross["u_asset_b"])

            # breakpoint()
            cross["u_interface_a.name"] = cross["u_interface_a"]
            cross["u_interface_a"] = next((x["sys_id"] for x in snow_interfaces if is_same_interface(x, cross, "_a")), None)
            cross["u_interface_b.name"] = cross["u_interface_b"]
            cross["u_interface_b"] = next((x["sys_id"] for x in snow_interfaces if is_same_interface(x, cross, "_b")), None)

            log = f"Cross gerado por script"
            # if assets_created:
            #     msg = "" 
            #     for asset in assets_created:
            #         breakpoint()
            #         # msg += f"\n({asset['source']}) {asset['name']} \n"
            #         msg += f"\n{asset['name']} \n"
            #         interface_of_asset = next((x for x in interfaces_of_cross if x["u_asset.sys_id"] == asset["sys_id"]), None)
            #         if interface_of_asset: msg += f"\t=> {interface_of_asset['interface_name']}"

            #     log += f"Equipamentos criados: \n {msg}"

            cross["u_anotacoes"] = log
            cross["u_review_stage"] = "Problem Identified" if problemIdentified else cross["u_review_stage"]
            if crossReviewComment:
                msg = ""                
                for error in crossReviewComment:
                    msg += "---------"
                    msg += f"\nOrigem: {source_translation.get(error['source'])}"
                    if error["origin_value"]: msg += f"\nValor: {error['origin_value']}"
                    msg += f"\nAnálise: {error['msg']}" 
                    msg += "\n---------"

                # errors = [x['msg'] for x in crossReviewComment]
                # cross["u_review"] = "\n".join(errors)
                cross["u_review"] = msg

            # breakpoint()
            logger(f"\tCreating cross {cross['u_id_cross']}")
            response = post_to_servicenow_table(url_snow, "u_cmdb_ci_bs_cross_connect", cross, token, params)  
            if response["error"]:
                cross["post_status"] = "error"
                cross["post_error"] = response["errorMsg"]
                logger(f"Error creating cross {cross['u_id_cross']} \n {response['errorMsg']}")
                breakpoint() 
                continue
            
            cross = {**cross, **default_result}
            cross["sys_id"] = get_value(response, lambda x: x["response_http"].json()["result"]["sys_id"], None)
            snow_cross.append(cross)
        # if cross["u_status"] == "Deactive": continue


        logger(f"\tWires")
        for source_a, source_b, wire in generator_wires_from_interfaces(cross, interfaces_of_cross):
            same_wire = lambda a,b: (
                a["u_cross_connect.sys_id"] == b["u_cross_connect.sys_id"] and
                (
                    ( a["u_interface_a.sys_id"] == b["u_interface_a"] ) 
                    or
                    ( a["u_interface_b.sys_id"] == b["u_interface_b"] ) 
                )
            )

            

            corr_wire = next((x for x in snow_wires if same_wire(x, wire)), None)
            if corr_wire: continue

            wire_conflicts = lambda wire1, wire2, suffix: (
                wire1["u_cross_connect.sys_id"] != wire2["u_cross_connect.sys_id"] and
                (
                    wire1[f"u_interface{suffix}.sys_id"] and wire2[f"u_interface{suffix}"] and # make sure they both exist    
                    wire1[f"u_interface{suffix}.sys_id"] == wire2[f"u_interface{suffix}"] and # check if they are the same
                    wire1[f"u_face{suffix}"] == wire2[f"u_face{suffix}"] # check if they are in the same side
                )
            )

            

            def try_to_connect(new_wire, existing_wires, suffix, try_front_first=True):
                try_first = "Front" if try_front_first else "Rear"
                try_second = "Rear" if try_front_first else "Front"

                new_wire[f"u_face{suffix}"] = try_first
                conflicting = [x for x in existing_wires if wire_conflicts(x, new_wire, suffix)]
                if not conflicting: return new_wire, conflicting 

                new_wire[f"u_face{suffix}"] = try_second
                conflicting += [x for x in existing_wires if wire_conflicts(x, new_wire, suffix)]

                if not conflicting: return new_wire, conflicting 

                return new_wire, conflicting 

            
            conflicting_wires = []
            
            wire, conflicting_wires_a = try_to_connect(wire, snow_wires, "_a") 
            wire, conflicting_wires_b = try_to_connect(wire, snow_wires, "_b", try_front_first=("Side" in source_b)) 
            conflicting_wires += conflicting_wires_a 
            conflicting_wires += conflicting_wires_b 
            conflicting_wires = [dict(t) for t in {tuple(d.items()) for d in conflicting_wires}] # removes duplicates

            for conf_wire in conflicting_wires :
                # logger(f"WIRE CONFLICT FOUND FOR CROSS {cross['u_id_cross']} \n When creating\n\t wire A: {wire['u_interface_a']} \n\t(TO)\n\t {wire['u_interface_b']} \n")
                # logger(f"Conflicts with existing wire \n\t wire A: {conf_wire['u_interface_a']} \n\t(TO)\n\t {conf_wire['u_interface_b']} \n")
                # logger(f"DISABLEING OLD WIRE TO CREATE NEW")
                logger(f"\t\tConflict found with cross: {conf_wire['u_cross_connect.u_id_cross']}")
                logger(f"\t\tDeactivanting old wire")

                msg = conf_wire["u_review"]
                msg += "---------"
                msg += f"\nEste fio foi desativado pois confletia com o cross {wire['u_cross_connect.u_id_cross']} ({wire['u_created_from_cross_source']})" 
                msg += "\n---------"

                conf_wire["u_status"] = "Deactive"
                payload = {
                    "u_status": "Deactive",
                    "u_review": msg 
                }
                response = patch_servicenow_record(url_snow, "dscy_net_wire", conf_wire["sys_id"], payload, token, params) 
                if response["error"]:
                    logger(f"Error updating wire {conf_wire['name']} \n {response['errorMsg']}")
                    continue

            wire["u_cross_connect.name"] = wire["u_cross_connect"]
            wire["u_cross_connect"] = cross["sys_id"]
            wire["u_cross_connect.sys_id"] = cross["sys_id"]

            # breakpoint()
            wire["u_rack_a.name"] = wire["u_rack_a"]
            wire["u_rack_a"] = next((x["sys_id"] for x in snow_racks if is_same_rack(x, wire, "_a")), wire["u_rack_a"])
            wire["u_rack_b.name"] = wire["u_rack_b"]
            wire["u_rack_b"] = next((x["sys_id"] for x in snow_racks if is_same_rack(x, wire, "_b")), wire["u_rack_a"])

            # wire["u_asset_a.name"] = wire["u_asset_a"]
            # wire["u_asset_a"] = next((x["sys_id"] for x in snow_assets if is_same_asset(x, wire, "_a")), wire["u_asset_a"])
            # wire["u_asset_b.name"] = wire["u_asset_b"]
            # wire["u_asset_b"] = next((x["sys_id"] for x in snow_assets if is_same_asset(x, wire, "_b")), wire["u_asset_a"])

            # wire["u_interface_a.name"] = wire["u_interface_a"]
            # wire["u_interface_a"] = next((x["sys_id"] for x in snow_interfaces if is_same_interface(x, wire, "_a")), None)
            # wire["u_interface_b.name"] = wire["u_interface_b"]
            # wire["u_interface_b"] = next((x["sys_id"] for x in snow_interfaces if is_same_interface(x, wire, "_b")), None)
            # breakpoint()
                
            logger(f"\t\tCreating {source_a} to {source_b}") 
            response = post_to_servicenow_table(url_snow, "dscy_net_wire", wire, token, params)
            if response["error"]:
                wire["post_status"] = "error"
                wire["post_error"] = response["errorMsg"]
                logger(f"Error creating wire for cross {cross['u_id_cross']} \n {response['errorMsg']}")
                continue

            wire = {**wire, **default_result}
            wire["sys_id"] = get_value(response, lambda x: x["response_http"].json()["result"]["sys_id"], None)
            wire["u_interface_a.sys_id"] = wire["u_interface_a"]
            wire["u_interface_b.sys_id"] = wire["u_interface_b"]

            wires_created.append(wire)
            snow_wires.append(wire)

        
        creation_resume.append({
            **cross,
            "assets": assets_created,
            "interfaces": interfaces_created,
            "wires": wires_created
        })

    return creation_resume

        # breakpoint()
            

def create_new_structure(path, fileName, oldCross):
    df = get_df_from_excel(path+fileName).fillna("")
    df_old_cross = get_df_from_excel(path+oldCross)
    
    if df.empty: 
        print(f"File {fileName} not found")
        return
    
    def _get_interface_info(asset):
        interface = get_value(asset, lambda x: x["Interface"], default_virtual_interface_name)
        mod = ""
        # matches = re.findall(r"MODX|MOD\d+", interface)
        pattern = r'(?:(MOD\d+)[/-])?(PT\d+-\d+)'
        match = re.search(pattern, interface)
        if match:
            mod = get_value(match, lambda x: x[1].replace("MOD", ""), None)
            interface = get_value(match, lambda x: x[2], None)

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
            "origin_value": get_value(asset, lambda x: x["origin_value"], None),
        }

        return hop 


    newStructure = []
    dict_old_crosses = df_old_cross.to_dict(orient="records")
    # breakpoint()
    for idCross in df["ID Cross"].unique():
        df_info = df[df["ID Cross"] == idCross]

        sort_mapping = {"Side A": 0, "Jump 1": 1, "Jump 2": 2, "Jump 3": 3, "Jump 4": 4, "Jump 5": 5, "Jump 6": 6, "Side B": 100}
        df_info["sort_value"] = df_info["source"].map(sort_mapping)
        df_info = df_info.sort_values(by="sort_value")
        del df_info["sort_value"] 

        dict_info = df_info.to_dict(orient="records")
        # old_cross = df_old_cross[df_old_cross["ID Cross"] == idCross]
        dict_old_cross = next((x for x in dict_old_crosses if x["ID Cross"] == idCross), None)

        data_ativacao = get_value(dict_old_cross, lambda x: x["Activation Date"], None)
        if pd.isnull(data_ativacao): data_ativacao = None
        else: data_ativacao = data_ativacao.isoformat()

        request = get_value(dict_old_cross, lambda x: x["Request"], None)
        if pd.isna(request): request = None

        # if idCross == "ID-RJO1-00009": breakpoint()
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
            "Type of Cross": get_value(dict_old_cross, lambda x: x["Type of Cross"], None) ,
            "Media type": get_value(dict_old_cross, lambda x: x["Media type"], None),
            **extract_side("Side A", dict_info),
            **extract_side("Side B", dict_info),
            "Jumps": [
                extract_hop(x) for x in dict_info if "Jump" in x["source"] 
            ]
        }

        newStructure.append(cross)

    return newStructure

def get_str(data):
    string = ""
    try:
        string = str(data, "utf8")
    except Exception as e:
        string = str(data)

    return string

def save_log(data, path, name):
    data = get_str(data)
    data = f"\n{data if data else ''}"
    save_file(f'{path}', contentToSave=data, fileName=f"{name}.txt")

def remove_file(path, name):
    folderDate = datetime.now().strftime("%d_%m_%Y-%Hhrs")
    try:
        os.remove(f'{path}/{name}.txt')
    except OSError:
        pass

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
        dateName = datetime.now().strftime("%d_%m_%Y-%Hhrs")
        def logger(msg):
            save_log(msg, f"{path}/post_logs/overview", f"{site}_{dateName}.txt",)
            print(msg)

        # newStructure = newStructure[0:50] # TESTS
        creation_resume = post_to_snow(newStructure, logger)
        with open(f"{path}/post_logs/{site}_creation_resume_{dateName}.json", 'w', encoding='utf-8') as f:
            json.dump(creation_resume, f, ensure_ascii=False, indent=4)



        # df_result.to_excel(f"{path}/{site}_post_result.xls", index=False)