
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token
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
    snow_updates_to_post = []
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
            "Login": self.gestao_x_login,
            "Token": self.gestao_x_token
        }
        self.GX_tickets = get_gestao_x(url, params)
    
    def _does_it_exist(self, code):
        found = False

        params = {"sysparm_query": "u_ticket_gestao_xLIKE"+code}
        table = "u_integradora_gestao_x"

        lookUp = get_servicenow_table_data(self._url_snow, table, params=params, token = self._token)
    
        if lookUp:
            found = True
        else:
            found = False
            
        return found
    
    def processing(self):
        if not self.GX_tickets:
            raise Exception("No new proactive tickets to process")
        else:
            pass

    def post(self):
        table_req = "sc_request"

        table_ritm = "sc_req_item"

        params = {"sysparm_input_display_value":"true"}

        for ticket in self.GX_tickets:
            #breakpoint()
            if self._does_it_exist(ticket['CODIGO']):
                print("No new proactive tickets to process")
                continue
            
            body_req = {
                "requested_for": "a45641c387bb655005eaa8630cbb35d8", #Criar usuário em prod para substituir esse dummy
                "description": "[EVEREST] Ticket: "+ticket['CODIGO'],
                "short_description": "Ticket "+ticket['CODIGO']+" aberto originalmente no Gestão X da Everest e replicado através da integração.",
                "state":"new"
            }

            #Post request to nest RITM:
            result_req = post_to_servicenow_table(self._url_snow, table_req, data = body_req, token = self._token, params = params)
            response = map_to_requests_response(result_req['response'])
            breakpoint()
            body_ritm = {
                "request": response.json()['result']['sys_id'],
                "assignment_group":"Gr.Suporte N3",
                "description": "[EVEREST] Ticket: "+ticket['CODIGO'],
                "short_description": "Ticket "+ticket['CODIGO']+" aberto originalmente no Gestão X da Everest e replicado através da integração.\nMaiores detalhes nas notas de atualização do ticket.",
                "u_is_integrated":"true",
                "state":"new"
            }
            
            result_ritm = post_to_servicenow_table(self._url_snow, table_ritm, data = body_ritm, token = self._token, params = params)

            self.results.append({**result_ritm, "item":ticket})

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