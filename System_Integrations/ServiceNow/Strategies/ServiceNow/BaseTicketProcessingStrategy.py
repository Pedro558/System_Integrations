import requests
import json
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token
from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from abc import ABC, abstractmethod
from typing import List
from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.utils.mapper import map_to_requests_response
from collections import defaultdict

class BaseTicketProcessingStrategy():
    # gestao_x_login = None
    # gestao_x_token = None

    # gestao_x_login_arauco = None
    # gestao_x_login_dimed = None
    # gestao_x_login_fatl = None
    # gestao_x_login_unimed = None

    # _servicenow_client_id = None
    # _servicenow_client_secret = None
    # _service_now_refresh_token = None

    def get_auth(self):
        # TODO deifinir como privado
        self.gestao_x_login = "INTEGRACAOELEA" #get_api_token('gestao-x-prd-login')
        self.gestao_x_token = "cJV3s9yjRStcS0LHV0boSQ==" #get_api_token('gestao-x-prd-api-token')

        self.gestao_x_login_arauco = "INTEGRACAOELEAARAUCO" #get_api_token("gestao-x-prd-login-arauco")
        self.gestao_x_login_dimed = "INTEGRACAOELEADIMED" #get_api_token("gestao-x-prd-login-dimed")
        self.gestao_x_login_fatl = "INTEGRACAOELEAFUNDACAOATLANTICO" #get_api_token("gestao-x-prd-login-fatl")
        self.gestao_x_login_unimed = "INTEGRACAOELEAUNIMED" #get_api_token("gestao-x-prd-login-unimed")

        self._servicenow_client_id = "ae6874cab78c8250ccc109956c8cc239" #get_api_token('servicenow-prd-client-id-oauth')
        self._servicenow_client_secret = "m^mbYcSqG@" #get_api_token('servicenow-prd-client-secret-oauth')
        self._service_now_refresh_token = "mT7eo3nX8mesAWKvlRTgKTRW2qYb7F-NluXpDZMmrmIn0UZ9Ak_7cwoIS4s5DKo8wfxUGq3732g3iVam9RlQ4A" #get_api_token('servicenow-prd-refresh-token-oauth')

    def get_login_solicitante(self, company_sys_id, descricao):
        login_solicitante = None

        match company_sys_id:
        #ARAUCO
            case "cc7f7f951bfcd110bef1a79fe54bcbb2":
                login_solicitante = self.gestao_x_login_arauco
            #DIMED
            case "2c7fbf951bfcd110bef1a79fe54bcb07":
                login_solicitante = self.gestao_x_login_dimed
            #FATL                                                       b47fbf951bfcd110bef1a79fe54bcb79
            case "b47fbf951bfcd110bef1a79fe54bcb79":
                login_solicitante = self.gestao_x_login_fatl
            #UNIMED
            case "287fbf951bfcd110bef1a79fe54bcb04":
                login_solicitante = self.gestao_x_login_unimed
            case _:
                login_solicitante = self.gestao_x_login
                descricao += "Solicitação feita por cliente não pré cadastrado na integração.\nFavor entrar em contato com o Service Desk para avaliar.\nCaso necessário comunique a equipe de integração.\n\n"

        return login_solicitante, descricao