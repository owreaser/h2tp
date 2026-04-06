from h2tp import HEADER_IDS, H2TPData, Response, Server

app = Server()

@app.router("/")
def index(data: H2TPData) -> str:
    return "Hello, world!"

@app.router()
def fallback(data: H2TPData) -> Response:
    return Response(
        "Page not found!",
        headers={
            HEADER_IDS.STATUS: "404 Not Found"
        }
    )

app.run(hostname="127.0.0.1", port=2220)
