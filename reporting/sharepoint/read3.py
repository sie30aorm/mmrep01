from urllib.parse import urlparse
from client.office365.runtime.auth.authentication_context import AuthenticationContext
from client.office365.sharepoint.client_context import ClientContext

username="alvaro.paricio@MasMovilE1.onmicrosoft.com"
password="99.Sofia"
url="https://masmovile1.sharepoint.com"

ctx_auth = AuthenticationContext(url)
if ctx_auth.acquire_token_for_user(username, password):
  ctx = ClientContext(url, ctx_auth)
  web = ctx.web
  ctx.load(web)
  ctx.execute_query()
  print("Web title: {0}".format(web.properties['Title']))

else:
  print(ctx_auth.get_last_error())
