import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from model import FireRescueModel


model = None

def create_model(strategy='improved', num_agents=1):
    global model
    model = FireRescueModel(strategy=strategy, num_agents=num_agents)

class Server(BaseHTTPRequestHandler):
    def _set_response(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_response()

    def do_GET(self):
        if self.path == '/':
            try:
                with open('index.html', 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self._set_response('text/html')
                self.wfile.write(html_content.encode('utf-8'))
            except FileNotFoundError:
                self.send_error(404, "index.html not found")
        elif self.path == '/init':
            global model
            if model is None:
                create_model(strategy='improved', num_agents=1)
            self._set_response()
            response_data = {
                "status": "Game initialized",
                "game_state": model.get_state()
            }
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        elif self.path == '/step':
            if model:
                model.step()
                self._set_response()
                response_data = {
                    "status": "Firefighter action (1 AP) completed",
                    "game_state": model.get_state()
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_error(400, "Model not initialized")
        else:
            self.send_error(404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data) if post_data else {}

        if self.path == '/step':
            if model:
                model.step()
                self._set_response()
                response_data = {
                    "status": "Firefighter action (1 AP) completed",
                    "game_state": model.get_state()
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_error(400, "Model not initialized")
        elif self.path == '/step_firefighter':
            if model:
                model.step()
                self._set_response()
                response_data = {
                    "status": "Firefighter action (1 AP) completed",
                    "game_state": model.get_state()
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_error(400, "Model not initialized")
        elif self.path == '/step_fire':
            if model:
                model.advance_fire = True
                model.step()
                self._set_response()
                response_data = {
                    "status": "Fire phase completed",
                    "game_state": model.get_state()
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_error(400, "Model not initialized")
        elif self.path == '/step_complete_turn':
            if model:
                safety_counter = 0
                while getattr(model, 'advance_fire', False) is False and safety_counter < 100:
                    model.step()
                    safety_counter += 1
                if getattr(model, 'advance_fire', False):
                    model.step()
                self._set_response()
                response_data = {
                    "status": "Complete turn (all AP + fire) executed",
                    "game_state": model.get_state()
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_error(400, "Model not initialized")
        elif self.path == '/reset':
            strategy = data.get('strategy', 'improved')
            num_agents = min(data.get('num_agents', 1), 6)  # Enforce max 6 firefighters
            create_model(strategy, num_agents)
            self._set_response()
            response_data = {
                "status": f"Game reset with {num_agents} firefighter(s)",
                "game_state": model.get_state()
            }
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_error(404)

def run(server_class=HTTPServer, handler_class=Server, port=8585):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Starting httpd on port {port}...")
    logging.info("\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping httpd...")
    logging.info("\n")

if __name__ == '__main__':
    run()