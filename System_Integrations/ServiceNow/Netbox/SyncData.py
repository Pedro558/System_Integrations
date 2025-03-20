import os


from System_Integrations.classes.strategies.SyncSnowNetbox.SyncDataHall import SyncDataHall
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncContext import SyncContext
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncCustomer import SyncCustomer
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncRack import SyncRack
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncRegion import SyncRegion
from System_Integrations.classes.strategies.SyncSnowNetbox.SyncSite import SyncSite
from System_Integrations.utils.netbox_api import get_data_halls, get_rack_roles, get_racks, get_regions, get_sites, get_tenants
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, get_servicenow_table_data
from commons.utils.env import only_run_in
from dotenv import load_dotenv

from commons.utils.parser import get_value

load_dotenv(override=True)

def get_netbox_tenants(netbox_url, headers):
    netbox_tenants = get_tenants(netbox_url, headers)
    netbox_tenants = [x for x in netbox_tenants if x.get("custom_fields", {}).get("number") and x.get("name")]
    return netbox_tenants


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
    netbox_tenants = get_netbox_tenants(netbox_url, netbox_headers)

    if False:
        print("--- Customer ---")
        sync = SyncContext(SyncCustomer(), snow_customer, netbox_tenants) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        sync.display_results()


    # region and site
    location_fields = ["sys_id, name, street, zip, city, state, latitude, longitude"]
    snow_location = get_servicenow_table_data(url_snow, "cmn_location", {"sysparm_display_value": True, "sysparm_fields":", ".join(location_fields)}, token)
    if False:
        print("--- Region ---")
        snow_region = [{
                **x,
                "name": get_value(x, lambda x: x["name"][0:3])
            } for x in snow_location]

        # ensure uniqueness based on region name (uses the last value found)
        snow_region = list({x.get("name"): x for x in snow_region}.values())

        netbox_region = get_regions(netbox_url, netbox_headers)
        
        sync = SyncContext(SyncRegion(), snow_region, netbox_region) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        sync.display_results()

    if False:
        # Sites
        print("--- Sites ---")
        netbox_site = get_sites(netbox_url, netbox_headers)

        for site in netbox_site:
            corr = next((x for x in snow_location if x.get("name") == site.get("name")), None)
            if corr: site["name"] = corr.get("name")

        sync = SyncContext(SyncSite(), snow_location, netbox_site) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        sync.display_results()


    # data halls
    if False:
        dh_fields = ["sys_id, name, u_site"]
        snow_dh = get_servicenow_table_data(url_snow, "u_cmdb_ci_data_hall", {"sysparm_display_value": True, "sysparm_fields":", ".join(dh_fields)}, token)
        netbox_dh = get_data_halls(netbox_url, netbox_headers)

        sync = SyncContext(SyncDataHall(), snow_dh, netbox_dh) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        print("--- Data Halls ---")
        sync.display_results()

        breakpoint()


    # racks
    print("--- Racks ---")
    netbox_tenants = get_netbox_tenants(netbox_url, netbox_headers)
    netbox_rack = get_racks(netbox_url, netbox_headers)
    rack_fields = ["u_data_hall.u_site, u_data_hall, company, name, sys_id, rack_units, u_type, u_produto, install_status, short_description, company.number"]
    snow_rack = get_servicenow_table_data(url_snow, "cmdb_ci_rack", {"sysparm_display_value": True, "sysparm_fields":", ".join(rack_fields)}, token)

    # get the corresponding tenant from netbox
    for i, x in enumerate(snow_rack):
        tenant = next((tenant for tenant in netbox_tenants if tenant.get("custom_fields").get("number", "1") == x.get("company.number", "2")), None)
        if not tenant: continue
        tenant = {
            'display': tenant.get("display"),
            'id': tenant.get("id"),
            'name': tenant.get("name"),
            'slug': tenant.get("slug"),
            'url': tenant.get("url")
        }
        snow_rack[i]["tenant"] = tenant
    
    len_all_snow_rack = len(snow_rack)
    snow_rack = [x for x in snow_rack if x.get("u_data_hall.u_site") and x.get("u_data_hall") and x.get("name")]
    len_filtered_snow_rack = len(snow_rack) 
    len_cleared = len_all_snow_rack - len_filtered_snow_rack
    if len_cleared > 0:
        print(f"\t-> Skipping racks without site or data hall ({len_cleared} records)")

    # take small subset for testing
    # snow_rack = [x for x in snow_rack if "AQ28" in x["name"]]
    # snow_rack = [x for x in snow_rack if "AR07" in x["name"]]
    # snow_rack = snow_rack[0:100]

    sync = SyncContext(SyncRack(), snow_rack, netbox_rack) 
    sync.compare()
    breakpoint()
    sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
    sync.display_results()

    breakpoint()



if __name__ == "__main__":
    only_run_in([None, "Dev"])
    execute()