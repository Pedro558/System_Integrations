# TODO É necessário separar esse código em diversos módulos?
# TODO PRECISO VERIFICAR A CONDIÇÃO DE ABERTURA DE CHAMADO NO GESTÃO X

import requests
import json
from ...auth.api_secrets import get_api_token
from ...utils.mapper import map_to_requests_response

#URLs
url_gestao_x = "https://csc.everestdigital.com.br/API/"
url_servicenow = "https://eleadev.service-now.com/"

#Tokens
gestao_x_login = get_api_token('gestao-x-prd-login')
#print(gestao_x_login)
gestao_x_userId = get_api_token('gestao-x-prd-userid')
#print(gestao_x_userId)
gestao_x_token = get_api_token('gestao-x-prd-api-token')
#print(gestao_x_token)
servicenow_client_id = get_api_token('servicenow-dev-client-id-oauth')
#print(servicenow_client_id)
servicenow_client_secret = get_api_token('servicenow-dev-client-secret-oauth')
#print(servicenow_client_secret)
service_now_refresh_token = get_api_token('servicenow-dev-refresh-token-oauth')
#print(service_now_refresh_token)

#Parametros da API https://csc.everestdigital.com.br/API/api/chamado/RetornaChamadosSolicitante
params_fetch_chamados_gestao_x = {
    "Usuarioid": gestao_x_userId,
    "Token": gestao_x_token,
}

#Variavel de parametros para GET na API do ServiceNow
#Recebe uma Encoded Query no formato do ServiceNow de acordo com a necessidade dentro das funções onde é necessário
params_encoded_query = {
    "sysparam_query": "",
}

params_input_display_value = {
    "sysparm_input_display_value": "",
}


#Gera uma nova token de acesso ao ServiceNow com o uso da 'refresh_token'
#https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0778194
def get_auth_token():
    url = url_servicenow+"/oauth_token.do"
    body = {
        "grant_type": "refresh_token",
        "client_id":servicenow_client_id,
        "client_secret":servicenow_client_secret,
        "refresh_token":service_now_refresh_token, #TODO perguntar pro filipe sobre a localização dessas variaveis dentro do código
    }

    response = requests.post(url, data=body)
    data = response.json()
    #print(data)

    return data["access_token"]



#Busca os chamados em acompanhamento no Gestão X
def fetch_chamados_gestao_x(url, params):
    try:
        response = requests.get(url+"api/chamado/RetornaChamadosSolicitante", params=params)
        if response.status_code == 200:
            ticket_data = response.json()
            return ticket_data
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET RetornaChamadosSolicitante: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET RetornaChamadosSolicitante: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET RetornaChamadosSolicitante: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on GET RetornaChamadosSolicitante: {err}")



#Verifica se o ticket (Gestão X) já está cadastrado no ServiceNow ou não
#Caso não esteja, quer dizer que o ticket foi proativamente aberto no Gestão X e deve ser cadastrado no ServiceNow para acompanhamento.
def does_it_exist(code, params, token):
    try:
        found = False
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer "+token,
        }
        params["sysparm_query"] = "u_ticket_gestao_xLIKE"+code

        response = requests.get(url_servicenow+"api/now/table/u_integradora_gestao_x", headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if not 'result' in data or len(data['result']) == 0:
                found = False
            else:
                found = True
                
            return found
        
        else:
            response.raise_for_status()
        
    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on POST api/table/u_gestao_x_integradora: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on POST api/table/u_gestao_x_integradora: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on POST api/table/u_gestao_x_integradora: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on POST api/table/u_gestao_x_integradora: {err}")
   


#Insere as novas informações dos historicos dos chamados do Gestão X na tabela integradora de atualizações (u_integradora_gestao_x_atualizacoes)
#Ao criar os registros nessa tabela o Flow 'ELEA-LB: Gestão X - Escreve atualizações recebidas dos tickets' realiza a atualização da RITM.
def create_proactive_ritm(tickets, token):  
    try:
        if not tickets:
            raise Exception("Tickets array is empty")

        url = url_servicenow+"/api/now/table/sc_req_item"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+token,
        }

        params = params_input_display_value

        params["sysparm_input_display_value"] = "true"

        results = []
        
        response = requests.Response()
        for ticket in tickets:
            try:
                if not does_it_exist(ticket['CODIGO'], params_encoded_query, token):
                    body = {
                        "assignment_group":"Gr.Suporte N3",
                        "u_is_integrated":"true",
                        "state":"new"
                    }
                    response = requests.post(url, headers=headers, params=params, data=json.dumps(body))

                    results.append({
                        "item": ticket,
                        "response": response.__dict__,
                    })  

                else:
                    print(f"Ticket {ticket['CODIGO']} has a corresponding RITM")

            except requests.exceptions.HTTPError as err: # HTTP Error
                raise Exception(f"HTTP error occurred on POST api/table/u_gestao_x_integradora_atualizacoes: {err}")
            except requests.exceptions.ConnectionError as err: # Connection Error
                raise Exception(f"Connection error on POST api/table/u_gestao_x_integradora_atualizacoes: {err}")
            except requests.exceptions.Timeout as err: # Timeout
                raise Exception(f"Request timed out on POST api/table/u_gestao_x_integradora_atualizacoes: {err}")
            except requests.exceptions.RequestException as err: # Request Exception
                raise Exception(f"A request exception occurred on POST api/table/u_gestao_x_integradora_atualizacoes: {err}")  
        
        return results
                
    except Exception as err:
        raise Exception(err)
 

results = create_proactive_ritm(fetch_chamados_gestao_x(url_gestao_x, params_fetch_chamados_gestao_x), get_auth_token())

for result in results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Ticket {result['item']['CODIGO']} was opened as {response.json()['result']['number']} in ServiceNow")
            else:
                print(f"Error while trying to open Ticket {result['item']['CODIGO']} in ServiceNow")
                print(f"{response.status_code}")
                print(f"{response.reason}")