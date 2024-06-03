from System_Integrations.ServiceNow.Strategies.ServiceNow.ProactiveTicketStrategy import ProactiveTicketStrategy
from System_Integrations.ServiceNow.Strategies.ServiceNow.ServiceNowTicketProcessingContext import ServiceNowTicketProcessingContext

#URL produção
url_gestao_x = "https://csc.everestdigital.com.br/API/"
url_servicenow_prd = "https://eleadev.service-now.com/"


strat = ProactiveTicketStrategy(
    url_snow=url_servicenow_prd,
    url_gestao_x=url_gestao_x,
)

ticket_context = ServiceNowTicketProcessingContext(strat)
ticket_context.get_auth()
ticket_context.fetch_list()
ticket_context.processing()

ticket_context.post()
ticket_context.show_results()

ticket_context.post_evidence()
ticket_context.show_evidence_results()