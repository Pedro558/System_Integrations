from System_Integrations.ServiceNow.Strategies.ServiceNow.ISnowTicketProcessingStrategy import ISnowTicketProcessingStrategy
from System_Integrations.utils.gestao_x_api import post_gestao_x
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token, post_to_servicenow_table
from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.utils.mapper import map_to_requests_response

class BaseTicketProcessingStrategy(ISnowTicketProcessingStrategy):
    _gestao_x_login = None
    _gestao_x_token = None

    _gestao_x_login_arauco = None
    _gestao_x_login_dimed = None
    _gestao_x_login_fatl = None
    _gestao_x_login_unimed = None

    _servicenow_client_id = None
    _servicenow_client_secret = None
    _service_now_refresh_token = None
    
    _url_snow = None
    _url_gestao_x = None
    _client_id = None
    _client_secret = None
    _refresh_token = None
    _token = None
    _table = None
    _fetch_params = None

    def get_auth(self):
        # TODO deifinir como privado
        self._gestao_x_login = get_api_token('gestao-x-prd-login') #"INTEGRACAOELEA"
        self._gestao_x_token = get_api_token('gestao-x-prd-api-token') #"cJV3s9yjRStcS0LHV0boSQ=="

        self._gestao_x_login_arauco = get_api_token("gestao-x-prd-login-arauco") #"INTEGRACAOELEAARAUCO"
        self._gestao_x_login_dimed = get_api_token("gestao-x-prd-login-dimed") #"INTEGRACAOELEADIMED"
        self._gestao_x_login_fatl = get_api_token("gestao-x-prd-login-fatl") #"INTEGRACAOELEAFUNDACAOATLANTICO"
        self._gestao_x_login_unimed = get_api_token("gestao-x-prd-login-unimed") #"INTEGRACAOELEAUNIMED"

        self._servicenow_client_id = get_api_token('servicenow-prd-client-id-oauth') #"ae6874cab78c8250ccc109956c8cc239"
        self._servicenow_client_secret = get_api_token('servicenow-prd-client-secret-oauth') #"m^mbYcSqG@"
        self._service_now_refresh_token = get_api_token('servicenow-prd-refresh-token-oauth') #"mT7eo3nX8mesAWKvlRTgKTRW2qYb7F-NluXpDZMmrmIn0UZ9Ak_7cwoIS4s5DKo8wfxUGq3732g3iVam9RlQ4A"

        self._token = get_servicenow_auth_token(self._url_snow, self._servicenow_client_id, self._servicenow_client_secret, self._service_now_refresh_token)

    def fetch_list(self):
        self.tickets = get_servicenow_table_data(self._url_snow, self._table, params = self._fetch_params, token = self._token)

    def get_login_solicitante(self, company_sys_id, descricao):
        login_solicitante = None

        match company_sys_id:
            #ARAUCO
            case "cc7f7f951bfcd110bef1a79fe54bcbb2":
                login_solicitante = self._gestao_x_login_arauco
            #DIMED
            case "2c7fbf951bfcd110bef1a79fe54bcb07":
                login_solicitante = self._gestao_x_login_dimed
            #FATL                                                       b47fbf951bfcd110bef1a79fe54bcb79
            case "b47fbf951bfcd110bef1a79fe54bcb79":
                login_solicitante = self._gestao_x_login_fatl
            #UNIMED
            case "287fbf951bfcd110bef1a79fe54bcb04":
                login_solicitante = self._gestao_x_login_unimed
            case _:
                login_solicitante = self._gestao_x_login
                descricao += "Solicitação feita por cliente não pré cadastrado na integração.\nFavor entrar em contato com o Service Desk para avaliar.\nCaso necessário comunique a equipe de integração.\n\n"

        return login_solicitante, descricao
    
    def processing(self):
        raise NotImplementedError()

    def post(self):
        
        url = self._url_gestao_x + 'api/chamado/AbrirChamado'
        headers = {
            "Content-Type": "application/json",
        }

        for ticket in self.tickets_to_post:
            data = ticket['data']
            result = post_gestao_x(url, headers, data)

            self.results.append({**result, "item": ticket})

    def show_results(self): 
        for ticket in self.results:
            print("--------------------------------")
            if ticket["error"]:
                #TODO
                continue
            response = map_to_requests_response(ticket['response'])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Ticket {ticket['item']['ticket_number']} was posted as {response.json()} in Gestão X")
            else:
                print(f"Error while trying to post ticket {ticket['item']['ticket_number']} with {ticket['item']['data']} history data")
                print(f"{response.status_code}")
                print(f"{response.reason}")

    def post_evidence(self):
        table = "u_integradora_gestao_x"
        params = {"sysparm_input_display_value":"true"}
        for result in self.results:
            data = {
                "u_ticket_gestao_x":map_to_requests_response(result['response']).json(),
                "u_requested_item":result['item']['ticket_number']
            }
            
            evidence_result = post_to_servicenow_table(self._url_snow, table, data, self._token, params = params)

            self.evidence_results.append({**evidence_result, "data": data}) #, "item": result["item"]

    def show_evidence_results(self): 
        for result in self.evidence_results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Record created in u_integradora_gestao_x for {result['data']['u_requested_item']} integrated with Gestão X ticket {result['data']['u_ticket_gestao_x']} ")
            else:
                print(f"Error while trying to update u_integradora_gestao_x for {result['data']['u_requested_item']} with Gestão X ticket {result['data']['u_ticket_gestao_x']}")
                print(f"Code: {response.status_code}")
                print(f"Message: {response.reason}")