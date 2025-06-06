from calendar import c
from collections import defaultdict
import os
import re
from abc import ABC, abstractmethod
from random import randint
import time
from typing import Literal
from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumRangeOptions, EnumSyncType, Host, Item, Read, EnumReadType
from datetime import datetime
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.dataclasses import SnowLink
from System_Integrations.utils.parser import get_value
from System_Integrations.utils.servicenow_api import client_monitoring_multi_post, get_servicenow_auth_token, get_servicenow_table_data, patch_servicenow_record, post_to_servicenow_table
from dotenv import load_dotenv
from System_Integrations.utils.parser import group_by
from commons.network.link.customer import get_info_from_desc

load_dotenv(override=True)

class ISnowProductLinks(ABC):

    def __init__(self, 
                env:Literal['dev','prd'] = "dev", 
                clientId = None,
                clientSecret = None,
                refreshToken = None,
                *args, **kwargs):
        self.env = env if env else "dev"
        self.clientId = clientId
        self.clientSecret = clientSecret
        self.refreshToken = refreshToken
    
    def auth(self):
        self.snow_url = "https://servicenow.eleadatacenters.com/" if self.env == "prd" else "https://eleadev.service-now.com/"
        # self.snow_url = "" if self.env == "prd" else "https://eleadev.service-now.com/"

        self.snow_client_id = self.clientId or get_api_token(f'servicenow-{self.env}-client-id-oauth')
        self.snow_client_secret = self.clientSecret or get_api_token(f'servicenow-{self.env}-client-secret-oauth')
        self.snow_refresh_token = self.refreshToken or get_api_token(f'servicenow-{self.env}-refresh-token-oauth')

        self.token = get_servicenow_auth_token(self.snow_url, self.snow_client_id, self.snow_client_secret, self.snow_refresh_token)

    def get_accounts(self):
        clients_fields = ["sys_id, name, number"]
        accounts = get_servicenow_table_data(self.snow_url, "customer_account", {"sysparm_display_value": True, "sysparm_fields":", ".join(clients_fields)}, self.token)
        return accounts

    def get_product_links(self):
        fields = ["sys_id", "u_customer", "u_customer.sys_id", "u_device", "u_interface", "u_link_cid", "u_link_name", "u_link_type"]
        accounts = get_servicenow_table_data(self.snow_url, "u_temp_customer_links", {"sysparm_display_value": True, "sysparm_fields":", ".join(fields)}, self.token)
        return accounts

    def get_most_recent_read_time(self, dataType:EnumSyncType = EnumSyncType.HIST):
        fields = ["sys_id", "u_time"]

        table = "u_read_links_total_traffic" if dataType == EnumSyncType.HIST else "u_read_links_total_traffic_trends"
        response = get_servicenow_table_data(
            self.snow_url,
            table,
            {
                "sysparm_display_value": True, "sysparm_fields":", ".join(fields),
                "sysparm_limit":1,
                "sysparm_query":"ORDERBYDESCu_time"
            },
            self.token
        )

        mostRecent = get_value(response, lambda x: response[0]["u_time"], None)
        if mostRecent:
            # Define the format of the date string
            date_format = "%d/%m/%Y %H:%M:%S"
            # Parse the string into a datetime object
            dt = datetime.strptime(mostRecent, date_format)
            # Convert the datetime object to a Unix timestamp
            mostRecent = int(dt.timestamp())

        return mostRecent


    def process_items_product_links(self, items:list[Item], snow_accounts, netbox_tenants, netbox_circuits, snow_links):
        acct_config_name = [x for x in netbox_tenants if x["custom_fields"]["config_name"]] # tenants that have config name setted
        acct_config_name = [( # Transforms it into a tuple of (<ACCT>, <List of the config options>)
                                x["custom_fields"]["number"], 
                                list(map(str.lstrip, x["custom_fields"]["config_name"].upper().split(",")))
                            ) for x in acct_config_name]
        
        ignorable = [
            "OR-POA1-SP04-1-2-001", # given wrong CID when creating, actual links are in et-0/0/22.2998 and et-0/0/22.2999
        ]

        def get_device(name, interface):
            if not interface: return name

            if "et" in interface:
                name = name.replace("QFX", "ACX").replace("PSP", "PRP")
            else:
                name = name.replace("ACX", "QFX").replace("PRP", "PSP")

            return name


        device_netb_circ = [ # makes the device info match the device of interface (the device in netbox points to ACX or QFX depending on the commit rate, but the interface is always the delivery interface)
            { **x, "custom_fields": {
                    **x["custom_fields"],
                    "origin_device": get_device(x["custom_fields"]["origin_device"], x["custom_fields"]["origin_interface"]),
                    "dest_device": get_device(x["custom_fields"]["dest_device"], x["custom_fields"]["dest_interface"]),
                    # "origin_device": x["custom_fields"]["origin_device"].replace("QFX", "ACX").replace("PSP", "PRP") if "et" in ( x["custom_fields"]["origin_interface"] or "") else x["custom_fields"]["origin_device"],
                    # "dest_device": x["custom_fields"]["dest_device"] .replace("QFX", "ACX").replace("PSP", "PRP") if "et" in ( x["custom_fields"]["dest_interface"] or "" ) else x["custom_fields"]["dest_device"],
                }
            }
            for x in netbox_circuits
        ] 

        aItems:list[Item] = []
        for item in items:
            acct = ""
            config_name_found = ""

            read_type = ""
            match = re.search(r"(Bits received|Bits sent|Total Interface Traffic)", item[1])
            if match: 
                read_type = match.group(1)
                config = {
                    "Bits received": EnumReadType.BITS_RECEIVED,
                    "Bits sent": EnumReadType.BITS_SENT,
                    "Total Interface Traffic": EnumReadType.TOTAL_TRAFFIC,
                }
                read_type = config[read_type]
            
            interface = None
            vlan = "" 
            interfaceComplete = "" 
            # interface = get_value(item, lambda x: x[1].split(' ')[1].split('(')[0], None)
            interface = get_value(item, lambda x: x[1].split('(')[0], "")
            interface = interface.replace("Interface", "").strip()
            # if re.search(r".*(Vlan.*|.*\.\d+).*", interface): continue # starts with Vlan or ends with <string>.<number>
            if re.search(r".*Vlan.*", interface): continue # starts with Vlan
            if re.search(r".*49.*\.\d+.*", interface): continue
            if re.search(r".*\.\d+.*", interface):
                parts = interface.split(".") 
                interface = parts[0]
                vlan = parts[1]


            interfaceComplete = f"{interface}.{vlan}" if vlan else interface

            commit_rate = 0
            circuit = None
            cid = ""
            config_cid = "" 
            cloud = None
            
            # TODO if device name pattern changes, this need to be refactored
            origin = item[5].split("-")[2] if item[5] else None 
            dest = None 

            if "ACCT" in item[1]:
                # get the content inside the parenthesis
                match = re.search(r'\((.*?)\)', item[1])
                desc = match.group(1) if match else ""
                # get info from the description
                info, _ = get_info_from_desc(desc)
                cid = info.get("cid")
                acct = info.get("acct")
                config_name_found = next((x[1][0] for x in acct_config_name if acct == x[0]), None)

                # cid = get_value(item, lambda x: x[1].split(" - ")[0].split("(")[-1], "")
                # acct = get_value(item, lambda x: x[1].split(" - ")[1], None)
            else:
                config_name_found = get_value(item, lambda x: x[1].split(" - ")[1], None)
                if config_name_found:
                    match = next((x for x in acct_config_name if config_name_found.upper() in x[1]), None)
                    if match: 
                        acct = match[0]
                        config_name_found = match[1][0] # use the first config name of the acct
                    # acct = next((x[0] for x in acct_config_name if config_name_found.upper() in x[1]), None)

                if interface:
                    circuit = next((x for x in device_netb_circ if 
                                    (
                                        x["custom_fields"]["origin_interface"] == interface 
                                        and x["custom_fields"]["origin_device"] == item[5]
                                        and (x["custom_fields"]["vlan"] == vlan if vlan else True)
                                    ) 
                                    or (
                                        x["custom_fields"]["dest_interface"] == interface 
                                        and x["custom_fields"]["dest_device"] == item[5]
                                        # and (x["custom_fields"]["vlan"] == vlan if vlan else True)
                                    )
                                    ), None)
                    
                    if circuit:
                        cid = circuit["cid"]


            if cid and cid in ignorable: continue

            if cid and not circuit:
                circuit = next((x for x in device_netb_circ if x["cid"] == cid), None)

            if cid and not interface:
                if circuit: interface = circuit["custom_fields"]["origin_interface"]
                else: print("NOT IN NETBOX: "+item[1])

            # if config_name_found and config_name_found.lower() == "procergs": 
            #     # if interface == "et-0/0/22":  breakpoint()
            #     if not cid: breakpoint()

            if not interface: continue
            # if not circuit: continue
            
            if circuit:
                netbox_cid = circuit["cid"]
                config_cid = circuit["custom_fields"]["config_cid"]
                commit_rate = circuit["commit_rate"]
                cloud = circuit["custom_fields"]["cloud"]
                if circuit["custom_fields"]["origin_device"]: 
                    origin = circuit["custom_fields"]["origin_device"].split("-")[2]
                if circuit["custom_fields"]["dest_device"]: 
                    dest = circuit["custom_fields"]["dest_device"].split("-")[2]

                # if interface == "et-0/0/2": breakpoint()
                if ( circuit["custom_fields"]["origin_device"] != item[5] 
                    # and circuit["custom_fields"]["origin_interface"] != interface 
                    ):
                    continue # avoids having dups of circuits with origin - dest (Like metro connects and on ramps)


            account = next((x for x in snow_accounts if x["number"] == acct), None)
            if not account:
                print("not found", config_name_found, item[1])

            linkType = None
            if "Elea Connect" in item[1]: linkType = "Elea Connect"
            elif "Elea Internet Connect" in item[1]: linkType = "Elea Connect"
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

                # this is for link that do not have a cid in the new pattern, to avoid bits sent and bits received of the same link to have a different identifier
                corr_item = None
                if interface:
                    corr_item = next((x for x in aItems if
                                      x.host.name == item[5] and
                                      x.interfaceName == interface and
                                      (x.vlan == vlan if vlan else True)
                                    ), None)

                if corr_item:
                    cid = corr_item.snowLink.cid
                else:
                    length = 8
                    rdm = randint(10**(length-1), (10**length)-1)
                    temp_cid = f"{config_name_found}"
                    if linkType: temp_cid += f" - {linkType}"
                    temp_cid += f" - {rdm}"
                    cid = temp_cid


            snowLink = None
            corrLink = next((x for x in snow_links if x["u_link_name"] == cid), None)
            # if item[5] == "PRP-ELEAD-SP04-ACX-02" and interface == "et-0/0/2": breakpoint()
            # if item[5] == "PSP-ELEAD-RJO1-QFX-01": breakpoint()
            if not corrLink and interface:
                corrLink = next((x for x in snow_links if 
                                # x["u_customer"] == account["name"] and
                                x["u_device"] == item[5] and
                                x["u_interface"] == interfaceComplete
                            ), None)


            if corrLink:
                snowLink = SnowLink(
                    acct = corrLink["u_customer"]["display_value"] if corrLink["u_customer"] else None,
                    account_sys_id = corrLink["u_customer.sys_id"] if "u_customer.sys_id" in corrLink else None,
                    client_display_name = config_name_found,
                    cid = cid,
                    commit_rate=commit_rate,
                    linkType = corrLink["u_link_type"],
                    sys_id = corrLink["sys_id"] if corrLink["sys_id"] != "0" else "",
                )
            else:
                snowLink = SnowLink(
                    acct = get_value(account, lambda x: x["number"], None),
                    account_sys_id = get_value(account, lambda x: x["sys_id"], None),
                    client_display_name = config_name_found,
                    cid = cid,
                    commit_rate=commit_rate,
                    linkType = linkType
                )

            snowLink.create_display_name(
                cid=netbox_cid,
                cloud=cloud,
                origin=origin,
                dest=dest,
            )

            # # treatment for links that do not have the pattern of cid set (Rename pending)
            # if item.need_cid:
            #     item

            aItems.append(Item(
                id = item[0],
                name = item[1],
                interfaceName = interface,
                interfaceComplete = interfaceComplete,
                vlan = vlan,
                host = Host(
                    id = item[4],
                    name = item[5],
                ),
                snowLink = snowLink,
                readType = read_type,
                need_cid=need_cid,
            ))
        

        # remove "duplicates" (same CID but due to logical interfaces, they are created as different items)
        # ex:
        # et-0/0/22       up    up   OR-POA1-SP04-1-2-001 - ACCT0010837 - 2GB - POA1POA1 - PROCERGS
        # et-0/0/22.2988  up    up   Elea OnRamp - Procergs - 5Gbps - pri - POA1-SP4
        # et-0/0/22.2999  up    up   Elea OnRamp - Procergs - 2Gbps - SEC - POA1-SP4
        interface_groups = defaultdict(list)
        for item in aItems:
            key = (item.host.name, item.interfaceName)
            interface_groups[key].append(item)
        
        filtered_items = []
        for (host, base_inteface), group in interface_groups.items():
            if any('.' in item.interfaceComplete for item in group):
                # if (host, base_inteface) == ("PRP-ELEAD-POA1-ACX-01", "et-0/0/21"): breakpoint()
                # Keep only logical interfaces if they exist
                filtered_items.extend(item for item in group if '.' in item.interfaceComplete)
            else:
                # If no logical interfaces, keep the physical interface
                filtered_items.extend(group)

        aItems = filtered_items

        # test_item = [x for x in aItems if not x.need_cid][0] # TESTES
        # aItems = [x for x in aItems if x.host.id == test_item.host.id and x.interfaceName == test_item.interfaceName]

        return aItems

    def process_total_traffic(self, 
                              reads:list[Read],
                              items:list[Item]=None, 
                              rangeType:EnumRangeOptions = EnumRangeOptions.LAST_DAY, 
                              avgTime:AvgTimeOptions = None,
                              startDate:int = None,
                              ):
        data = []
        for read in reads:
            if not read.item.snowLink.sys_id: continue

            data.append({
                "u_value": read.value,
                "u_time": read.timeStr,
                "u_link": read.item.snowLink.sys_id
            })

        return data
        
    def post_product_links(self, items:list[Item]):
        grouped_items = group_by(items, ["snowLink.cid"])
        aLinks = []
        for key in grouped_items.keys():
            item:list[Item] = grouped_items[key]
            aLinks.append({
                "sys_id": item[0].snowLink.sys_id if item[0].snowLink.sys_id else None,
                "u_customer": item[0].snowLink.account_sys_id,
                "u_device": item[0].host.name,
                "u_interface": item[0].interfaceComplete,
                "u_link_cid": item[0].snowLink.cid,
                "u_link_name": item[0].snowLink.display_name,
                "u_link_type": item[0].snowLink.linkType,
                "original_items": item if item else []
            })

        for i, link in enumerate(aLinks):
            print(f"{i+1}/{len(aLinks)} => {link['u_link_cid']}")

            link_to_post = {**link}
            del link_to_post["original_items"]
            
            if link_to_post["sys_id"]:
                response = patch_servicenow_record(self.snow_url, "u_temp_customer_links", link_to_post["sys_id"], link_to_post, self.token)
            else:
                del link_to_post["sys_id"]
                response = post_to_servicenow_table(self.snow_url, "u_temp_customer_links", link_to_post, self.token)

            # if "response_http" not in response: breakpoint()
            response = response["response_http"]
            link["sys_id"] = None
            try:
                response.raise_for_status()
                link["sys_id"] = response.json()["result"]["sys_id"]
                for item in link["original_items"]:
                    item.snowLink.sys_id = link["sys_id"]

            except Exception as error:
                print(error)

        return items


    @staticmethod
    def process_batches(data, process_batch, chunk_size = 6000, show_print=True):
        chunk_size = 6000
        iteration = 0
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            iteration += 1
            process_batch(chunk, {"iteration": iteration, "start": i, "end": i+chunk_size, "count_list": len(data)})

    # Some function may want to post it based on Reads or based on Items
    def post_total_traffic_reads(self, 
                                 reads:list[Read] = None, 
                                 items:list[Item] = None, 
                                 dataType:EnumSyncType = EnumSyncType.HIST, 
                                 rangeType:EnumRangeOptions = EnumRangeOptions.LAST_DAY,
                                 avgTime:AvgTimeOptions = AvgTimeOptions.FIVE_MIN,
                                ):
        total_traffic_data = []

        for read in reads:
            total_traffic_data.append({
                "u_value": read.value,
                "u_time": read.timeStr, 
                "u_link": read.item.snowLink.sys_id
            })

        def process_batch(batch, info):
            start_time = time.time()
            iteration = info["iteration"]
            start = info["start"]
            end = info["end"]
            count_list = info["count_list"]

            print(f"Batch {iteration} ({start}/{count_list})")


            params = {"readType": "total_traffic", "dataType": dataType.value}
            response = client_monitoring_multi_post(self.snow_url, batch, self.token, params=params)

            try:
                response = response["response"]
                response.raise_for_status()
                result = response.json()
                reads_error = [x for x in result if "error" in x]
                reads_not_saved = [x for x in result if "sys_id" not in x or not x["sys_id"]]
                reads_ok = [x for x in result if "error" not in x and x["sys_id"]]
                
                print(f"\t=> OK ({len(reads_ok)}) | Error ({len(reads_error)}) | Unkown ({len(reads_not_saved)})")

            except:
                print(f"\t=> Error in batch {response.json()}")


            end_time = time.time()
            duration = end_time - start_time
            print(f"\t=> took {duration:.2f} seconds")

        print(f"\nPost reads to Snow...")
        start = time.time()
        self.process_batches(
            total_traffic_data,
            process_batch,
        )
        end = time.time()
        duration = end - start
        print(f"-> took {duration:.2f} seconds")

