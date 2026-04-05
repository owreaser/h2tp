from h2tp import fetch

response = fetch("h2tp://127.0.0.1:2220/")

if response is None:
    print("Invalid response!")
else:
    print(response["body"])
