
from http.server import HTTPServer, BaseHTTPRequestHandler

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

print("Starting test server on 127.0.0.1:5001...")
server_address = ("127.0.0.1", 5001)
httpd = HTTPServer(server_address, TestHandler)
print("Server started!")
httpd.serve_forever()
