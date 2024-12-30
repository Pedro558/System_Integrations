
import os
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

from System_Integrations.classes.strategies.Storage.IFileStorage import IFileStorage
from System_Integrations.classes.strategies.Storage.dataclasses import File
from commons.classes.utils import get_kwargs

from azure.storage.blob import ContainerClient, BlobSasPermissions, generate_blob_sas

# dotenv_path = os.path.join(os.path.dirname(__file__), 'azure.env')  # Define o caminho do arquivo .env
load_dotenv(override=True)  # Carrega as variáveis de ambiente do arquivo credentials.env

class BlobStorage(IFileStorage):
    
    def __init__(self, 
                 accountName:str | None = None,
                 containerName:str | None = None, 
                 *args, **kwargs):
        params = {**get_kwargs(), **kwargs}
        super().__init__(**params)

        self.accountName = accountName or "cs210032001be4b11a3"
        self.accountUrl = f"https://{self.accountName}.blob.core.windows.net/"
        self.containerName = containerName or "metric-container"


    def auth(self):
        # TODO RDK TEMPORARY, REMOVE THIS
        self.token = os.getenv("RD_OPTION_AZURE_BLOB_STORAGE_ACCOUNT_KEY_TEST") # os.getenv("storageAccountKey")
        self.containerClient = ContainerClient(
            account_url=self.accountUrl,
            credential=self.token,
            container_name=self.containerName,
        )


    def upload(self, files:list[File]):
        start_time = time.time()
        print("Uploading files to Azure...")
        for index, file in enumerate(files):
            # with open(file.path, 'rb') as data:
            if not file.name: breakpoint()

            self.containerClient.upload_blob(
                name=file.name,
                data=file.data,
                overwrite=True,
            )

            sas_token = generate_blob_sas(
                account_name=self.accountName,
                container_name=self.containerName,
                blob_name=file.name,
                account_key=self.token,
                permission=BlobSasPermissions(read=True),  # Grant read permissions
                start=datetime.now() - timedelta(minutes=5),
                expiry=datetime.now() + timedelta(hours=24),  # Token valid for 1 hour
            )

            file.url = f"{self.accountUrl}{self.containerName}/{file.name}?{sas_token}"
            
            print(f"\t{index+1}/{len(files)} uploaded...")
            
        end_time = time.time()
        duration = end_time - start_time
        print(f"All done, took => {duration:.2f} seconds")

        return files