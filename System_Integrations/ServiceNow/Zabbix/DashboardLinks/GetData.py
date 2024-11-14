import datetime
from http.client import HTTPException
import requests, os, json, time
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv(override=True)
api_token_test = os.getenv("zabbix_api_token_test")

def get_data_test(url, headers, data):
    response = requests.post(url=url, headers=headers, data=json.dumps(data), verify=False)
    return response 
    
url = "https://10.11.70.90/zabbix/api_jsonrpc.php"
headers = {
    "Authorization": f"Bearer {api_token_test}",
    "Content-Type": "application/json"
}
data = {
    "jsonrpc": "2.0",
    "method": "item.get",
    "params": {
        # "output": ["itemid", "name", "tags", "host"],
        "output": "extend",
        # "host": "PRP-ELEAD-RJO1-ACX-01",
        "selectHosts": ["hostid", "name"],  # Include host information
        "selectInterfaces": ["interfaceid", "ip", "name"],  # Include interface information
        "search": {
            "name": "bits"
        },
        "tags": [{
            "tag": "Application", 
            "value": "ACCT" 
        }],
        # "filter": {}
    },
    "id": 2
}

print("Buscando links")
start = time.time()
response = get_data_test(url=url, headers=headers, data=data)
end = time.time()
duration = end - start
print(f"\t-> took {duration:.2f} seconds")
# breakpoint()

items = response.json()["result"]
# breakpoint()
print(f"\t-> Qtd items: {len(items)}")

path = os.path.dirname(os.path.realpath(__file__))
with open(f"{path}/data.json", 'w', encoding='utf-8') as f:
    json.dump(response.json(), f, ensure_ascii=False, indent=4)

items = response.json()['result']
item_ids = [item['itemid'] for item in items]

data = {
    "jsonrpc": "2.0",
    "method": "history.get",
    "params": {
        "output": "extend",#["value", "clock"],
        # "itemids": item_ids[0:42],
        # "history": 0,  # 0 = numeric (bits sent/received)
        "sortfield": "clock",
        "sortorder": "ASC",  # Sort by oldest to newest
        # "limit": 1,
        # "time_from": int(datetime.datetime(2024, 1, 1).timestamp()),
        # "time_till": int(datetime.datetime(2024, 11, 1).timestamp())
    },
    "id": 3
}

# breakpoint()
print("\nBuscando dados (sent/received)")
batch_size = 1#40
iteration = 0
i = 0
while i < len(item_ids):
    try:
        batch = item_ids[i:i + batch_size]
        data["params"]["itemids"] = batch
        print(f"\t---- ")
        print(f"\t-> Iteration: {iteration}")
        print(f"\t-> Batch Size: {batch_size}")

        start = time.time()
        response = get_data_test(url=url, headers=headers, data=data)
        end = time.time()
        duration = end - start
        
        # breakpoint()
        iteration += 1
        response.raise_for_status()
        i += batch_size

        reads = response.json()["result"]
    
        print(f"\t-> took {duration:.2f} seconds")
        print("\t-> Qtd leituras: ", len(reads))

        breakpoint()

    except requests.exceptions.HTTPError as error:
        print("\t-> Error, reducing batch size")
        batch_size -= 5
    except Exception as e:
        print("Unexpected error")
        print(e)
        break
    finally:
        pass
