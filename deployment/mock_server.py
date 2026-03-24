import http.server
import json

class MockHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        path = self.path.split('?')[0]

        if path == '/api/models/get-providers':
            # Returns {modelProviders: [], aiproxyIdMap: {}}
            resp = {"code": 0, "data": {"modelProviders": [], "aiproxyIdMap": {}}}
        elif path == '/api/models':
            # Returns list of models (array)
            resp = {"code": 0, "data": []}
        elif path == '/api/tools' or path == '/api/tools/tags':
            resp = {"code": 0, "data": []}
        else:
            resp = {"code": 0, "data": []}

        self.wfile.write(json.dumps(resp).encode())

    def log_message(self, format, *args):
        pass

print("Mock plugin server starting on port 3001...")
http.server.HTTPServer(('0.0.0.0', 3001), MockHandler).serve_forever()
