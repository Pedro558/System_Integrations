from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, patch_servicenow_record
from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from System_Integrations.utils.servicenow_api import post_to_servicenow_table
from System_Integrations.utils.gestao_x_api import get_gestao_x
from System_Integrations.utils.mapper import map_to_requests_response
from .BaseTicketProcessingStrategy import BaseTicketProcessingStrategy
from .ISnowTicketProcessingStrategy import ISnowTicketProcessingStrategy


class ProactiveTicketStrategy(BaseTicketProcessingStrategy, ISnowTicketProcessingStrategy):
    """
        Strategy for transmiting proactive tickets (originally from Gestão X) to Servicenow
    """
    _url_snow = None
    _url_gestao_x = None
    _client_id = None
    _client_secret = None
    _refresh_token = None
    _token = None
    
    GX_tickets = []
    tickets_to_post = []
    results = []
    evidence_results = []

    def __init__(self, url_snow, url_gestao_x) -> None:
        self._url_snow = url_snow
        self._url_gestao_x = url_gestao_x
        # self._client_id = client_id
        # self._client_secret = client_secret
        # self._refresh_token = refresh_token

    def get_auth(self):
        super().get_auth()
        self._token = get_servicenow_auth_token(self._url_snow, self._servicenow_client_id, self._servicenow_client_secret, self._service_now_refresh_token)

    def fetch_list(self):
        url = self._url_gestao_x + "api/chamado/Retorna_chamados_acompanhamento_solicitantes"
        params = {
            "Login": self._gestao_x_login,
            "Token": self._gestao_x_token
        }
        self.GX_tickets = get_gestao_x(url, params)
    
    def _does_it_exist(self, code):
        found = False

        table = "u_integradora_gestao_x"
        params = {"sysparm_query": "u_ticket_gestao_xLIKE"+code}

        lookUp = get_servicenow_table_data(self._url_snow, table, params=params, token = self._token)
    
        if lookUp:
            found = True
        else:
            found = False
            
        return found
    
    def processing(self):
        if not self.GX_tickets:
            raise Exception("No new proactive tickets to process")
        for ticket in self.GX_tickets:
            if '---TESTE INTEGRAÇÃO---' in ticket['DESCRICAO']:
                    continue
            if self._does_it_exist(ticket['CODIGO']):
                print(f"Ticket {ticket['CODIGO']} já foi integrado")
                continue
            
            url_detalhes = self._url_gestao_x + "api/chamado/RetornaDetalhesChamados"
            params_detalhes = {
                "CodigoChamado": ticket['CODIGO'],
                "Token": self._gestao_x_token
            }
            detalhes_chamado = get_gestao_x(url_detalhes, params = params_detalhes)
            codigo = detalhes_chamado['CODIGO'][:3]
            
            match codigo: #SELECIONA DADOS DE ABERTURA DO SERVICENWO (CLIENTE/SOLICITANTE)
                case "EAD": #ARAUCO
                    opener_requester = {
                        "inc":{
                            "company": "cc7f7f951bfcd110bef1a79fe54bcbb2", #company cliente
                            "caller_id": "7f73108d87624e1405eaa8630cbb3541", #usuário dummy everest
                        },
                        "req":{
                            "requested_for": "6bfcb1fe1b6e2110bef1a79fe54bcb4d", #matricula dummy da empresa
                            "opened_by":"7f73108d87624e1405eaa8630cbb3541", #matricula dummy da everest
                        }
                    }
                case "EDI": #DIMED
                    opener_requester = {
                        "inc":{
                            "company": "2c7fbf951bfcd110bef1a79fe54bcb07", #company cliente
                            "caller_id": "7f73108d87624e1405eaa8630cbb3541", #usuário dummy everest
                        },
                        "req":{
                            "requested_for": "740d35fe1b6e2110bef1a79fe54bcbb9", #matricula dummy da empresa
                            "opened_by":"7f73108d87624e1405eaa8630cbb3541", #matricula dummy da everest
                        }
                    }
                case "EFU": #FATL
                    opener_requester = {
                        "inc":{
                            "company": "b47fbf951bfcd110bef1a79fe54bcb79", #company cliente
                            "caller_id": "7f73108d87624e1405eaa8630cbb3541", #usuário dummy everest
                        },
                        "req":{
                            "requested_for": "000df1fe1b6e2110bef1a79fe54bcb56", #matricula dummy da empresa
                            "opened_by":"7f73108d87624e1405eaa8630cbb3541", #matricula dummy da everest
                        }
                    }
                case "EUN": #UNIMED
                    opener_requester = {
                        "inc":{
                            "company": "2c7fbf951bfcd110bef1a79fe54bcb07", #company cliente
                            "caller_id": "7f73108d87624e1405eaa8630cbb3541", #usuário dummy everest
                        },
                        "req":{
                            "requested_for": "740d35fe1b6e2110bef1a79fe54bcbb9", # matricula dummy da empresa
                            "opened_by":"7f73108d87624e1405eaa8630cbb3541", #matricula dummy da everest
                        }
                    }
                case _:  #OUTROS
                    #TODO VALIDAR TODOS OS SYS_ID DE PRD
                    opener_requester ={
                        "inc":{
                            "company": "707fbf951bfcd110bef1a79fe54bcb42", #company cliente
                            "caller_id": "7f73108d87624e1405eaa8630cbb3541"# usuário dummy everest
                        },
                        "req":{
                            "requested_for": "a45641c387bb655005eaa8630cbb35d8", #matricula dummy da empresa
                            "opened_by":"7f73108d87624e1405eaa8630cbb3541" # matricula dummy da everest
                            # EM PROD USAR: 7f73108d87624e1405eaa8630cbb3541
                        }
                    }

            #DADOS PARA ABERTURA DE INCIDENTE
            if detalhes_chamado["EMX_TIPO_ITEM"] == "I":
                ticket_to_post = {
                    "CODIGO": detalhes_chamado['CODIGO'],
                    "type":detalhes_chamado["EMX_TIPO_ITEM"],
                    "inc":{
                        "company": opener_requester["inc"]["company"],
                        "caller_id": opener_requester["inc"]["caller_id"],
                        "contact_type": "Email",
                        "short_description": "[EVEREST] Ticket: "+ticket['CODIGO'],
                        "description": "Ticket "+ticket['CODIGO']+" aberto originalmente no Gestão X da Everest e replicado através da integração.\nMaiores detalhes nas notas de atualização do ticket.",
                        "state": "New",
                        "assignment_group": "Gr.Suporte N3"
                    }
                }

            #DADOS PARA SOLICITAÇÕES E OUTROS CHAMADOS
            else: #elif detalhes_chamado["EMX_TIPO_ITEM"] == "S":
                ticket_to_post = {
                    "CODIGO": detalhes_chamado['CODIGO'],
                    "type":detalhes_chamado["EMX_TIPO_ITEM"],
                    "req":{
                        "requested_for": opener_requester["req"]["requested_for"],
                        "opened_by": opener_requester["req"]["opened_by"],
                        "short_description": "Ticket "+ticket['CODIGO']+" aberto originalmente no Gestão X da Everest e replicado através da integração.",
                        "description": "[EVEREST] Ticket: "+ticket['CODIGO'],
                        "state":"new"
                    },
                    "ritm":{
                        "post": {
                            "request": None,
                            "assignment_group":"Gr.Suporte N3",
                            "short_description": "[EVEREST] Ticket: "+ticket['CODIGO'],
                            "description": "Ticket "+ticket['CODIGO']+" aberto originalmente no Gestão X da Everest e replicado através da integração.\nMaiores detalhes nas notas de atualização do ticket.",
                            "u_is_integrated":"true",
                            "state":"new"
                        },
                        "patch": {
                            "short_description": "[EVEREST] Ticket: "+ticket['CODIGO'],
                            "description": "Ticket "+ticket['CODIGO']+" aberto originalmente no Gestão X da Everest e replicado através da integração.\nMaiores detalhes nas notas de atualização do ticket."
                        }
                    }
                }
            
            self.tickets_to_post.append(ticket_to_post)

    def post(self):
        table_req = "sc_request"
        table_ritm = "sc_req_item"
        table_inc = "incident"

        params = {"sysparm_input_display_value":"true"}

        for ticket in self.tickets_to_post:     
            if ticket["type"] == "I":
                result = post_to_servicenow_table(self._url_snow, table_inc, data = ticket["inc"], token = self._token, params = params)

            else: #ticket["type"] == "S"
                #Post request to nest RITM:
                result_req = post_to_servicenow_table(self._url_snow, table_req, data = ticket["req"], token = self._token, params = params)
                response = map_to_requests_response(result_req['response'])
                ticket["ritm"]["post"]["request"] = response.json()['result']['sys_id']
                
                #Post RITM
                result = post_to_servicenow_table(self._url_snow, table_ritm, data = ticket["ritm"]["post"], token = self._token, params = params)
                result_sys_id = map_to_requests_response(result["response"]).json()['result']['sys_id']

                #Devido a uma questão de timing/sincronia, é necessario usar um delay ou o metodo patch para adicionar o Resumo e Descrição da RITM.
                result_patch = patch_servicenow_record(self._url_snow, table_ritm, result_sys_id, ticket["ritm"]["post"], token = self._token, params = params)
            self.results.append({**result, "item":ticket})

    def show_results(self):
        for ticket in self.results:
            print("--------------------------------")
            if ticket["error"]:
                print(ticket["errorMsg"])
                continue
            response = map_to_requests_response(ticket['response'])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Ticket {ticket['item']['CODIGO']} was opened as {response.json()['result']['number']} in ServiceNow")
            else:
                print(f"Error while trying to open Ticket {ticket['item']['CODIGO']} in ServiceNow")
                print(f"{response.status_code}")
                print(f"{response.reason}")

    def post_evidence(self):
        table = "u_integradora_gestao_x"
        params = {"sysparm_input_display_value":"true"}

        for result in self.results:
            body = {
                "u_requested_item":map_to_requests_response(result['response']).json()['result']['number'],
                "u_ticket_gestao_x":result['item']['CODIGO']
            }
            evidence_result = post_to_servicenow_table(self._url_snow, table, body, self._token, params)

            self.evidence_results.append({**evidence_result, "item":body})

    def show_evidence_results(self): 
        for evidence in self.evidence_results:
            print("--------------------------------")
            if evidence["error"]:
                print(evidence["errorMsg"])
                continue
            response = map_to_requests_response(evidence['response'])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Record created in u_integradora_gestao_x for {evidence['item']['u_requested_item']} integrated with Gestão X ticket {evidence['item']['u_ticket_gestao_x']}")
            else:
                print(f"Error while trying to update u_integradora_gestao_x for {evidence['item']['u_requested_item']} with Gestão X ticket {evidence['item']['u_ticket_gestao_x']}")
                print(f"{response.status_code}")
                print(f"{response.reason}")