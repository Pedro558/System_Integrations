import requests
import json
from ...auth.api_secrets import get_api_token
from ...utils.mapper import map_to_requests_response
from ...utils.parser import get_value


# def map_to_requests_response(response_dict) -> requests.Response:
#     # Create a requests.Response instance
#     http_response = requests.Response()

#     # Set attributes using the dictionary data
#     for key, value in http_response.__dict__.items():
#         setattr(http_response, key, response_dict.get(key, value))

#     return http_response


#URLs
url_gestao_x = "https://csc.everestdigital.com.br/API/"
url_servicenow = "https://eleadev.service-now.com/"

#Tokens
gestao_x_login = get_api_token('gestao-x-prd-login')
#print(gestao_x_login)
gestao_x_token = get_api_token('gestao-x-prd-api-token')
#print(gestao_x_token)
servicenow_client_id = get_api_token('servicenow-dev-client-id-oauth')
#print(servicenow_client_id)
servicenow_client_secret = get_api_token('servicenow-dev-client-secret-oauth')
#print(servicenow_client_secret)
service_now_refresh_token = get_api_token('servicenow-dev-refresh-token-oauth')
#print(service_now_refresh_token)

#Variavel de parametros para GET na API do ServiceNow
#Recebe uma Encoded Query no formato do ServiceNow de acordo com a necessidade dentro das funções onde é necessário
serviceNow_params = {
    "sysparm_query": "",
    "sysparm_fields": ""
}

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



def fetch_ritm_servicenow(url, params, token):    
    params["sysparm_query"] = "assignment_group=3ee6ef4c1bb8d510bef1a79fe54bcbb3^u_is_integrated=false^stateNOT IN3,4,7,9,10,11" #TODO Avaliar Sys_ID do Gr.Suporte N3 em PRD
    params["sysparm_fields"] = "number, sys_id, cat_item.name"

    headers = {
            "Content-Type": "application/json",
            "Accept":"application/json",
            "Authorization": "Bearer "+token,
        }
    
    try:
        response = requests.get(url+"api/now/table/sc_req_item", headers=headers, params=params)
        
        ritm_list = response.json()
        #print("voltou response")
        if not 'result' in ritm_list or len(ritm_list['result']) == 0:
            raise Exception("No RITMs found")

        if response.status_code == 200:        
            return ritm_list['result']
        
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET fetch_ritm_servicenow: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET fetch_ritm_servicenow: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET fetch_ritm_servicenow: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on GET fetch_ritm_servicenow: {err}")



def fetch_ritm_variables (url, ritm, params, token):
    params["sysparm_query"] = "request_item.sys_id="+ritm['sys_id']   #get_value(ritm, lambda x : x['results']['sys_is'], None)
    params["sysparm_fields"] = "sys_id, sc_item_option.item_option_new.question_text, sc_item_option.value, sc_item_option.order"
    
    headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+token,
        }
    
    try:
        response = requests.get(url+"api/now/table/sc_item_option_mtom", headers=headers, params=params)
        if response.status_code == 200:
            variable_list = response.json()
            #print(variable_list[0])
            if not 'result' in variable_list or len(variable_list['result']) == 0:
                raise Exception(f"No variables found for {ritm['number']}")
            
            return variable_list['result']
        
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET fetch_ritm_variables: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET fetch_ritm_variables: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET fetch_ritm_variables: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on GET fetch_ritm_variables: {err}")



def descriptionBuilder(variables, descConfig):
    descricao = ""
    for config in descConfig:
        aValue = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == config["var"]]
                                                        #and config["extraValidator"](variable) if "extraValidator" in config else True]

        descricao += config["msg"] + aValue[0]["sc_item_option.value"]

    return descricao



