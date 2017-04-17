from http.server import HTTPServer,SimpleHTTPRequestHandler
from socketserver import BaseServer
import ssl

httpd = HTTPServer(('0.0.0.0', 3000), SimpleHTTPRequestHandler)
httpd.socket = ssl.wrap_socket (httpd.socket,
	certfile='/home/reports/.ssl/server.crt',
	keyfile='/home/reports/.ssl/server.key',
	server_side=True)
httpd.serve_forever()
