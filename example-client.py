import sys

from h2tp import fetch

response = fetch(f"h2tp://127.0.0.1:2220{sys.argv[1] or '/' if len(sys.argv) >= 2 else '/'}")

if response is None:
    print("Invalid response!")
else:
    print(response)
