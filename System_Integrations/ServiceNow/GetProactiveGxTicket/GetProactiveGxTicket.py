import requests
import json
from ...auth.api_secrets import get_api_token
from ...utils.mapper import map_to_requests_response

#URL produção
url_gestao_x = "https://csc.everestdigital.com.br/API/"
url_servicenow_prd = "https://servicenow.eleadigital.com/"

#Tokens produção
gestao_x_login = get_api_token('gestao-x-prd-login')
gestao_x_userid = get_api_token('gestao-x-prd-userid')
gestao_x_token = get_api_token('gestao-x-prd-api-token')

servicenow_client_id = get_api_token('servicenow-prd-client-id-oauth')
servicenow_client_secret = get_api_token('servicenow-prd-client-secret-oauth')
service_now_refresh_token = get_api_token('servicenow-prd-refresh-token-oauth')

#Parametros da API https://csc.everestdigital.com.br/API/api/chamado/Retorna_chamados_acompanhamento_solicitantes
params_fetch_chamados_gestao_x = {
    #"Usuarioid": gestao_x_userid,
    "Login": gestao_x_login,
    "Token": gestao_x_token,
}

#Variavel de parametros para GET na API do ServiceNow
#Recebe uma Encoded Query no formato do ServiceNow de acordo com a necessidade dentro das funções onde é necessário
params_encoded_query = {
    "sysparam_query": "",
}

#Recebe "true" OU "false".
#Se true, inserir o valor de Display de um dado campo funciona normalmente.
#Se false, é necessario inserir o Sys_ID
params_input_display_value = {
    "sysparm_input_display_value": "",
}


#Gera uma nova token de acesso ao ServiceNow com o uso da 'refresh_token'
#Tokens expiram a cada 1800 segundos (30 minutos), caso a função seja chamada multiplas vezes dentro desse periodo ela apenas retorna a mesma token ainda válida.
#https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0778194
def get_auth_token():
    url = url_servicenow_prd+"/oauth_token.do"
    body = {
        "grant_type": "refresh_token",
        "client_id":servicenow_client_id,
        "client_secret":servicenow_client_secret,
        "refresh_token":service_now_refresh_token,
    }

    response = requests.post(url, data=body)
    data = response.json()
    #print(data)

    return data["access_token"]



#Busca os chamados em acompanhamento no Gestão X
def fetch_chamados_gestao_x(url, params):
    try:
        response = requests.get(url+"api/chamado/Retorna_chamados_acompanhamento_solicitantes", params=params)
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
def does_it_exist(code, params, token):
    try:
        found = False
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer "+token,
        }
        params["sysparm_query"] = "u_ticket_gestao_xLIKE"+code

        response = requests.get(url_servicenow_prd+"api/now/table/u_integradora_gestao_x", headers=headers, params=params)

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
        raise Exception(f"HTTP error occurred on GET does_it_exist: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET does_it_exist: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET does_it_exist: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on GET does_it_exist: {err}")
   


#Caso não exista uma RITM criada no ServiceNow para documentar o Ticket do Gestão X, cria essa RITM, atribuida ao grupo Gr.Suporte N3 e constando como já integrada.
#Essa ritm será atualizada normalmente junto das demais que estão integradas.
def create_proactive_ritm(tickets, token):  
    try:
        if not tickets:
            raise Exception("Tickets array is empty")

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
                    response = requests.post(url_servicenow_prd+"/api/now/table/sc_req_item", headers=headers, params=params, data=json.dumps(body))

                    results.append({
                        "item": ticket,
                        "response": response.__dict__,
                    })

                else:
                    print(f"Ticket {ticket['CODIGO']} has a corresponding RITM")

            except requests.exceptions.HTTPError as err: # HTTP Error
                raise Exception(f"HTTP error occurred on POST create_proactive_ritm: {err}")
            except requests.exceptions.ConnectionError as err: # Connection Error
                raise Exception(f"Connection error on POST create_proactive_ritm: {err}")
            except requests.exceptions.Timeout as err: # Timeout
                raise Exception(f"Request timed out on POST create_proactive_ritm: {err}")
            except requests.exceptions.RequestException as err: # Request Exception
                raise Exception(f"A request exception occurred on POST create_proactive_ritm: {err}")  
        
        return results
                
    except Exception as err:
        raise Exception(err)
 


#Cria registro na tabela integradora relacionando a nova RITM com seu ticket no Gestão X
def create_integradora_gestao_x_record(ritm, ticket):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+get_auth_token(),
        }

        params = params_input_display_value

        params["sysparm_input_display_value"] = "true"

        body = {
            "u_requested_item":ritm,
            "u_ticket_gestao_x":ticket
        }
        response = requests.post(url_servicenow_prd+"/api/now/table/u_integradora_gestao_x", headers=headers, params=params, data=json.dumps(body))

        results =[]

        results.append({
            "item": body,
            "response": response.__dict__,
        })

        return print(f"Registro integrador criado unindo a {ritm} ao ticket {ticket}")
    
    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on POST create_integradora_gestao_x_record: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on POST create_integradora_gestao_x_record: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on POST create_integradora_gestao_x_record: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on POST create_integradora_gestao_x_record: {err}")  



results = create_proactive_ritm(fetch_chamados_gestao_x(url_gestao_x, params_fetch_chamados_gestao_x), get_auth_token())

for result in results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            if response.status_code == 200 or response.status_code == 201:
                response = response.json()
                print(f"Ticket {result['item']['CODIGO']} was opened as {response['result']['number']} in ServiceNow")
                create_integradora_gestao_x_record(response['result']['number'], result['item']['CODIGO']) #Registro integrador é criado apenas caso a ritm seja adequadamente criada.
            else:
                print(f"Error while trying to open Ticket {result['item']['CODIGO']} in ServiceNow")
                print(f"{response.status_code}")
                print(f"{response.reason}")