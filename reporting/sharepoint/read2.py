import json

from client.office365.runtime.auth.authentication_context import AuthenticationContext
from client.office365.runtime.client_request import ClientRequest
from client.office365.runtime.utilities.request_options import RequestOptions

username="alvaro.paricio@MasMovilE1.onmicrosoft.com"
password="99.Sofia"
#Page:
# https://masmovile1.sharepoint.com/sites/Test2/control_financiero/Lists/ORG_DEPARTAMENTOS/AllItems.aspx
# spo_site="https://masmovile1.sharepoint.com/sites/Test2/control_financiero/_api/web/lists/ORG_DEPARTAMENTOS"
# spo_site="https://masmovile1.sharepoint.com/sites/Test2/control_financiero/_api/web/lists/getbytitle('ORG_DEPARTAMENTOS')/items"

spo_site="https://masmovile1.sharepoint.com"

ctxAuth = AuthenticationContext(spo_site)
if ctxAuth.acquireTokenForUser(username, password):
  request = ClientRequest(spo_site,ctxAuth)
  requestUrl = "/_api/web/"   #Web resource endpoint
  data = request.executeQuery(requestUrl=requestUrl)

  webTitle = data['d']['Title']
  print("Web title: {0}".format(webTitle))

else:
  print(ctxAuth.getLastErrorMessage())
