import requests

url = "API_URL"

params = {
    "serviceKey": "인증키",
    "pageNo": 1,
    "numOfRows": 10,
    "type": "json"
}

response = requests.get(url, params=params)

print(response.status_code)
print(response.json())