def process_data(url, ritm_list):
    tickets_to_post = []
    if not ritm_list:
        return #tratar
    
    for ritm in ritm_list:
        variables = fetch_ritm_variables(url, ritm, serviceNow_params, get_auth_token())

        #Contact info is universal
        aQuestionContact = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "Contact"]
                    
        contactParams = {
            "sysparm_query": "sys_id="+aQuestionContact[0]["sc_item_option.value"],
            "sysparm_fields": "company.name, first_name, last_name, email, phone, mobile_phone"
        }
        header = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+get_auth_token(),
        }
        
        getContactInfo = requests.get(url_servicenow+"api/now/table/sys_user", params = contactParams, header=header)
        if getContactInfo.status_code == 200:
            contactInfo = getContactInfo.json()['result']
            valueContact = contactInfo[0]["first_name"]+" "+contactInfo["last_name"]
            valueCompany = contactInfo[0]["account"]
            valueEmail = contactInfo[0]["email"]
            valuePhone = contactInfo[0]["phone"]
            valueMobilePhone = contactInfo[0]["mobile_phone"]

        else:
            response.raise_for_status()

        descricao = ""
        if ritm['cat_item.name']:
            match ritm['cat_item.name']:
                case 'Operational system':           
                    # COLINHA:
                    # aQuestionHostname = list(filter(
                    #                             lambda variable: variable['question'] == 'hostname'
                    #                             , variables
                    #                             ))

                    # OU

                    # aQuestionHostname = [variable for variable in variables if variable["question"] == 'hostname']
                    
                    # ENTÃO

                    # questionHortname = aQuestionHostname[0]["value"]

                    #valueSummary = [variable["sc_item_option.value"] for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'Summary'][0]
                    #Essa alternativa retorna um array contendo somente o value e então entrega para a variavel a primeira posição (0) do array que é a string contendo o valor
                    #                    return   for each ele in array     if ele['key'] == 'value' 
                    #aQuestionSummary = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'Summary']
                    
                    #  Operating System
                    aQuestionWhatOperatingSystem = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "What Operating System?"]
                    valueWhatOperatingSystem = aQuestionWhatOperatingSystem[0]["sc_item_option.value"]
                    #  Unix Service
                    aQuestionWhatServiceWindows = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "What is the service?" and variable["sc_item_option.order"] == "5"]
                    valueWhatServiceWindows = aQuestionWhatServiceWindows[0]["sc_item_option.value"]
                    #  Windows Services
                    aQuestionWhatServiceUnix = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "What is the service?" and variable["sc_item_option.order"] == "6"]
                    valueWhatServiceUnix = aQuestionWhatServiceUnix[0]["sc_item_option.value"]
                    #  Reboot Time Start                
                    aQuestionRebootTimeStart = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == " What is the Server Reboot Time (Start)"] #sim, tem um espaço no nome da variavel
                    valueRebootTimeStart = aQuestionRebootTimeStart[0]["sc_item_option.value"] if len(aQuestionRebootTimeStart) > 0 else None
                    #  Reboot Time End
                    aQuestionRebootTimeEnd = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "What is the Server Reboot Time (end)"]
                    valueRebootTimeEnd = aQuestionRebootTimeEnd[0]["sc_item_option.value"] if len(aQuestionRebootTimeEnd) > 0 else None


                    descriptionConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What Operating System?", "msg": "\n\nSistema Operacional: "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}\n\n"
                    descricao += descriptionBuilder(variables, descriptionConfig)
                    if valueWhatOperatingSystem == 'windows':
                        descricao += f"\nTipo de serviço: {valueWhatServiceWindows}"
                    elif valueWhatOperatingSystem == 'unix':
                        descricao += f"\nTipo de serviço: {valueWhatServiceUnix}"
                    if valueRebootTimeStart:
                        descricao += f"\nHora do inicio do reboot: {valueRebootTimeStart}"
                    if valueRebootTimeEnd:
                        descricao += f"\n Hora do fim do reboot: {valueRebootTimeEnd}"

                case 'Backup':
                    descriptionConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What type of service?", "msg": "\n\nTipo de serviço: "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                    ]
                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}\n\n"
                    descricao += descriptionBuilder(variables, descriptionConfig)


                case 'Database':
                    aConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What is the Database Manager?", "msg": "\n\nGerenciador do banco (DBM): "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "},
                        {"var": "What is the instance?", "msg": "\nNome da instancia: "},
                        {"var": "What is the service?", "msg": "\nTipo de Serviço: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}\n\n"
                    descricao += descriptionBuilder(variables, aConfig)

                case 'Monitoring':
                    #  Blackout Window Start
                    aQuestionBlackoutWindowStart = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'What is the blackout window (start)']
                    valueBlackoutWindowStart = aQuestionBlackoutWindowStart[0]["sc_item_option.value"] if len(aQuestionBlackoutWindowStart) > 0 else None
                    #  Blackout Window End
                    aQuestionBlackoutWindowEnd = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'What is the blackout window (End)']
                    valueBlackoutWindowEnd = aQuestionBlackoutWindowEnd[0]["sc_item_option.value"] if len(aQuestionBlackoutWindowEnd) > 0 else None

                    aConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What is the service?", "msg": "\n\nTipo de serviço: "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}\n\n"
                    descricao += descriptionBuilder(variables, aConfig)
                    if valueBlackoutWindowStart:
                        descricao += f"\nInicio da janela do blackout: {valueBlackoutWindowStart}"
                    if valueBlackoutWindowEnd:
                        descricao += f"\nInicio da janela do blackout: {valueBlackoutWindowEnd}"

                case 'Storage':
                    aConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What is the service?", "msg": "\n\nTipo de serviço: "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}\n\n"
                    descricao += descriptionBuilder(variables, aConfig)
        else:
            continue

        ticket_to_post =  {
            "ritm_number": ritm['number'],
            "data": {
                "Descricao":descricao,
                "LoginSolicitante":gestao_x_login,
                "Token":gestao_x_token,
                "CatalogoServicosid":"1423"
            }
        }
        

        tickets_to_post.append(ticket_to_post)
                    

    return tickets_to_post



