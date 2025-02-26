import os


from System_Integrations.classes.strategies.SyncSnowNetbox import SyncDataHall
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncContext import SyncContext
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncCustomer import SyncCustomer
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncRack import SyncRack
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncRegion import SyncRegion
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncSite import SyncSite
from System_Integrations.utils.netbox_api import get_data_halls, get_racks, get_sites, get_tenants
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from commons.utils.env import only_run_in
from dotenv import load_dotenv

from commons.utils.parser import get_value

load_dotenv(override=True)

def execute():
    url_snow = "https://eleadev.service-now.com/" # DEV
    servicenow_client_id = os.getenv("RD_OPTION_SNOW_CLIENT_ID_TEST") #get_api_token('servicenow-prd-client-id-oauth')
    servicenow_client_secret = os.getenv("RD_OPTION_SNOW_CLIENT_SECRET_TEST") #get_api_token('servicenow-prd-client-secret-oauth')
    service_now_refresh_token = os.getenv("RD_OPTION_SNOW_CLIENT_REFRESH_TOKEN_TEST") #get_api_token('servicenow-prd-refresh-token-oauth')

    netbox_url = "https://10.62.70.93/api" # homolog
    netbox_token = os.getenv("netbox_test_api_key")
    netbox_headers = {
        "Content-Type": "application/json",
        "authorization": f"Token {netbox_token}"
    }

    token = get_servicenow_auth_token(url_snow, servicenow_client_id, servicenow_client_secret, service_now_refresh_token)
    
    # customers
    clients_fields = ["sys_id, name, number, account_parent, u_nickname", "city", "state", "country"]
    snow_customer = get_servicenow_table_data(url_snow, "customer_account", {"sysparm_display_value": True, "sysparm_fields":", ".join(clients_fields)}, token)
    snow_customer = [x for x in snow_customer if x.get("number") and x.get("name")]
    netbox_tenants = get_tenants(netbox_url, netbox_headers)
    netbox_tenants = [x for x in netbox_tenants if x.get("custom_fields", {}).get("number") and x.get("name")]




    sync = SyncContext(SyncCustomer(), snow_customer, netbox_tenants) 
    sync.compare()

    # for customer in snow_customer:
    #     corr = next((x for x in netbox_tenants if x["custom_fields"]["number"] == customer["number"]), None)
    #     if not corr: continue

    #     print(customer["name"], " - ", corr["name"])

    # exit()

    sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
    print("--- Customer ---")
    sync.display_results()
    breakpoint()

    # region and site
    location_fields = ["sys_id, name"]
    snow_location = get_servicenow_table_data(url_snow, "cmn_location", {"sysparm_display_value": True, "sysparm_fields":", ".join(location_fields)}, token)

    snow_region = [{
            **x,
            "name": get_value(x, lambda x: x["name"][0:3].replace("0", "O"))
        } for x in snow_location]
    netbox_region = []
    
    # sync = SyncContext(SyncRegion(), snow_region, netbox_region) 
    # sync.compare()
    # sync.sync_all()

    netbox_site = get_sites(netbox_url, netbox_headers)

    # sync = SyncContext(SyncSite(), snow_location, netbox_site) 
    # sync.compare()
    # sync.sync_all()

    # data halls
    dh_fields = ["sys_id, name, u_site"]
    snow_dh = get_servicenow_table_data(url_snow, "u_cmdb_ci_data_hall", {"sysparm_display_value": True, "sysparm_fields":", ".join(dh_fields)}, token)

    netbox_dh = get_data_halls(netbox_url, netbox_headers)

    # sync = SyncContext(SyncDataHall(), snow_dh, netbox_dh) 
    # sync.compare()
    # sync.sync_all()

    # racks
    rack_fields = ["u_data_hall, company, name, sys_id"]
    snow_rack = get_servicenow_table_data(url_snow, "cmdb_ci_rack", {"sysparm_display_value": True, "sysparm_fields":", ".join(rack_fields)}, token)
    netbox_rack = get_racks(netbox_url, netbox_headers)

    # sync = SyncContext(SyncRack(), snow_rack, netbox_rack) 
    # sync.compare()
    # sync.sync_all()



if __name__ == "__main__":
    only_run_in([None, "Dev"])
    execute()