import pymysql, os, re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from System_Integrations.utils.netbox_api import get_tenants
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from System_Integrations.utils.parser import get_value
from collections import defaultdict

load_dotenv(override=True)

# ===
# NETBOX
# ===
netbox_url = os.getenv("netbox_test_url")
netbox_api_key = os.getenv("netbox_test_api_key")
netbox_headers = {
    "Authorization": f"Token {netbox_api_key}"
}
netbox_tenants = get_tenants(netbox_url, netbox_headers)

# ===
# SNOW
# ===
snow_url = os.getenv("snow_url")
snow_client_id = os.getenv("snow_client_id")
snow_client_secret = os.getenv("snow_client_secret")
snow_refresh_token = os.getenv("snow_refresh_token")
token = get_servicenow_auth_token(snow_url, snow_client_id, snow_client_secret, snow_refresh_token)

clients_fields = ["sys_id, name, number"]
snow_accounts = get_servicenow_table_data(snow_url, "customer_account", {"sysparm_display_value": True, "sysparm_fields":", ".join(clients_fields)}, token)

# Database connection parameters
db_params = {
    'host': os.getenv("zabbix_db_ip"),
    'database': os.getenv("zabbix_db_name"),
    'user': os.getenv("zabbix_db_user"),
    'password': os.getenv("zabbix_db_pwd"),
    'port': 3306
}
conn = pymysql.connect(**db_params)
cursor = conn.cursor()

query_items = f"""
SELECT itemid, name, interfaceid, uuid, hostid
FROM items
WHERE
    name like '%\Bits%' 
    and ( 
        name LIKE '%ACCT%'
        or name LIKE '%Elea OnRamp%'
        or name LIKE '%Elea Connect%'
        or name Like '%Elea Metro Connect%' 
    )
"""

cursor.execute(query_items)
items = cursor.fetchall()
breakpoint()


# TEST LOOK FOR LINK THAT WAS RENAMED
# interface_groups = defaultdict(list)

# for item in items:
#     # Extract the interface from the description
#     interface = item[1].split(' ')[1].split('(')[0]  # Extract the interface part
#     interface_groups[interface].append(item)

# # Filter for interfaces with duplicates
# duplicates = {k: v for k, v in interface_groups.items() if len(v) > 1}

# # Output the results
# for interface, group in duplicates.items():
#     print(f"Interface: {interface}")
#     for entry in group:
#         print(f"  {entry}")

breakpoint()


aItems = []

# Prepares netbox info to be consumed
acct_config_name = [x for x in netbox_tenants if x["custom_fields"]["config_name"]] # tenants that have config name setted
acct_config_name = [( # Transforms it into a tuple of (<ACCT>, <List of the config options>)
                        x["custom_fields"]["number"], 
                        list(map(str.lstrip, x["custom_fields"]["config_name"].upper().split(",")))
                    ) for x in acct_config_name]

for item in items:
    cid = ""
    acct = ""
    config_name_found = ""
    
    interface = get_value(item, lambda x: x[1].split(' ')[1].split('(')[0], None)
    if not interface: continue
    if re.search(r"^(Vlan.*|\.\d+)$", interface): continue # starts with Vlan or ends with .<number>
    
    if "ACCT" in item[1]:
        cid = get_value(item, lambda x: x[0].split(" - ")[1], None)
        acct = get_value(item, lambda x: x[1].split(" - ")[1], None)
        config_name_found = next((x[1][0] for x in acct_config_name if acct == x[0]), None)

    else:
        config_name_found = get_value(item, lambda x: x[1].split(" - ")[1], None)
        if config_name_found:
            acct = next((x[0] for x in acct_config_name if config_name_found.upper() in x[1]), None)
            # breakpoint()
            # for config in acct_config_name:
            #     try:
            #     except:
            #         breakpoint()
                    
            #     if acct: break

    account = next((x for x in snow_accounts if x["number"] == acct), None)
    if not account:
        print("not found", config_name_found, item[1])
        # breakpoint()

    aItems.append({
        "itemid": item[0],
        "name": item[1],
        "acct": get_value(account, lambda x: x["number"], None),
        "account_sys_id": get_value(account, lambda x: x["sys_id"], None),
        "client_display_name": config_name_found
    })

breakpoint()
