
import base64
import requests
import os
import json
from datetime import datetime
import curlify
import http.client
import mimetypes
from codecs import encode

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

imgBase64 = base64.b64encode(img.read()).decode('utf-8')
data = {
    "u_daily": imgBase64,
    "u_weekly": imgBase64,
    "u_monthly": imgBase64,
    "u_type": "Total Traffic",
    "u_link": "61ebca358712de100944eb930cbb3517",
    "u_time": datetime.now().strftime("%Y-%m-%d %H:%M%S"),
}

conn = http.client.HTTPSConnection("eleadev.service-now.com")
dataList = []
boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
dataList.append(encode('--' + boundary))
dataList.append(encode('Content-Disposition: form-data; name=uploadFile; filename={0}'.format('/C:/Temp/ZabbixSnowSyncImg/TotalTraffic/total_traffic.png')))

fileType = mimetypes.guess_type('/C:/Temp/ZabbixSnowSyncImg/TotalTraffic/total_traffic.png')[0] or 'application/octet-stream'
dataList.append(encode('Content-Type: {}'.format(fileType)))
dataList.append(encode(''))

with open('C:/Temp/ZabbixSnowSyncImg/TotalTraffic/total_traffic.png', 'rb') as f:
  dataList.append(f.read())
dataList.append(encode('--'+boundary+'--'))
dataList.append(encode(''))
body = b'\r\n'.join(dataList)
payload = body
headers = {
  'Content-Type': 'multipart/form-data',
  'Authorization': 'Bearer '+token,
  'Cookie': '',
  'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
}
conn.request("POST", "/api/now/attachment/upload", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))