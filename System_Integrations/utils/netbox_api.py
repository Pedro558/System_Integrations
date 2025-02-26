import requests, json, urllib3

from System_Integrations.utils.compare_utils import is_response_ok

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

def create_tenants(base_url:str, payload:list, headers={}):
    """
    Creates a list of Tenants.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    response = requests.Response()
    try:
        response = requests.post(base_url+ f"/tenancy/tenants/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)
               
    return response

def update_tenants(base_url:str, payload:list, headers={}):
    """
    Updates a list of Tenants.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    payload = payload if isinstance(payload, list) else [payload]

    response = requests.Response()
    try:
        response = requests.put(base_url+ f"/tenancy/tenants/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)

    return response
#
# REGIONS
#
def get_regions(base_url:str, headers={}, params={}):
    """
    get a list of Regions.

    Args:
        base_url (str): The base URL of the netbox API.

    Returns:
        list contaning the results of the search.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")

    url = f"{base_url}/dcim/regions/"
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

def create_regions(base_url:str, payload:list, headers={}):
    """
    Creates a list of Regions.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    response = requests.Response()
    try:
        response = requests.post(base_url+ f"/dcim/regions/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)
               
    return response

def update_regions(base_url:str, payload:list, headers={}):
    """
    Updates a list of Regions.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    payload = payload if isinstance(payload, list) else [payload]

    response = requests.Response()
    try:
        response = requests.put(base_url+ f"/dcim/regions/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)

    return response

#
# SITES
#
def get_sites(base_url:str, headers={}, params={}):
    """
    get a list of regions.

    Args:
        base_url (str): The base URL of the netbox API.

    Returns:
        list contaning the results of the search.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")

    url = f"{base_url}/dcim/sites/"
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

def create_sites(base_url:str, payload:list, headers={}):
    """
    Creates a list of Sites.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    response = requests.Response()
    try:
        response = requests.post(base_url+ f"/dcim/sites/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)
               
    return response

def update_sites(base_url:str, payload:list, headers={}):
    """
    Updates a list of Sites.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    payload = payload if isinstance(payload, list) else [payload]

    response = requests.Response()
    try:
        response = requests.put(base_url+ f"/dcim/sites/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)

    return response

#
# DATA HALLS
#
def get_data_halls(base_url:str, headers={}, params={}):
    """
    get a list of data halls.

    Args:
        base_url (str): The base URL of the netbox API.

    Returns:
        list contaning the results of the search.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")

    url = f"{base_url}/dcim/locations/"
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

def create_data_halls(base_url:str, payload:list, headers={}):
    """
    Creates a list of Data Halls.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    response = requests.Response()
    try:
        response = requests.post(base_url+ f"/dcim/locations/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)
               
    return response

def update_data_halls(base_url:str, payload:list, headers={}):
    """
    Updates a list of Data Halls.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    payload = payload if isinstance(payload, list) else [payload]

    response = requests.Response()
    try:
        response = requests.put(base_url+ f"/dcim/locations/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)

    return response

#
# RACKS
#
def get_racks(base_url:str, headers={}, params={}):
    """
    get a list of racks

    Args:
        base_url (str): The base URL of the netbox API.

    Returns:
        list contaning the results of the search.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")

    url = f"{base_url}/dcim/racks/"
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

def create_racks(base_url:str, payload:list, headers={}):
    """
    Creates a list of racks.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    response = requests.Response()
    try:
        response = requests.post(base_url+ f"/dcim/racks/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)
               
    return response

def update_racks(base_url:str, payload:list, headers={}):
    """
    Updates a list of racks.

    Args:
        base_url (str): The base URL of the netbox API.
        payload (list): A list of dictionaries containing the parameters for the operation.

    Returns:
        list contaning the results of the create operation by item.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")
    if not payload: raise ValueError("payload must be specified")

    payload = payload if isinstance(payload, list) else [payload]
    
    response = requests.Response()
    try:
        response = requests.put(base_url+ f"/dcim/racks/", 
                                headers=headers, 
                                data=json.dumps(payload),
                                verify=False)
        
    except requests.RequestException as e:
        print('An error occurred:', e)

    return response

#
# Circuits
#
def get_circuits(base_url:str, headers={}, params={}):
    """
    get a list of Circuits.

    Args:
        base_url (str): The base URL of the netbox API.

    Returns:
        list contaning the results of the search.

    Raises:
        ValueError: if non optional arguments are not specified.
    """

    if not base_url: raise ValueError("base_url must be specified")

    url = f"{base_url}/circuits/circuits/"
    results = []
    while True:
        response = requests.request("GET", 
                                    url, 
                                    headers=headers, 
                                    params=params,
                                    verify=False)
        
        if not is_response_ok(response):
            print(response.status_code)
            print(response.reason)
            break

        results += response.json()["results"]

        if 'next' not in response.json() or not response.json()['next']:
            break
        else:
            url = response.json()["next"]
                       
    return results
