import os
from abc import ABC, abstractmethod
import re
from System_Integrations.classes.requests.zabbix.dataclasses import Host, Item, Read
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.dataclasses import SnowLink
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from dotenv import load_dotenv

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

    def get_most_recent_read(self):
        pass

    def get_most_recent_read_trend(self):
        pass

    def process_items_product_links(self, items:list[Item], snow_accounts, netbox_tenants):
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
            
            if "ACCT" in item[1]:
                cid = get_value(item, lambda x: x[0].split(" - ")[1], None)
                acct = get_value(item, lambda x: x[1].split(" - ")[1], None)
                config_name_found = next((x[1][0] for x in acct_config_name if acct == x[0]), None)

            else:
                config_name_found = get_value(item, lambda x: x[1].split(" - ")[1], None)
                if config_name_found:
                    acct = next((x[0] for x in acct_config_name if config_name_found.upper() in x[1]), None)
                    
            account = next((x for x in snow_accounts if x["number"] == acct), None)
            if not account:
                print("not found", config_name_found, item[1])

            aItems.append(Item(
                id = item[0],
                name = item[1],
                interfaceName = interface,
                host = Host(
                    id = item[4],
                    name = item[5],
                ),
                snowLink = SnowLink(
                    acct = get_value(account, lambda x: x["number"], None),
                    account_sys_id = get_value(account, lambda x: x["sys_id"], None),
                    client_display_name = config_name_found,
                ),
                readType = read_type,
            ))

        return aItems

    def process_history_total_traffic(self, reads:list[Read]):
        pass

    def process_trend_total_traffic(self, reads:list[Read]):
        pass

    def post_total_traffic_reads(self, reads:list[Read]):
        pass

    def post_total_traffic_reads_trends(self, reads:list[Read]):
        pass