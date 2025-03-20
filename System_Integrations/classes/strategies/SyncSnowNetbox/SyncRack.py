from commons.utils.chunks import process_chunks
from commons.utils.dicts import clear_props
from commons.utils.snow import get_link
from .BaseSync import BaseSync
from typing import List
from commons.utils.parser import get_value
from System_Integrations.utils.netbox_api import create_racks, update_racks

class SyncRack(BaseSync): 
    status_mapping = {
        "Occupied": "active",
        "Ocupado": "active",
        "Available": "available",
        "Livre": "available",
        "(300)": "reserved",
        "Em implantação": "reserved",
        "Unusable": "deprecated",
        "Inutilizável": "deprecated",
    }

    def _extract_data_a(self, aData:list=[]):
        aExtracted = []
        for item in aData:
            aExtracted.append({
                "item": item,
                "extracted_info": {
                    "name": get_value(item, lambda x: x["name"], None),
                    "data_hall": get_value(item, lambda x: x["u_data_hall"]["display_value"], None),
                    "site": get_value(item, lambda x: x["u_data_hall.u_site"]["display_value"], None),
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
                    "data_hall": get_value(item, lambda x: x["location"]["name"], None),
                    "site": get_value(item, lambda x: x["site"]["name"], None),
                }
            })

        return aExtracted
    
    def _map_new_b(self, item, data_b):
        site = get_value(item, lambda x: x["u_data_hall.u_site"]["display_value"], None)
        location = get_value(item, lambda x: x["u_data_hall"]["display_value"], None)
        tenant = get_value(item, lambda x: x["tenant"]["name"], None)
        status = get_value(item, lambda x: x["install_status"], None)
        status = self.status_mapping.get(status)

        u_height = get_value(item, lambda x: x["rack_units"], "0")
        if u_height == "0" or u_height == 0 or not u_height: 
            u_height = 1

        description = get_value(item, lambda x: x["short_description"], "")
        description = description.strip()

        return {
            "name": get_value(item, lambda x: x["name"], None),
            "site": { "name": site },
            "location": { "name": location },
            "tenant": { "name": tenant } if tenant else None,
            "status": status if status else "active",
            "description": description,
            "u_height": u_height,
            "custom_fields": {
                "rack_snow_sys_id": get_value(item, lambda x: x["sys_id"], None),
                "rack_snow_link": get_link("cmdb_ci_rack", item["sys_id"])
            },
        }
    
    def _map_update_b(self, item_a, item_b, data_b):
        if item_a.get("sys_id", 1) != item_b.get("custom_fields").get("rack_snow_sys_id", 2):
            return

        site = get_value(item_a, lambda x: x["u_data_hall.u_site"]["display_value"], None)
        location = get_value(item_a, lambda x: x["u_data_hall"]["display_value"], None)
        status = get_value(item_a, lambda x: x["install_status"], None)
        status = self.status_mapping.get(status)

        # its better to just always override the description, maybe revisit in the future
        description_a = get_value(item_a, lambda x: x["short_description"], "")
        description_a = description_a.strip()
        # description_b = get_value(item_b, lambda x: x["description"], "")
        # if description_a != description_b and description_a not in description_b:
        #     description_b += f"\n{description_a}"

        u_height = get_value(item_b, lambda x: x["u_height"], None)
        u_height = get_value(item_a, lambda x: x["rack_units"], u_height)
        if u_height == "0" or u_height == 0 or not u_height: u_height = 1

        if u_height:
            u_height = int(u_height)

        tenant = get_value(item_a, lambda x: x["tenant"], None)
        
        return {
            **item_b,
            "name": get_value(item_a, lambda x: x["name"], None),
            "site": { 
                **item_b["site"],
                "name": site
            },
            "location": {
                **item_b["location"],
                "name": location 
            },
            "tenant": {
                **item_b["tenant"],
                "name": tenant.get("name", None) 
            } if ( tenant and item_b["tenant"] ) else None,
            "status": {
                **item_b["status"],
                "value": status if status else "active"
            },
            "description": description_a,
            "u_height": u_height,
            "custom_fields": {
                "rack_snow_sys_id": get_value(item_a, lambda x: x["sys_id"], None),
                "rack_snow_link": get_link("cmdb_ci_rack", item_a["sys_id"])
            },
        }

    def sync_new(self, baseUrl:str, data:List, headers):
        data = data["data_b"]

        processor = lambda chunk: [create_racks(baseUrl, x, headers) for x in chunk]
        results = process_chunks(data, processor, chunk_size=20, delay=0.5, should_print=False)
        
        return {
            "result_a": [],
            "result_b": results
        }

    def sync_update(self, baseUrl:str, data:List, headers):
        props_to_avoid = ["_depth", "display", "url"]
        for i, item_b in enumerate(data["data_b"]):
            obj = {
                **item_b,
                "width": get_value(item_b, lambda x: x["width"]["value"], None),
                "location": clear_props(item_b["location"], props_to_avoid),
                "tenant": clear_props(item_b["tenant"], props_to_avoid),
                "site": clear_props(item_b["site"], props_to_avoid),
                "status": get_value(item_b, lambda x: x["status"]["value"], None),
            }

            if obj.get("type", None) == None: 
                del obj["type"]

            if obj.get("weight_unit", None) == None: 
                del obj["weight_unit"]

            data["data_b"][i] = obj

        data = data["data_b"]
        processor = lambda chunk: [update_racks(baseUrl, x, headers) for x in chunk]
        results = process_chunks(data, processor, chunk_size=20, delay=0.5, should_print=False)

        return {
            "result_a": [],
            "result_b": results 
        }

    def sync_delete(self, baseUrl:str, data:List, headers):
        return []


    def get_display_string_b(self, item_b):
        dh = get_value(item_b, lambda x: x["location"]["name"], None)
        return f"{f'Data Hall: {dh} => Rack ' if dh else ''}{item_b['name']}"