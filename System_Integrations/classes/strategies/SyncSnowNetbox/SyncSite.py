import re

from commons.pandas.utils import remove_acento
from commons.utils.dicts import clear_props
from commons.utils.snow import get_link
from .BaseSync import BaseSync
from typing import List
from commons.utils.parser import get_value
from System_Integrations.utils.netbox_api import create_sites, update_sites

class SyncSite(BaseSync): 
    def _extract_data_a(self, aData:list=[]):
        aExtracted = []
        for item in aData:
            aExtracted.append({
                "item": item,
                "extracted_info": {
                    "name": get_value(item, lambda x: x["name"], None),
                }
            })

        return aExtracted
    
    def _extract_data_b(self, aData:list=[]):
        aExtracted = []
        for item in aData:
            aExtracted.append({
                "item": item,
                "extracted_info": {
                    "name": get_value(item, lambda x: x["name"], None),
                }
            })

        return aExtracted
    
    def _map_new_b(self, item, data_b):
        name = get_value(item, lambda x: x["name"], None)
        zip = get_value(item, lambda x: x["zip"], "")
        street = get_value(item, lambda x: x["street"], "")
        city = get_value(item, lambda x: x["city"], "")
        state = get_value(item, lambda x: x["state"], "")
        latitude = get_value(item, lambda x: x["latitude"], "")
        if len(latitude) > 8: 
            latitude = float(latitude)
            latitude = round(latitude, 6)
        longitude = get_value(item, lambda x: x["longitude"], "")
        if len(longitude) > 8: 
            longitude = float(longitude)
            longitude = round(longitude, 6)

        physical_address = ""
        if street: physical_address += f"{street}"
        if city: physical_address += f", {city} {f'- {state}' if state else ''}"  
        if zip: physical_address += f", {zip}"  
        physical_address = physical_address.strip()

        return {
            "name": name,
            "slug": re.sub(r'[^a-z0-9]+', '-', remove_acento(name.lower())),  
            "region": { "name": name[0:3] },
            "physical_address": physical_address,
            "latitude": latitude if latitude else None,
            "longitude": longitude if longitude else None,
            "custom_fields": {
                "location_snow_sys_id": get_value(item, lambda x: x["sys_id"], None),
                "location_snow_link": get_link("cmn_location", item["sys_id"], self.base_url_a)
            }
        }
    
    def _map_update_b(self, item_a, item_b, data_b=[]):
        zip = get_value(item_a, lambda x: x["zip"], "")
        street = get_value(item_a, lambda x: x["street"], "")
        city = get_value(item_a, lambda x: x["city"], "")
        state = get_value(item_a, lambda x: x["state"], "")
        latitude = get_value(item_a, lambda x: x["latitude"], "")
        if len(latitude) > 8: 
            latitude = float(latitude)
            latitude = round(latitude, 6)
        longitude = get_value(item_a, lambda x: x["longitude"], "")
        if len(longitude) > 8: 
            longitude = float(longitude)
            longitude = round(longitude, 6)


        physical_address = ""
        if street: physical_address += f"{street}"
        if city: physical_address += f", {city} {f'- {state}' if state else ''}"  
        if zip: physical_address += f", {zip}"  
        physical_address = physical_address.strip()

        return {
            **item_b,
            "name": get_value(item_a, lambda x: x["name"], None),
            "physical_address": physical_address,
            "latitude": latitude if latitude else None,
            "longitude": longitude if longitude else None,
            "custom_fields": {
                **item_b["custom_fields"],
                "location_snow_sys_id": get_value(item_a, lambda x: x["sys_id"], None),
                "location_snow_link": get_link("cmn_location", item_a["sys_id"], self.base_url_a)
            }
        }

    def sync_new(self, baseUrl:str, data:List, headers):
        data = data["data_b"]
        return {
            "result_a": [],
            "result_b": [create_sites(baseUrl, x, headers) for x in data]
        }

    def sync_update(self, baseUrl:str, data:List, headers):
        props_to_avoid = ["_depth", "display", "url"]
        for i, item_b in enumerate(data["data_b"]):

            data["data_b"][i] = {
                **item_b,
                "group": clear_props(item_b["group"], props_to_avoid),
                "region": clear_props(item_b["region"], props_to_avoid),
                "status": get_value(item_b, lambda x: x["status"]["value"], None),
            }

        return {
            "result_a": [],
            "result_b": [update_sites(baseUrl, x, headers) for x in data["data_b"]]
        }

    def sync_delete(self, baseUrl:str, data:List, headers):
        return []

    def get_display_string_b(self, item_b):
        return f"{item_b['name']}"