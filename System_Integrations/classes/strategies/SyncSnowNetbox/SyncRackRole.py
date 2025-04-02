from commons.utils.chunks import process_chunks
from commons.utils.dicts import clear_props
from .BaseSync import BaseSync
from typing import List
from commons.utils.parser import get_value
from System_Integrations.utils.netbox_api import create_racks, update_racks


mapping_role = {
    ""
}


class SyncRackRole(BaseSync): 
    def _extract_data_a(self, aData:list=[]):
        aExtracted = []
        for item in aData:
            aExtracted.append({
                "item": item,
                "extracted_info": {
                    "name": get_value(item, lambda x: x["u_type"], None),
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
        site = get_value(item, lambda x: x["u_data_hall.u_site"]["display_value"], None)
        location = get_value(item, lambda x: x["u_data_hall"]["display_value"], None)

        return {
            "name": get_value(item, lambda x: x["name"], None),
            "site": { "name": site },
            "location": { "name": location },
            "status": "active",
        }
    
    def _map_update_b(self, item_a, item_b, data_b):
        return {
            **item_b,
            "name": get_value(item_a, lambda x: x["name"], None),
        }

    def sync_new(self, baseUrl:str, data:List, headers):
        data = data["data_b"]

        processor = lambda chunk: [create_racks(baseUrl, x, headers) for x in chunk]
        results = process_chunks(data, processor, chunk_size=2, delay=0.3, should_print=False)
        
        return {
            "result_a": [],
            "result_b": results
        }

    def sync_update(self, baseUrl:str, data:List, headers):
        props_to_avoid = ["_depth", "display", "url"]
        for i, item_b in enumerate(data["data_b"]):
            data["data_b"][i] = {
                **item_b,
                "location": clear_props(item_b["location"], props_to_avoid),
                "role": clear_props(item_b["role"], props_to_avoid),
                "tenant": clear_props(item_b["tenant"], props_to_avoid),
                "site": clear_props(item_b["site"], props_to_avoid),
                "status": get_value(item_b, lambda x: x["status"]["value"], None),
            }

        return {
            "result_a": [],
            "result_b": [update_racks(baseUrl, x, headers) for x in data["data_b"]]
        }

    def sync_delete(self, baseUrl:str, data:List, headers):
        return []


    def get_display_string_b(self, item_b):
        dh = get_value(item_b, lambda x: x["location"]["name"], None)
        return f"{f'Data Hall: {dh} => Rack ' if dh else ''}{item_b['name']}"