def openGestaoXTicket(url, tickets_to_post):
    url += 'api/chamado/AbrirChamado'
    headers = {
            "Content-Type": "application/json",
    }
    try:
        results =[]
        for ticket in tickets_to_post:
            response = requests.post(url, headers=headers, data=json.dumps(ticket['data']))
            if response.status_code == 200 or response.status_code == 201:
                results.append({
                    "item": ticket,
                    "response": response.__dict__,
                })  
            else:
                response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on POST openGestaoXTicket: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on POST openGestaoXTicket: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on POST openGestaoXTicket: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on POST openGestaoXTicket: {err}")


    return results



def postServiceNowIntegradora(url, token, tickets_posted):
    url += 'api/now/table/u_integradora_gestao_x?sysparm_input_display_value=true'
    headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+token,
        }
    
    try:
        results =[]
        for ticket in tickets_posted:
            data = {
                "u_ticket_gestao_x":map_to_requests_response(ticket['response']).json(),
                "u_requested_item":ticket['item']['ritm_number']
            }
            response = requests.post(url, headers=headers, data=json.dumps(data))
    
            if response.status_code == 200 or response.status_code == 201:
                results.append({
                    "item": ticket['item'],
                    "response": response.__dict__,
                })  
            else:
                response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on POST postServiceNowIntegradora: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on POST postServiceNowIntegradora: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on POST postServiceNowIntegradora: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on POST postServiceNowIntegradora: {err}")

    return results


ritms = fetch_ritm_servicenow(url_servicenow, serviceNow_params, get_auth_token())
tickets_to_post = process_data(url_servicenow, ritms)
tickets_posted = openGestaoXTicket(url_gestao_x, tickets_to_post)
results = postServiceNowIntegradora(url_servicenow, get_auth_token(), tickets_posted)

for ticket in tickets_posted:
            print("--------------------------------")
            response = map_to_requests_response(ticket["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"RITM {ticket['item']['ritm_number']} was posted as {map_to_requests_response(ticket['response']).json()} in Gestão X")
            else:
                print(f"Error while trying to post RITM {ticket['item']['ritm_number']} with {ticket['item']['data']} history data")
                print(f"{response.status_code}")
                print(f"{response.reason}")

for result in results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Record created in u_integradora_gestao_x for {result['item']['ritm_number']} integrated with Gestão X ticket {map_to_requests_response(ticket['response']).json()} ")
            else:
                print(f"Error while trying to update u_integradora_gestao_x for {result['item']['u_requested_item']} with Gestão X ticket {map_to_requests_response(ticket['response']).json()}")
                print(f"{response.status_code}")
                print(f"{response.reason}")