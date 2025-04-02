import re

from commons.pandas.utils import remove_acento
from commons.utils.dicts import clear_props
from commons.utils.snow import get_link
from .BaseSync import BaseSync
from typing import List
from commons.utils.parser import get_value
from System_Integrations.utils.netbox_api import create_data_halls, update_data_halls

class SyncDataHall(BaseSync): 
    def _extract_data_a(self, aData:list=[]):
        aExtracted = []
        for item in aData:
            aExtracted.append({
                "item": item,
                "extracted_info": {
                    "name": get_value(item, lambda x: x["name"], "").lower(),
                    "site": get_value(item, lambda x: x["u_site"]["name"], None),
                }
            })

        return aExtracted
    
    def _extract_data_b(self, aData:list=[]):
        aExtracted = []
        for item in aData:
            aExtracted.append({
                "item": item,
                "extracted_info": {
                    "name": get_value(item, lambda x: x["name"], "").lower(),
                    "site": get_value(item, lambda x: x["site"]["display_value"], None),
                }
            })

        return aExtracted
    
    def _map_new_b(self, item, data_b):
        name = get_value(item, lambda x: x["name"], "")
        site = get_value(item, lambda x: x["u_site"]["display_value"], None)
        if not site:
            parts = name.split("-") # the pattern for the name of the data hall contains the site name. e.g.: POA1-1-DH01
            site = parts[0] if len(parts) == 3 else None

        return {
            "name": name,
            "slug": re.sub(r'[^a-z0-9]+', '-', remove_acento(name.lower())),  
            "site": {"name": site},
            "status": "active",
            "custom_fields": {
                "dh_snow_sys_id": get_value(item, lambda x: x["sys_id"], None),
                "dh_snow_link": get_link("u_cmdb_ci_data_hall", item["sys_id"], self.base_url_a)
            }
        }
    
    def _map_update_b(self, item_a, item_b, data_b):
        name = get_value(item_a, lambda x: x["name"], "")
        site = get_value(item_a, lambda x: x["u_site"]["display_value"], None)
        if not site:
            parts = name.split("-") # the pattern for the name of the data hall contains the site name. e.g.: POA1-1-DH01
            site = parts[0] if len(parts) == 3 else None

        return {
            **item_b,
            "name": name,
            "slug": re.sub(r'[^a-z0-9]+', '-', remove_acento(name.lower())),  
            "site": {**item_b["site"], "name": site},
            "status": {**item_b["status"], "value": "active"},
            "custom_fields": {
                **item_b["custom_fields"],
                "dh_snow_sys_id": get_value(item_a, lambda x: x["sys_id"], None),
                "dh_snow_link": get_link("u_cmdb_ci_data_hall", item_a["sys_id"], self.base_url_a)
            }
        }

    def sync_new(self, baseUrl:str, data:List, headers):
        data = data["data_b"]
        return {
            "result_a": [],
            "result_b": [create_data_halls(baseUrl, x, headers) for x in data]
        }

    def sync_update(self, baseUrl:str, data:List, headers):
        props_to_avoid = ["_depth", "display", "url"]
        for i, item_b in enumerate(data["data_b"]):
            data["data_b"][i] = {
                **item_b,
                "tenant": clear_props(item_b["tenant"], props_to_avoid),
                "site": clear_props(item_b["site"], props_to_avoid),
                "status": get_value(item_b, lambda x: x["status"]["value"], None),
            }

        return {
            "result_a": [],
            "result_b": [update_data_halls(baseUrl, x, headers) for x in data["data_b"]]
        }

    def sync_delete(self, baseUrl:str, data:List, headers):
        return []


    def get_display_string_b(self, item_b):
        site = get_value(item_b, lambda x: x["site"]["name"], None)
        return f"{f'Site {site} => Data Hall ' if site else ''}{item_b['name']}"