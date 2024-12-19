import os
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient, generate_blob_sas, UserDelegationKey, BlobSasPermissions

from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests

from commons.utils.date import get_date

dotenv_path = os.path.join(os.path.dirname(__file__), 'azure.env')  # Define o caminho do arquivo .env
load_dotenv(dotenv_path)  # Carrega as variáveis de ambiente do arquivo credentials.env

appId = os.getenv("app_id")
appSecret = os.getenv("app_secret")
tenantId = os.getenv("tenantId")
subscriptionId = os.getenv("subscriptionId")
token = os.getenv("token")
connectionString = os.getenv("connectionString")
storageAccountKey = os.getenv("storageAccountKey")
print(token)
# accountUrl = "https://cs210032001be4b11a3.blob.core.windows.net/?sp="+token
accountName = "cs210032001be4b11a3"
accountUrl = f"https://{accountName}.blob.core.windows.net/"
containerName = "metric-container"
blobName = "teste.png"

# credential = ClientSecretCredential(client_id=appId, client_secret=appSecret, tenant_id=tenantId)
# blobService = BlobServiceClient(
#     account_url=accountUrl,
# )

# containerClient = blobService.get_container_client("metric-container")
# containerClient = ContainerClient.from_connection_string(connectionString, "metric-container")
containerClient = ContainerClient(
    account_url=accountUrl,
    credential=storageAccountKey,
    container_name=containerName,
)
# containerClient = ContainerClient(
#     account_url=accountUrl,
#     credential=credential,
#     container_name="metric-container",
# )


# blobService = BlobServiceClient.from_connection_string(connectionString)
blobService = BlobServiceClient(
    account_url=accountUrl,
    credential=storageAccountKey
)

breakpoint()
# blobService = BlobServiceClient(
#     account_url=accountUrl,
#     credential=credential, 
# )

# blobService.

folderLocation = "C:/Temp/ZabbixSnowSyncImg/TotalTraffic"
filePath = f"{folderLocation}/total_traffic.png" 

with open(filePath, "rb") as file:
    response = containerClient.upload_blob(
        name=blobName,
        data=file,
        overwrite=True,
    )
    
    breakpoint()

    sas_token = generate_blob_sas(
        account_name=accountName,
        container_name=containerName,
        blob_name=blobName,
        account_key=storageAccountKey,
        permission=BlobSasPermissions(read=True),  # Grant read permissions
        start=datetime.now() - timedelta(minutes=5),
        expiry=datetime.now() + timedelta(hours=24)  # Token valid for 1 hour
    )

    blob_url = f"https://{accountName}.blob.core.windows.net/{containerName}/{blobName}?{sas_token}"
    print(f"SAS URL: {blob_url}")


    # delegation_key = blobService.get_user_delegation_key(
    #     key_start_time=get_date("today"),
    #     key_expiry_time=get_date("tomorrow"),
    # )

    breakpoint()

    # responseSas = generate_blob_sas(
    #     account_name=accountUrl,
    #     container_name="metric-container",
    #     blob_name="teste.png",
    #     permission="r",
    #     expiry="2025-12-12",
    #     user_delegation_key=delegation_key
    # )
    

# blobClient = BlobServiceClient(
#     account_url=accountUrl,
    
# )





# headers = {
# }
# params = {
#     "comp": "list",
#     "sp": "racwdl&st=2024-12-11T19:49:47Z&se=2027-12-31T03:49:47Z&spr=https&sv=2022-11-02&sr=c&sig=lpjkwmgVfkphUET%2F7UPZAl6WdLdFyb0E5DmXqgH0VWs%3D" 
# }
# response = requests.get("https://cs210032001be4b11a3.blob.core.windows.net/", headers=headers)

# print(response.status_code)
# print(response.text)