import os
import re
from abc import ABC, abstractmethod
from random import randint
from System_Integrations.classes.requests.zabbix.dataclasses import Host, Item, Read, EnumReadType
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.dataclasses import SnowLink
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from dotenv import load_dotenv
from System_Integrations.utils.parser import group_by

load_dotenv(override=True)

class ISnowProductLinks(ABC):
    
    def auth(self):
        # TODO get secrets from safe
        self.snow_url = os.getenv("snow_url")
        self.snow_client_id = os.getenv("snow_client_id")
        self.snow_client_secret = os.getenv("snow_client_secret")
        self.snow_refresh_token = os.getenv("snow_refresh_token")
        self.token = get_servicenow_auth_token(self.snow_url, self.snow_client_id, self.snow_client_secret, self.snow_refresh_token)

    def get_accounts(self):
        clients_fields = ["sys_id, name, number"]
        accounts = get_servicenow_table_data(self.snow_url, "customer_account", {"sysparm_display_value": True, "sysparm_fields":", ".join(clients_fields)}, self.token)
        return accounts

    def get_product_links(self):
        fields = ["sys_id", "u_customer", "u_customer.sys_id", "u_device", "u_interface", "u_link_cid", "u_link_name", "u_link_type"]
        accounts = get_servicenow_table_data(self.snow_url, "u_temp_customer_links", {"sysparm_display_value": True, "sysparm_fields":", ".join(fields)}, self.token)
        return accounts

    def get_most_recent_read(self):
        pass

    def get_most_recent_read_trend(self):
        pass

    def process_items_product_links(self, items:list[Item], snow_accounts, netbox_tenants, snow_links):
        acct_config_name = [x for x in netbox_tenants if x["custom_fields"]["config_name"]] # tenants that have config name setted
        acct_config_name = [( # Transforms it into a tuple of (<ACCT>, <List of the config options>)
                                x["custom_fields"]["number"], 
                                list(map(str.lstrip, x["custom_fields"]["config_name"].upper().split(",")))
                            ) for x in acct_config_name]
        aItems:list[Item] = []
        for item in items:
            acct = ""
            config_name_found = ""

            read_type = ""
            match = re.search(r"(Bits received|Bits sent)", item[1])
            if match: read_type = match.group(1)
            
            interface = get_value(item, lambda x: x[1].split(' ')[1].split('(')[0], None)
            if not interface: continue
            if re.search(r"^(Vlan.*|^.*\.\d+$)$", interface): continue # starts with Vlan or ends with <string>.<number>
            
            cid = ""
            if "ACCT" in item[1]:
                cid = get_value(item, lambda x: x[0].split(" - ")[1], "")
                acct = get_value(item, lambda x: x[1].split(" - ")[1], None)
                config_name_found = next((x[1][0] for x in acct_config_name if acct == x[0]), None)

            else:
                config_name_found = get_value(item, lambda x: x[1].split(" - ")[1], None)
                if config_name_found:
                    acct = next((x[0] for x in acct_config_name if config_name_found.upper() in x[1]), None)
                    
            account = next((x for x in snow_accounts if x["number"] == acct), None)
            if not account:
                print("not found", config_name_found, item[1])

            linkType = None
            if "Elea Connect" in item[1]: linkType = "Elea Connect"
            elif "Elea Metro Connect" in item[1]: linkType = "Elea Metro Connect"
            elif "Elea OnRamp" in item[1]: linkType = "Elea On Ramp"
            else:
                # cid = item[1].split(" - ")[0]
                if "IC" in cid: linkType = "Elea Connect"
                elif "MC" in cid: linkType = "Elea Metro Connect"
                elif "OR" in cid: linkType = "Elea On Ramp"

            need_cid = False
            # TEMP: generates a temp cid, while definitive solution is still on the works
            if not cid:
                need_cid = True
                length = 8
                rdm = randint(10**(length-1), (10**length)-1)
                temp_cid = f"{config_name_found}"
                if linkType: temp_cid += f" - {linkType}"
                temp_cid += f" - {rdm}"
                cid = temp_cid

            snowLink = None
            corrLink = next((x for x in snow_links if x["u_link_name"] == cid), None)
            # if item[5] == "PSP-ELEAD-RJO1-QFX-01" and interface == "ge-0/0/15": breakpoint()
            # if item[5] == "PSP-ELEAD-RJO1-QFX-01": breakpoint()
            if not corrLink:
                corrLink = next((x for x in snow_links if 
                                # x["u_customer"] == account["name"] and
                                x["u_device"] == item[5] and
                                x["u_interface"] == interface
                            ), None)

            if corrLink:
                # "u_customer", "u_device", "u_interface", "u_link_cid", "u_link_name", "u_link_type"
                snowLink = SnowLink(
                    acct = corrLink["u_customer"]["display_value"] if corrLink["u_customer"] else None,
                    account_sys_id = corrLink["u_customer.sys_id"] if "u_customer.sys_id" in corrLink else None,
                    client_display_name = config_name_found,
                    cid = corrLink["u_link_name"],
                    linkType = corrLink["u_link_type"],
                    sys_id = corrLink["sys_id"],
                )
            else:
                snowLink = SnowLink(
                    acct = get_value(account, lambda x: x["number"], None),
                    account_sys_id = get_value(account, lambda x: x["sys_id"], None),
                    client_display_name = config_name_found,
                    cid = cid,
                    linkType = linkType
                )

            aItems.append(Item(
                id = item[0],
                name = item[1],
                interfaceName = interface,
                host = Host(
                    id = item[4],
                    name = item[5],
                ),
                snowLink = snowLink,
                readType = read_type,
            ))

        return aItems

    def process_history_total_traffic(self, reads:list[Read]):
        data = []
        for read in reads:
            if not read.item.snowLink.sys_id: continue

            data.append({
                "u_value": read.value,
                "u_time": read.timeStr,
                "u_link": read.item.snowLink.sys_id
            })

        return data

    def process_trend_total_traffic(self, reads:list[Read]):
        pass

    def post_product_links(self, items:list[Item]):
        grouped_items = group_by(items, ["cid"])
        breakpoint()
        aLinks = []
        for key in grouped_items.keys():
            item = grouped_items[key]
            aLinks.append({
                "u_customer": item[0].snowLink.account_sys_id,
                "u_device": item[0].host.name,
                "u_interface": item[0].interfaceName,
                "u_link_cid": item[0].snowLink.cid,
                "u_link_name": item[0].snowLink.cid,
                "u_link_type": item[0].snowLink.linkType,
                "original_items": item
            })
        


    def post_total_traffic_reads(self, reads:list[Read]):
        pass

    def post_total_traffic_reads_trends(self, reads:list[Read]):
        pass