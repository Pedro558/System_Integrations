import pymysql, os, re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from System_Integrations.utils.netbox_api import get_tenants
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from System_Integrations.utils.parser import get_value
from collections import defaultdict
import bisect

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

five_days_ago = int((datetime.now() - timedelta(days=5)).timestamp())

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
# breakpoint()


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

# breakpoint()


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
            # breakpoint()
            # for config in acct_config_name:
            #     try:
            #     except:
            #         breakpoint()
                    
            #     if acct: break

    # if "sent" in read_type: breakpoint()
    account = next((x for x in snow_accounts if x["number"] == acct), None)
    if not account:
        print("not found", config_name_found, item[1])

    aItems.append({
        "itemid": item[0],
        "name": item[1],
        "acct": get_value(account, lambda x: x["number"], None),
        "account_sys_id": get_value(account, lambda x: x["sys_id"], None),
        "client_display_name": config_name_found,
        "hostid": item[4],
        "interface": interface,
        "read_type": read_type,
    })

# SIMPLIFY TESTS
test_item = aItems[0]
aItems = [x for x in aItems if x["hostid"] == test_item["hostid"] and x["interface"] == test_item["interface"]]
breakpoint()

aItemIds = [x["itemid"] for x in aItems]

query_history = f"""
SELECT hUnit.itemid, hUnit.clock, hUnit.value, host.host hostName 
FROM history_uint hUnit
    JOIN items item ON hUnit.itemid = item.itemid
    JOIN hosts host ON item.hostid = host.hostid
WHERE 
    hUnit.itemid IN ({','.join(['%s'] * len(aItemIds))})
    and clock <= %s
"""
    # and clock <= %s

cursor.execute(query_history, (*aItemIds, five_days_ago))
history_data = cursor.fetchall()

breakpoint()
def get_item_info(read, aItems):
    corr_item = next((x for x in aItems if read[0] == x["itemid"]), None)
    if not corr_item:
        print(f"No corr Item found for read of itemid ", read[0])
        return {"not_found": True}

    return {
        **corr_item,
        "time": read[1],
        "value": read[2],
        "host_name": read[3],
    }

history_data = [{
        **get_item_info(x, aItems),
    } for x in history_data]

read_types_to_sum = ["Bits received", "Bits sent"]
total_traffic_data = []
pair_dict = {}
breakpoint()

# Step 1: Group by (hostid, interface)
grouped_data = defaultdict(list)
for obj in history_data:
    print("grouping data", len(grouped_data))
    key = (obj["hostid"], obj["interface"])
    grouped_data[key].append(obj)

# Step 2: Pair by closest time
breakpoint()
pairs = []
unmatched_sent = []
max_time_diff = 120 # Allowable time difference in seconds
for key, measurements in grouped_data.items():
    # Separate by type
    sent = sorted([m for m in measurements if m["read_type"] == "Bits sent"], key=lambda x: x["time"])
    received = sorted([m for m in measurements if m["read_type"] == "Bits received"], key=lambda x: x["time"])
    
    # Extract times for binary search
    received_times = [m["time"] for m in received]
    used_indices = set()

    iterations = 0

    for s in sent[:]:
        print("Matching pairs ", len(pairs))
        # Find the closest time in "Bits Received" using binary search
        pos = bisect.bisect_left(received_times, s["time"])
        closest_match = None
        closest_idx = None
        direction = 0  # 0 = not started, -1 = left, +1 = right
        
        while True:
            if pos < len(received) and (direction >= 0):  # Check right neighbor
                if pos not in used_indices:
                    closest_match = received[pos]
                    closest_idx = pos
                    break
                pos += 1
                direction = 1  # Move right
            
            if pos > 0 and (direction <= 0):  # Check left neighbor
                if pos - 1 not in used_indices:
                    closest_match = received[pos - 1]
                    closest_idx = pos - 1
                    break
                pos -= 1
                direction = -1  # Move left
            
            # If neither direction finds a match
            if direction > 0 and pos >= len(received) or direction < 0 and pos <= 0:
                break
        
        # Validate match
        if closest_match and abs(s["time"] - closest_match["time"]) <= max_time_diff:
            pairs.append((s, closest_match))
            used_indices.add(closest_idx)  # Mark index as used
        else:
            unmatched_sent.append(s)
        # if s["itemid"] == 49412 and s["time"] == 1731862859:
        #     breakpoint()

        # # Determine the closest match
        # try:
        #     closest_match = None
        #     closest_idx = None

        #     if pos < len(received):  # Check the right neighbor
        #         closest_match = received[pos]
        #         closest_idx = pos

        #     if pos > 0:  # Check the left neighbor
        #         if pos > len(received): left_match = received[-1]
        #         else: left_match = received[pos - 1]

        #         if closest_match is None or abs(left_match["time"] - s["time"]) < abs(closest_match["time"] - s["time"]):
        #             closest_match = left_match
        #             closest_idx = pos - 1

        # except Exception as error:
        #     breakpoint()
        #     print()

        # # Pair if a match is found
        # if closest_match and closest_idx not in used_indices:
        #     pairs.append((s, closest_match))
        #     used_indices.add(closest_idx)
        #     received.remove(closest_match)  # Remove to avoid re-matching
        # else:
        #     pairs_not_found.append(s)

        iterations += 1


    breakpoint()

# DID NOT WORK BECAUSE THERE ARE MATCHES THAT NEED TO BE MADE BASED ON TIME PROXIMITY
# for read in history_data:
#     print(f"building pairs... {len(pair_dict)}")
#     key = (read["hostid"], read["interface"], read["time"])
#     if key not in pair_dict:
#         pair_dict[key] = {"Bits sent": None, "Bits received": None}
#     # else:
#     #     breakpoint()

#     pair_dict[key][read["read_type"]] = read

# pair_not_found = []
# for key, values in pair_dict.items():
#     print(f"building total traffic... {len(total_traffic_data)} ", end="")
#     if not (values["Bits sent"] and values["Bits received"]):
#         print("No pair found")
#         pair_not_found.append(values)
#         continue

#     print("Pair found")
#     total_traffic_data.append({
#         **values["Bits sent"],
#         "value": values["Bits sent"]["value"] + values["Bits received"]["value"],
#         "itemid": None,
#         "origin_itemids": [values["Bits sent"]["itemid"], values["Bits received"]["itemid"]]
#     })
        


breakpoint()

# POOR PERFORMANCE
# half_of_hist_size = len(history_data) / 2 
# for read in history_data:
#     print(f"Processing... {len(total_traffic_data)}/{half_of_hist_size}")
#     read_type = read["read_type"]
#     other_type = next((x for x in read_types_to_sum if x != read_type), None)
#     if not other_type: continue

#     other_read = next((
#             x for x in history_data 
#                 if x["hostid"] == read["hostid"]
#                     and x["interface"] == read["interface"]
#                     and x["time"] == read["time"]
#                     and x["read_type"] == other_type
#         ), None)

#     if not other_read: continue

#     total_traffic_data.append({
#         **read,
#         "value": read["value"] + other_read["value"],
#         "itemid": None,
#         "origin_itemids": [read["itemid"], other_read["itemid"]]
#     })
    

breakpoint()



weekly_reads = []
