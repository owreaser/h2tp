from h2tp import Server

app = Server()

@app.router()
def index(data: dict) -> str:
    return "Hello, world!"

app.run(hostname="127.0.0.1", port=2220)
