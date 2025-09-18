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
	street = data.get('address', 'N/A')
	city = data.get('city')
	region = data.get('region')
	postal = data.get('postal')
	country = data.get('country_name')
	if street != 'N/A':
		address = f"{street}, {city}, {region} {postal}, {country}"
	else:
		address = f"{city}, {region} {postal}, {country}"
	return address

print("IP Address:", get_ip_address())
print("Physical Address:", get_physical_address())