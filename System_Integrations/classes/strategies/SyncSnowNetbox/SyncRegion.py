import re

from commons.pandas.utils import remove_acento
from .BaseSync import BaseSync
from typing import List
from commons.utils.parser import get_value
from System_Integrations.utils.netbox_api import create_regions, create_sites, update_regions, update_sites

class SyncRegion(BaseSync): 
    """
    Snow (cmn_location) ==> (regions) Netbox

    (A) Snow
    (B) Netbox    

    Implemented to be used as directional, data always go from Snow to Netbox
    """
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
        return {
            "name": name,
            "slug": re.sub(r'[^a-z0-9]+', '-', remove_acento(name.lower())),
        }
    
    def _map_update_b(self, item_a, item_b, data_b=[]):
        return {
            **item_b,
            "name": get_value(item_a, lambda x: x["name"], None),
        }

    def sync_new(self, baseUrl:str, data:List, headers):
        data = data["data_b"]
        return {
            "result_a": [],
            "result_b": create_regions(baseUrl, data, headers)
        }

    def sync_update(self, baseUrl:str, data:List, headers):
        data = data["data_b"]
        return {
            "result_a": [],
            "result_b": update_regions(baseUrl, data, headers)
        }

    def sync_delete(self, baseUrl:str, data:List, headers):
        return []


    def get_display_string_b(self, item_b):
        return f"{item_b['name']}"