from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from collections import defaultdict
from .BaseTicketProcessingStrategy import BaseTicketProcessingStrategy
from .ISnowTicketProcessingStrategy import ISnowTicketProcessingStrategy
import traceback

class RITMProcessingStrategy(BaseTicketProcessingStrategy, ISnowTicketProcessingStrategy):
    """
        Strategy for sending RITM tickets from servicenow to Gestao X
    """
    _url_snow = None
    _url_gestao_x = None
    _client_id = None
    _client_secret = None
    _refresh_token = None
    _token = None
    _table = 'sc_req_item'
    _fetch_params = {
        'sysparm_query': 'assignment_group=3ee6ef4c1bb8d510bef1a79fe54bcbb3^u_is_integrated=false^stateNOT IN3,4,7,9,10,11',
        'sysparm_fields':'number, sys_id, cat_item.name'
    }

    tickets = []
    tickets_to_post = []
    results = []
    evidence_results = []

    def __init__(self, url_snow, url_gestao_x) -> None:
        self._url_snow = url_snow
        self._url_gestao_x = url_gestao_x

    def _descriptionBuilder(self, variables, descConfig):
        descricao = ""
        for config in descConfig:
            aValue = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == config["var"]]
                                                            #and config["extraValidator"](variable) if "extraValidator" in config else True]

            descricao += config["msg"] + aValue[0]["sc_item_option.value"] if aValue[0]["sc_item_option.value"] else ""
            
        return descricao
    
    def _get_multi_row_question_answer(self, ritm_sys_id, cat_item_name):
        params = {
            'sysparm_fields': "item_option_new.question_text, row_index, value"
        }

        cat_item_name = "Networks"

        match cat_item_name:
            case 'Networks':
                params['sysparm_query'] = "variable_set=f9f1f6371b689510bef1a79fe54bcb43^parent_id="+ritm_sys_id+"^parent_table_name=sc_req_item"
                params['sysparm_fields'] = "item_option_new.question_text, row_index, value"
                
                table = "sc_multi_row_question_answer"
                getMultiRowData = get_servicenow_table_data(self._url_snow, table, params = params, token = self._token)
            
                results = defaultdict(list)

                #data = getMultiRowData.json()['result']

                for item in getMultiRowData:
                    row_id = item["row_index"]
                    question = item["item_option_new.question_text"]
                    answer = item["value"]
                    results[row_id].append({"question":question,"answer":answer})

                # key_names = results.keys()
                # key_names_list = [key_names]#list(key_names)

                key_names_list = list(results)

                description = ""
                counter = 0
                for key in key_names_list:
                    counter = counter+1
                    aQuestionSourceIp = [item for item in results[key] if item['question'] == "Source IP(s) (hosts/Subnets) Ex: 10.36.1.1/255.255.255.0"]
                    valueSourceIp = aQuestionSourceIp[0]['answer']

                    aQuestionDestinationIp = [item for item in results[key] if item['question'] == "Destination IP(s) (hosts/subnets) Ex: 10.39.1.151/255.255.255.0"]
                    valueDestinationIp = aQuestionDestinationIp[0]['answer']

                    aQuestionProtocol = [item for item in results[key] if item['question'] == "Protocol Ex: TCP, UDP"]
                    valueProtocol = aQuestionProtocol[0]['answer']

                    aQuestionPort = [item for item in results[key] if item['question'] == "Port / Service Ex: 80 (http)"]
                    valuePort = aQuestionPort[0]['answer']

                    aQuestionNatSourceIp = [item for item in results[key] if item['question'] == "NAT - Source IP(s) (hosts/Subnets) Ex: 10.36.1.1"]
                    valueNatsourceIp = aQuestionNatSourceIp[0]['answer']

                    aQuestionNatDestinationIp = [item for item in results[key] if item['question'] == "NAT - Destination IP(s) (hosts/Subnets) Ex: 10.39.1.151/255.255.255.0"]
                    valueNatDestinationIp = aQuestionNatDestinationIp[0]['answer']
                    
                    aQuestionNatProtocol = [item for item in results[key] if item['question'] == "NAT - Protocol Ex: TCP, UDP"]
                    valueNatProtocol = aQuestionNatProtocol[0]['answer']

                    aQuestionNatPort = [item for item in results[key] if item['question'] == "NAT - Port / Service Ex: 80 (http)"]
                    valueNatPort = aQuestionNatPort[0]['answer']

                    description += f"\n\n---Regra {counter}---\n"\
                                f"IP de Origem: {valueSourceIp if valueSourceIp else ''}\n"\
                                f"IP de Destino: {valueDestinationIp if valueDestinationIp else ''}\n"\
                                f"Protocolo: {valueProtocol if valueProtocol else ''}\n"\
                                f"Porta: {valuePort if valuePort else ''}\n"\
                                f"NAT - IP de Origem: {valueNatsourceIp if valueNatsourceIp else ''}\n"\
                                f"NAT - IP de Destino{valueNatDestinationIp if valueSourceIp else ''}\n"\
                                f"NAT - Protocolo: {valueNatProtocol if valueNatProtocol else ''}\n"\
                                f"NAT - Porta: {valueNatPort if valueNatPort else ''}"
                    
        return description

    def processing(self):
        try:
            if not self.tickets:
                print("No new RITM to process")
                return

            for ritm in self.tickets:
                #GET VARIABLES
                table_variables = "sc_item_option_mtom"
                params = {
                    "sysparm_query": "request_item.sys_id="+ritm['sys_id'],
                    "sysparm_fields": "sys_id, sc_item_option.item_option_new.question_text, sc_item_option.value, sc_item_option.order"
                }
                variables = get_servicenow_table_data(self._url_snow, table_variables, params = params, token = self._token)

                descricao = ""
                #END GET VARIABLES

                #GET CONTACT
                print(aQuestionContact)
                aQuestionContact = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "Contact"]
                table_contacts = "sys_user"
                contactParams = {
                    "sysparm_query": "sys_id="+aQuestionContact[0]["sc_item_option.value"],
                    "sysparm_fields": "company.name, company.sys_id, first_name, last_name, email, phone, mobile_phone"
                }

                contactInfo = get_servicenow_table_data(self._url_snow, table_contacts, params = contactParams, token = self._token)
                #END GET CONTACT

                valueContact = contactInfo[0]["first_name"]+" "+contactInfo[0]["last_name"]
                valueCompany = contactInfo[0]["company.name"]
                valueEmail = contactInfo[0]["email"]
                valuePhone = contactInfo[0]["phone"]
                valueMobilePhone = contactInfo[0]["mobile_phone"]
                valueCompanySysId = contactInfo[0]["company.sys_id"]

            #descricao = '---TESTE INTEGRAÇÃO---\n' #NECESSARIO EM DEV
            
            login_solicitante, _ = super().get_login_solicitante(valueCompanySysId, descricao) #valueCompanySysId, descricao)
            
            if ritm['cat_item.name']:
                match ritm['cat_item.name']:
                    case 'Operational system':                               
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

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)
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

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)

                    case 'Database':
                        descriptionConfig = [
                            {"var": "Summary", "msg": "\n\nResumo:\n" },
                            {"var": "Description", "msg": "\n\nDescrição:\n" },
                            {"var": "What is the Database Manager?", "msg": "\n\nGerenciador do banco (DBM): "},
                            {"var": "What is the server/hostname?", "msg": "\nNome do Host: "},
                            {"var": "What is the instance?", "msg": "\nNome da instancia: "},
                            {"var": "What is the service?", "msg": "\nTipo de Serviço: "}
                        ]

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)

                    case 'Monitoring':
                        #  Blackout Window Start
                        aQuestionBlackoutWindowStart = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'What is the blackout window (start)']
                        valueBlackoutWindowStart = aQuestionBlackoutWindowStart[0]["sc_item_option.value"] if len(aQuestionBlackoutWindowStart) > 0 else None
                        #  Blackout Window End
                        aQuestionBlackoutWindowEnd = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'What is the blackout window (End)']
                        valueBlackoutWindowEnd = aQuestionBlackoutWindowEnd[0]["sc_item_option.value"] if len(aQuestionBlackoutWindowEnd) > 0 else None

                        descriptionConfig = [
                            {"var": "Summary", "msg": "\n\nResumo:\n" },
                            {"var": "Description", "msg": "\n\nDescrição:\n" },
                            {"var": "What is the service?", "msg": "\n\nTipo de serviço: "},
                            {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                        ]

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)
                        if valueBlackoutWindowStart:
                            descricao += f"\nInicio da janela do blackout: {valueBlackoutWindowStart}"
                        if valueBlackoutWindowEnd:
                            descricao += f"\nInicio da janela do blackout: {valueBlackoutWindowEnd}"

                    case 'Storage':
                        descriptionConfig = [
                            {"var": "Summary", "msg": "\n\nResumo:\n" },
                            {"var": "Description", "msg": "\n\nDescrição:\n" },
                            {"var": " What is the service?", "msg": "\n\nTipo de serviço: "},
                            {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                        ]

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)

                    case 'Networks':
                        aQuestionWhatService = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == ' What is the service?']
                        valueWhatService = aQuestionWhatService[0]["sc_item_option.value"] if len(aQuestionWhatService) > 0 else None

                        descriptionConfig = [    
                            {"var": "Summary", "msg": "\n\nResumo:\n" },
                            {"var": "Description", "msg": "\n\nDescrição:\n" },
                            {"var": " What is the service?", "msg": "\n\nTipo de serviço: "},
                            {"var": " What network equipment?", "msg": "\nNome do equipamento: "} 
                        ]

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)
                        
                        if valueWhatService == ' firewall_nat_rule_include':
                            descricao += self._get_multi_row_question_answer(ritm['sys_id'], ritm['cat_item.name'])
                        elif valueWhatService == ' firewall_nat_rule_delete':
                            descricao += self._get_multi_row_question_answer(ritm['sys_id'], ritm['cat_item.name'])                     

        
            ticket_to_post =  {
                "ticket_number": ritm['number'],
                "data": {
                    "Descricao":descricao,
                    "LoginSolicitante": login_solicitante,
                    "Token": self._gestao_x_token,
                    "CatalogoServicosid":"2649" # especifico gestaoX
                }
            }
            
            self.tickets_to_post.append(ticket_to_post)
            
        except Exception as e:
            print(f"-!-!-!-!-!-!-!-ERROR START-!-!-!-!-!-!-!-\nError on {ritm['number']}:\n",traceback.format_exc(), "\n-!-!-!-!-!-!-!-ERROR END-!-!-!-!-!-!-!-")
