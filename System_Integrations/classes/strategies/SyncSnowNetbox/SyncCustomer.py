from collections import defaultdict
import re


from commons.pandas.utils import remove_acento
from commons.utils.dicts import clear_props
from commons.utils.snow import get_link
from .BaseSync import BaseSync
from typing import List
from commons.utils.parser import get_value
from System_Integrations.utils.netbox_api import create_tenants, update_tenants

class SyncCustomer(BaseSync):
    """
    Snow (customer_account) ==> (tenants) Netbox

    (A) Snow
    (B) Netbox    

    Implemented to be used as directional, data always go from Snow to Netbox
    """
    def _extract_data_a(self, aData:list=[]): # Snow
        aExtracted = []
        for item in aData:
            aExtracted.append({
                "item": item,
                "extracted_info": {
                    # "name": get_value(item, lambda x: x["name"], None), # compare only acct, to update name
                    "number": get_value(item, lambda x: x["number"], None),
                }
            })

        return aExtracted
    
    def _extract_data_b(self, aData:list=[]): # netbox
        aExtracted = []
        for item in aData:
            aExtracted.append({
                "item": item,
                "extracted_info": {
                    # "name": get_value(item, lambda x: x["name"], None), # compare only acct, to update name
                    "number": get_value(item, lambda x: x["custom_fields"]["number"], None)
                }
            })

        return aExtracted
    

    #
    # Utils
    #
    def _build_name(self, item_a, item_b=None):
        # check if in item_a theres the field city and state
        # Use in this order o priority to add it to the end of the name
        breakpoint()
        city = item_a.get("city", "")
        state = item_a.get("state", "")

        if city:
            name = f"{item_a['name']} {city}"
        elif state:
            name = f"{item_a['name']} {state}"
        else:
            name = item_a["name"]

        return re.sub(r'[^a-z0-9]+', '-', remove_acento(name.lower()))

    def _build_nickname(self, item_a, item_b=None):
        name = item_a["name"] or ""

        nickname = item_a.get("u_nickname", "")
        nickname = nickname.split(",")[0]

        if not nickname and item_b:
            nickname = get_value(item_b, lambda x: x["custom_fields"]["config_name"], "")
            nickname = nickname or ""
            nickname = nickname.split(",")[0]

        if not nickname and item_a.get("account_parent", None):
            nickname = name
            city = item_a.get("city", "")
            state = item_a.get("state", "")
            country = item_a.get("country", "")

            if city:
                nickname = f"{nickname} {city}"
            elif state:
                nickname = f"{nickname} {state}"
            elif country:
                nickname = f"{nickname} {country}"

        if not nickname: nickname = name

        return nickname.strip()

    def _merge_nicknames(self, item_a, item_b):
        curr_nickname = get_value(item_b, lambda x: x["custom_fields"]["config_name"], "") or ""
        u_nickname = get_value(item_a, lambda x: x["u_nickname"], "") or ""
        curr_nickname = curr_nickname.split(",")
        u_nickname = u_nickname.split(",")
        curr_nickname += u_nickname
        curr_nickname = list(dict.fromkeys(curr_nickname))
        curr_nickname = [x for x in curr_nickname if x.strip()]
        curr_nickname = ",".join(curr_nickname)
        return curr_nickname


    def _map_new_b(self, item_a, data_b=[]):
        nickname = self._build_nickname(item_a)

        name = nickname
        slug = re.sub(r'[^a-z0-9]+', '-', remove_acento(nickname.lower()))

        obj = {
            "name": name,
            "slug": slug,
            "custom_fields": {
                "config_name": item_a["u_nickname"],
                "number": item_a["number"],
                "customer_snow_link": get_link("customer_account", item_a["sys_id"])
            }
        }

        data_b_no_self = data_b # if it is a new item, the list will not contain it already
        self.make_unique([obj], data_b_no_self, "name", lambda val, item: f"{val} ({item['custom_fields']['number']})")
        self.make_unique([obj], data_b_no_self, "slug", lambda val, item: f"{val}-{item['custom_fields']['number']}")
        
        return obj

    def _map_update_b(self, item_a, item_b, data_b=[]):
        nickname = self._build_nickname(item_a, item_b)
        name = item_b.get("name", nickname)

        # Merge nicknames from both systems 
        nicknames = self._merge_nicknames(item_a, item_b)
        
        obj = {
            **item_b,
            "name": name,
            "custom_fields": {
                **item_b["custom_fields"],
                "config_name": nicknames,
                "number": item_a["number"],
                "customer_snow_link": get_link("customer_account", item_a["sys_id"])
            }
        }

        data_b_no_self = [x for x in data_b if x["id"] != obj["id"]]
        self.make_unique([obj], data_b_no_self, "name", lambda val, item: f"{val} ({item['custom_fields']['number']})")
        self.make_unique([obj], data_b_no_self, "slug", lambda val, item: f"{val}-{item['custom_fields']['number']}")

        return obj

    def make_unique(self, items, all_data, key, on_dup):
        """Modify duplicates in a list of dictionaries to make them unique based on a key, using ID."""
        seen = defaultdict(list)
        
        for item in items:
            val = item[key]
            seen[val].append(item)

        for item in all_data:
            val = item[key]
            seen[val].append(item)            
        
        for val, group in seen.items():
            if len(group) > 1:  # If duplicates exist
                for item in group:
                    item[key] = on_dup(val, item)

    def make_data_unique(self, lst, all_data=[]):
        self.make_unique(lst["data_b"], 
                    "name", 
                    lambda val, item: 
                        f"{val} ({get_value(item, lambda x: x['custom_fields']['number'], '')})"
                )
        self.make_unique(lst["data_b"],
                    "slug", 
                    lambda val, item: 
                        f"""{val}{
                            get_value(item, lambda x: '-'+x['custom_fields']['number'] if x['custom_fields']['number'] else '', '')
                        }"""
                )

        return lst


    def sync_new(self, baseUrl:str, data:List, headers):
        data = data["data_b"]

        

        return {
            "result_a": [],
            "result_b": [create_tenants(baseUrl, x, headers) for x in data] 
        }

    def sync_update(self, baseUrl:str, data:List, headers):
        # final fixes to make the http request work are done here
        # this is important because the data in the extract_data should only update the values so that it is possible to identify if there were any real changes made
        props_to_avoid = ["_depth", "display", "url"]
        for i, item_b in enumerate(data["data_b"]):
            data["data_b"][i] = {
                **item_b,
                "group": clear_props(item_b["group"], props_to_avoid),
            }

        return {
            "result_a": [],
            "result_b": [update_tenants(baseUrl, x, headers) for x in data["data_b"]] 
        }

    def sync_delete(self, baseUrl:str, data:List, headers):
        return []
        
    def get_display_string_b(self, item_b):
        return f"{item_b['name']} - {item_b['custom_fields']['number']}"