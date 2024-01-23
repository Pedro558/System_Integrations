import os
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient

def get_api_token(system):
    #  Get parameters
    appId = os.getenv('RD_OPTION_APPID')
    appSecret = os.getenv('RD_OPTION_APPSECRET')

    # Create a Service Principal credential
    tenantId = "a3f930ac-efea-47ba-9671-a3024e6c4e15"
    credential = ClientSecretCredential(client_id=appId, client_secret=appSecret, tenant_id=tenantId)

    # Get Azure KeyVault
    vaultName = "sys-int-prd-keyvault"
    keyvaultUri = f"https://{vaultName}.vault.azure.net"
    secret = SecretClient(vault_url=keyvaultUri, credential=credential)

    # Get KeyVault Secret
    secretName = f"{system}"
    print(f"Requesting {system} API Token")
    apiToken = secret.get_secret(secretName)
    apiToken = apiToken.value
    return apiToken