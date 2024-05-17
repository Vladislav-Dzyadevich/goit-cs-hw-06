import mimetypes
import socket
import logging
import multiprocessing
import json

from pathlib import Path
from urllib.parse import urlparse, unquote_plus
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

URI_DB = "mongodb://mongodb:27017"
BASE_DIR = Path(__file__).parent
CHUNK_SIZE = 1024
HTTP_PORT = 3000
SOCKET_PORT = 5000
HTTP_HOST = "0.0.0.0"
SOCKET_HOST = "127.0.0.1"

class HttpGetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        router = urlparse(self.path).path
        match router:
            case "/":
                self.send_html(BASE_DIR / "index.html")
            case "/message_html":
                self.send_html(BASE_DIR / "message.html")
            case _:
                file = BASE_DIR.joinpath(router[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html(BASE_DIR / "404.html", 404)

    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
            client_socket.close()
        except socket.error:
            logging.error("Failed to send data")

        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def send_html(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def render_template(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open("db/data.json", "r", encoding="utf-8") as f:
            content = json.load(f)

        template = jinja.get_template(filename)
        html = template.render(posts=content)
        self.wfile.write(html.encode())

    def send_static(self, filename, status=200):
        self.send_response(status)
        mimetype = mimetypes.guess_type(filename)[0] or "text/plain"
        self.send_header("Content-type", mimetype)
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())

def run_http_server():
    httpd = HTTPServer((HTTP_HOST, HTTP_PORT), HttpGetHandler)
    try:
        logging.info(f"Server started: http://{HTTP_HOST}:{HTTP_PORT}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server stopped due to a KeyboardInterrupt")
    except Exception as e:
        logging.error(e)
    finally:
        logging.info("Server stopped")
        httpd.server_close()

def save_to_db(data):
    client = MongoClient(URI_DB, server_api=ServerApi('1'))
    db = client.homework
    try:
        data_parse = unquote_plus(data)
        data_dict = {
            key: value for key, value in [el.split("=") for el in data_parse.split("&")]
        }
        document = {"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}
        document.update(data_dict)
        db.messages.insert_one(document)
    except Exception as e:
        logging.error(e)
    finally:
        client.close()

def run_socket_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((SOCKET_HOST, SOCKET_PORT))
    logging.info(f"Server started: socket://{SOCKET_HOST}:{SOCKET_PORT}")
    try:
        while True:
            data, addr = server.recvfrom(CHUNK_SIZE)
            logging.info(f"Received from {addr}: {data.decode()}")
            save_to_db(data.decode())
    except Exception as e:
        logging.error(e)
    finally:
        logging.info("Server socket stopped")
        server.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(message)s")

    http_server = multiprocessing.Process(target=run_http_server, name="http_server")
    socket_server = multiprocessing.Process(target=run_socket_server, name="socket_server")

    http_server.start()
    socket_server.start()

    try:
        http_server.join()
        socket_server.join()
    except KeyboardInterrupt:
        logging.info("Servers are stopping due to a KeyboardInterrupt")
    finally:
        http_server.terminate()
        socket_server.terminate()
        http_server.join()
        socket_server.join()
        logging.info("Servers stopped")
