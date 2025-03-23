from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/templates/index.html"
        try:
            with open(f".{self.path}", "rb") as file:
                self.send_response(200)
                if self.path.endswith(".html"):
                    self.send_header("Content-type", "text/html")
                elif self.path.endswith(".css"):
                    self.send_header("Content-type", "text/css")
                elif self.path.endswith(".js"):
                    self.send_header("Content-type", "application/javascript")
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        if self.path == "/api/submissions":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            linkedin = data.get("linkedin")
            devpost = data.get("devpost")
            email = data.get("email")

            try:
                response = (
                    supabase.table("interested_organizers")
                    .insert({"linkedin": linkedin, "devpost": devpost, "email": email})
                    .execute()
                )
                print("Insert response:", response)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"message": "Submission successful!"}).encode()
                )
            except Exception as e:
                print("Insert error:", e)
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_error(404, "Endpoint Not Found")


def run(server_class=HTTPServer, handler_class=MyHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port http://localhost:{port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
