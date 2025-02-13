import os
import pandas as pd
from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.classes.requests.zabbix.SyncProductReadsSnow import SyncProductLinksSnow
from System_Integrations.classes.requests.zabbix.dataclasses import AvgTimeOptions, EnumSyncType
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.SnowProductLinks import SnowProductLinks
from System_Integrations.classes.strategies.zabbix.ProductLinks.NewZbxDB import NewZbxDB
from System_Integrations.classes.strategies.zabbix.ProductLinks.OldZbxDB import OldZbxDB
from System_Integrations.utils.netbox_api import get_circuits, get_tenants
from commons.pandas.utils import get_df_from_excel

# db = OldZbxDB()
db = NewZbxDB()
targetSystem = SnowProductLinks()

db.auth()
db.connect()
targetSystem.auth()

# Netbox auth
netbox_url = "https://10.127.69.93/api"
netbox_api_key = get_api_token("netbox")
netbox_headers = {
    "Authorization": f"Token {netbox_api_key}"
}
netbox_tenants = get_tenants(netbox_url, netbox_headers) 
netbox_circuits = get_circuits(netbox_url, netbox_headers) 

accounts = targetSystem.get_accounts()
links = targetSystem.get_product_links()

items = db.get_items_product_links()
items = targetSystem.process_items_product_links(items, accounts, netbox_tenants, netbox_circuits, links)
oldLinks = [(x.snowLink.cid, x.host.name, x.interfaceName, x.name) for x in items if "IC" not in x.snowLink.cid and "OR" not in x.snowLink.cid and "MC" not in x.snowLink.cid]

# oldLinks = [("", x[5], "", x[1]) for x in items if "ACCT" not in x[1]] 

df = pd.DataFrame(oldLinks, columns=["CID", "Host", "Interface", "Name"])
folder_dir = os.path.abspath(__file__).replace("\\FindOldLinks.py", "").replace("\\", "/")
df.to_excel(f"{folder_dir}/links_new.xlsx", index=False)

# df_or = get_df_from_excel("./links_on_ramp.xlsx", ["CID", "Status", "Equip.", "Interface", "VLAN", "Qual Cloud?", "Redundante?", "Primario?", "CID Redundante"])
# df_ic = get_df_from_excel("./links_elea_connect.xlsx", ["CID", "Status", "Equip.", "Interface", "bloco", "", "Qual Cloud?"])
# df_or = get_df_from_excel("./links_metro_connect.xlsx", ["CID", "Status", "Equip.", "Interface", "VLAN", "Qual Cloud?"])