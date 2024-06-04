
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token
from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from System_Integrations.utils.servicenow_api import patch_servicenow_record
from System_Integrations.utils.gestao_x_api import post_gestao_x
from System_Integrations.utils.gestao_x_api import get_gestao_x
from System_Integrations.utils.mapper import map_to_requests_response
from .BaseTicketProcessingStrategy import BaseTicketProcessingStrategy
from .ISnowTicketProcessingStrategy import ISnowTicketProcessingStrategy


class GXTicketUpdateStrategy(BaseTicketProcessingStrategy, ISnowTicketProcessingStrategy):
    """
        Strategy for updating Gestão X tickets with information from Snow
    """
    _url_snow = None
    _url_gestao_x = None
    _client_id = None
    _client_secret = None
    _refresh_token = None
    _token = None
    
    work_notes = []
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
        table = "u_integradora_gestao_x_atualizacoes"

        params = {
            "sysparm_query": "u_posted=false",
            "sysparm_fields": "u_ticket_gestao_x.u_ticket_gestao_x, u_descricao, u_data_da_atualizacao, sys_id"
        }        
        
        self.work_notes = get_servicenow_table_data(self._url_snow, table, params, self._token)

        if not self.work_notes:
            raise Exception("No Work Notes found")

    def processing(self):
        url = self._url_gestao_x + "api/chamado/RetornaDetalhesChamados"
        
        for work_note in self.work_notes:
            CodigoChamado = work_note['u_ticket_gestao_x.u_ticket_gestao_x']

            params = {
                "CodigoChamado": CodigoChamado,
                "Token": self._gestao_x_token
            }

            detalhes_chamados = get_gestao_x(url, params = params)

            if detalhes_chamados['RESPONSAVEL_LOGIN_USER'] == "":
                loginResponsavel = "INTEGRACAOELEA"
            else:
                loginResponsavel = detalhes_chamados['RESPONSAVEL_LOGIN_USER']

            status = detalhes_chamados['STATUS_ID']
            
            self.snow_updates_to_post.append({
                "sys_id": work_note["sys_id"],
                "u_data_da_atualizacao": work_note["u_data_da_atualizacao"],
                "body":{
                    "CodigoChamado": CodigoChamado,
                    "Token": self._gestao_x_token,
                    "Descricao": "Atualização através do ServiceNow:\n"+work_note['u_descricao'],
                    "Status": status,
                    "LoginResponsavel": loginResponsavel #TODO pendente atualização do Paulo sobre essa API
                }
            })          

    def post(self):
        url = self._url_gestao_x + "api/chamado/AlterarChamado"

        headers = {
            "Content-Type": "application/json",
            "Application": ""
        }
        for update in self.snow_updates_to_post:
            result = post_gestao_x(url, headers = headers, data = update["body"])

            self.results.append({**result, "item": update})

    def show_results(self): 
        for update in self.results:
            print("--------------------------------")
            if update["error"]:
                print(update["errorMsg"])
                continue
            response = map_to_requests_response(update["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Updated {update['item']['body']['CodigoChamado']} with the update from {update['item']['u_data_da_atualizacao']}")
            else:
                print(f"Error while trying to update ticket {update['item']['body']['CodigoChamado']} with the update from {update['item']['u_data_da_atualizacao']}")
                print(f"{response.status_code}")
                print(f"{response.reason}")

    def post_evidence(self):
        for update in self.results:
            table = "u_integradora_gestao_x_atualizacoes"
            record = update['item']['sys_id']

            body = {"u_posted": "true"}
            
            evidence_result = patch_servicenow_record(self._url_snow, table, record, body, self._token)
            
            self.evidence_results.append({**evidence_result, "item": update['item']})
        
    def show_evidence_results(self): 
        for result in self.evidence_results:
            print("--------------------------------")
            if result["error"]:
                print(result["errorMsg"])
                continue
            response = map_to_requests_response(result["response"])
            #breakpoint()
            if response.status_code == 200 or response.status_code == 201:
                print(f"Corresponding Work Note for {result['item']['body']['CodigoChamado']} at {result['item']['u_data_da_atualizacao']} marked as posted")
            else:
                print(f"Error while trying to update ticket {result['item']['body']['CodigoChamado']} with the update from {result['item']['u_data_da_atualizacao']}")
                print(f"Code: {response.status_code}")
                print(f"Message: {response.reason}")