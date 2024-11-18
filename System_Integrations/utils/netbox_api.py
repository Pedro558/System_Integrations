import requests, json, urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#
# TENANTS
#
def get_tenants(base_url:str, headers={}, params={}):
    """
    get a list of Tenants.

    Args:
        base_url (str): The base URL of the netbox API.

    Returns:
        list contaning the results of the search.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")

    url = f"{base_url}/tenancy/tenants/"
    results = []
    while True:
        response = requests.request("GET", 
                                    url, 
                                    headers=headers, 
                                    params=params,
                                    verify=False)
        
        results += response.json()["results"]

        if 'next' not in response.json() or not response.json()['next']:
            break
        else:
            url = response.json()["next"]
                       
    return results
