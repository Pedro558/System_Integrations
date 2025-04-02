import os


from System_Integrations.auth.api_secrets import get_api_token
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

from commons.utils.list import findIn
from commons.utils.parser import get_value

load_dotenv(override=True)

def get_netbox_tenants(netbox_url, headers):
    netbox_tenants = get_tenants(netbox_url, headers)
    netbox_tenants = [x for x in netbox_tenants if x.get("custom_fields", {}).get("number") and x.get("name")]
    return netbox_tenants


def execute():
    # FOR TESTING DEV
    # snow_instance = "eleadev.service-now" # DEV
    # servicenow_client_id = os.getenv("RD_OPTION_SNOW_CLIENT_ID_TEST") #get_api_token('servicenow-prd-client-id-oauth')
    # servicenow_client_secret = os.getenv("RD_OPTION_SNOW_CLIENT_SECRET_TEST") #get_api_token('servicenow-prd-client-secret-oauth')
    # service_now_refresh_token = os.getenv("RD_OPTION_SNOW_CLIENT_REFRESH_TOKEN_TEST") #get_api_token('servicenow-prd-refresh-token-oauth')

    # FOR TESTING PRD
    # snow_instance = "servicenow.eleadigital" # PRD
    # servicenow_client_id = os.getenv("RD_OPTION_SNOW_CLIENT_ID") #get_api_token('servicenow-prd-client-id-oauth')
    # servicenow_client_secret = os.getenv("RD_OPTION_SNOW_CLIENT_SECRET") #get_api_token('servicenow-prd-client-secret-oauth')
    # service_now_refresh_token = os.getenv("RD_OPTION_SNOW_CLIENT_REFRESH_TOKEN") #get_api_token('servicenow-prd-refresh-token-oauth')

    # REAL DEAL
    env = os.getenv("ENVIRONMENT")
    snow_instance =  "servicenow.eleadigital" if env == "prd" else "eleadev.service-now"
    servicenow_client_id = get_api_token('servicenow-prd-client-id-oauth' if env == "prd" else 'servicenow-dev-client-id-oauth')
    servicenow_client_secret = get_api_token('servicenow-prd-client-secret-oauth' if env == "prd" else 'servicenow-dev-client-secret-oauth')
    service_now_refresh_token = get_api_token('servicenow-prd-refresh-token-oauth' if env == "prd" else 'servicenow-dev-refresh-token-oauth')

    url_snow = f"https://{snow_instance}.com/" 

    # FOR TESTING DEV
    # netbox_url = "https://10.62.70.93/api" # homolog
    # netbox_token = os.getenv("netbox_api_key")

    # FOR TESTING PRD
    # netbox_url = "https://10.127.69.93/api" # PRD
    # netbox_token = os.getenv("netbox_api_key")

    # REAL DEAL
    netbox_url = "https://10.127.69.93/api" if env == "prd" else "https://10.62.70.93/api"
    netbox_token = get_api_token('netbox-prd-api' if env == "prd" else 'netbox-homolog-api') 

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

    if True:
        print("--- Customer ---")
        sync = SyncContext(SyncCustomer(base_url_a=url_snow), snow_customer, netbox_tenants) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        sync.display_results()


    # region and site
    location_fields = ["sys_id, name, street, zip, city, state, latitude, longitude"]
    snow_location = get_servicenow_table_data(url_snow, "cmn_location", {"sysparm_display_value": True, "sysparm_fields":", ".join(location_fields)}, token)
    if True:
        print("--- Region ---")
        snow_region = [{
                **x,
                "name": get_value(x, lambda x: x["name"][0:3])
            } for x in snow_location]

        # ensure uniqueness based on region name (uses the last value found)
        snow_region = list({x.get("name"): x for x in snow_region}.values())

        netbox_region = get_regions(netbox_url, netbox_headers)
        
        sync = SyncContext(SyncRegion(base_url_a=url_snow), snow_region, netbox_region) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        sync.display_results()

    if True:
        # Sites
        print("--- Sites ---")
        netbox_site = get_sites(netbox_url, netbox_headers)

        for site in netbox_site:
            corr = next((x for x in snow_location if x.get("name") == site.get("name")), None)
            if corr: site["name"] = corr.get("name")

        sync = SyncContext(SyncSite(base_url_a=url_snow), snow_location, netbox_site) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        sync.display_results()

    if True:
        # data halls
        print("--- Data Halls ---")
        dh_fields = ["sys_id, name, u_site"]
        snow_dh = get_servicenow_table_data(url_snow, "u_cmdb_ci_data_hall", {"sysparm_display_value": True, "sysparm_fields":", ".join(dh_fields)}, token)
        netbox_dh = get_data_halls(netbox_url, netbox_headers)

        # ensures that after the first time a dh is matched (the sys_id is saved in netbox)
        # the same correlation is kept even though the name of a certain dh is changed in service now
        for dh in snow_dh:
            index, corr = findIn(netbox_dh, lambda x: x.get("custom_fields").get("dh_snow_sys_id", "1") == dh.get("sys_id"))
            if not corr: continue
            netbox_dh[index] = {
                **corr,
                "name": dh.get("name"),
            }

        sync = SyncContext(SyncDataHall(base_url_a=url_snow), snow_dh, netbox_dh) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        sync.display_results()


    if True:
        # racks
        print("--- Racks ---")
        netbox_tenants = get_netbox_tenants(netbox_url, netbox_headers)
        netbox_rack = get_racks(netbox_url, netbox_headers, {"limit": 1000})
        rack_fields = ["u_data_hall.u_site, u_data_hall, company, name, sys_id, rack_units, u_type, u_produto, install_status, short_description, company.number"]
        snow_rack = get_servicenow_table_data(url_snow, "cmdb_ci_rack", {"sysparm_display_value": True, "sysparm_fields":", ".join(rack_fields)}, token)

        # ensures that after the first time a dh is matched (the sys_id is saved in netbox)
        # the same correlation is kept even though the name of a certain dh is changed in service now
        for rack in snow_rack:
            index, corr = findIn(netbox_rack, lambda x: x.get("custom_fields").get("rack_snow_sys_id", "1") == rack.get("sys_id"))
            if not corr: continue
            netbox_rack[index] = {
                **corr,
                "name": rack.get("name"),
            }

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
            print(f"-> Skipping racks without site or data hall ({len_cleared} records)")

        sync = SyncContext(SyncRack(base_url_a=url_snow), snow_rack, netbox_rack) 
        sync.compare()
        sync.sync_all(baseUrl=netbox_url, headers=netbox_headers)
        sync.display_results()


if __name__ == "__main__":
    only_run_in([None, "Homolog", "Prod"])
    execute()