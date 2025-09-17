import socket
import requests

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def get_physical_address():
    response = requests.get("https://ipapi.co/json/")
    data = response.json()
    city = data.get('city')
    region = data.get('region')
    country = data.get('country_name')
    address = f"{city}, {region}, {country}"
    return address

print("IP Address:", get_ip_address())
print("Physical Address:", get_physical_address())