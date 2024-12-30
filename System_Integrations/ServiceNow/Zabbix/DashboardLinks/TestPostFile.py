import base64
import requests
import os
import json
from datetime import datetime
import curlify

from System_Integrations.utils.servicenow_api import get_servicenow_auth_token
from commons.utils.logging import save_file

from dotenv import load_dotenv

load_dotenv(override=True)


snow_url = os.getenv("snow_url")
snow_client_id = os.getenv("snow_client_id")
snow_client_secret = os.getenv("snow_client_secret")
snow_refresh_token = os.getenv("snow_refresh_token")
token = get_servicenow_auth_token(snow_url, snow_client_id, snow_client_secret, snow_refresh_token)
# print(token)
# breakpoint()

headers = {
    # 'Content-Type': 'multipart/form-data',
    'Content-Type': 'application/json',
    'Authorization': 'Bearer '+token,
}

folderLocation = "C:/Temp/ZabbixSnowSyncImg/TotalTraffic"
filePath = f"{folderLocation}/total_traffic.png" 
save_file(pathToSave=folderLocation, contentToSave="", fileName=".ignore") # make sure the path is created
img = open(filePath, "rb")


# imgBase64 = base64.b64encode(img.read()).decode('utf-8')
# data = {
#     "u_daily": imgBase64,
#     "u_weekly": imgBase64,
#     "u_monthly": imgBase64,
#     "u_type": "Total Traffic",
#     "u_link": "61ebca358712de100944eb930cbb3517",
#     "u_time": datetime.now().strftime("%Y-%m-%d %H:%M%S"),
# }


# img = open(filePath, "rb")
# files = {"test": img} 
# files = {'file_name': ("daily.png", img, "image/png", {'Expires': '0'})}
# files = {"file": img}
headers = {
    # "Accept":"*/*",
    # "Accept": "application/json",
    # 'Content-Type': 'application/octet-stream',
    # 'Content-Type': 'multipart/form-data',
    'Content-Type': 'image/png',
    'Authorization': 'Bearer '+token,
}

# response = requests.post(url=snow_url+'/api/eldi/client_links_monitoring/update_imgs', headers=headers, data = json.dumps(data))
# response = requests.post(url=snow_url+'/api/sn_entitlement/teste_scoped_licensing_engine/update_imgs', headers=headers, data = json.dumps(data))

params = {
    "file_name": "teste_1.png",
    "table_name": "u_link_reads_image",
    # "uplaodFile": img.read(),
    # "uplaodFile": f"@{filePath}",
    "table_sys_id": "61ebca358712de100944eb930cbb3517",
}

# simplexzaço
files= {
    "file": ("teste_2.png", open(filePath, "rb"), "image/png")
} 


# files=[
#   ('uploadFile',
#    (
#        'total_traffic.png',
#         open('/Temp/ZabbixSnowSyncImg/TotalTraffic/total_traffic.png','rb'),
#         # "@C:/Temp/ZabbixSnowSyncImg/TotalTraffic/total_traffic.png",
#        'image/png'
#     )
#    )
# ]

# response = requests.request("POST", url=snow_url+"api/now/attachment/upload", headers=headers, data=params, files=files)

# response = requests.post(url=snow_url+"api/now/attachment/upload", headers=headers, files=files, data=params)
response = requests.post(url=snow_url+"api/now/attachment/file", headers=headers, params=params, files=files)

# print(curlify.to_curl(response.request))

print(response.status_code)
print(response.text)
breakpoint()

# data = {
#     "u_weekly": "4ea70afe3b1ad210b3cfc447f4e45a17",
# }

# url = snow_url + 'api/now/table/' + "u_link_reads_image"

# headers = {
#     'Content-Type': 'application/json',
#     'Authorization': 'Bearer '+token,
# }

# response = requests.post(url, headers=headers, params = {}, data=json.dumps(data))
# print(response.status_code)
# print(response.json())
# breakpoint()