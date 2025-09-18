"""
app.py
A small Flask app that:
 - Shows your public IP (detected server-side)
 - Does an IP-based geolocation (best-effort)
 - Serves a page that asks the browser for high-accuracy geolocation,
   sends back latitude/longitude to the server, which reverse-geocodes
   to a full street/building address (via OpenStreetMap Nominatim).

Requirements:
 - Python 3.8+
 - pip install flask requests

Run:
 $ pip install flask requests
 $ python app.py
 Then open http://127.0.0.1:5000 in the browser on the machine whose
 building/street address you want to capture, grant permission when prompted.
"""

from flask import Flask, request, jsonify, render_template_string
import socket
import requests

app = Flask(__name__)

# HTML page served to request browser geolocation and send back to server
HTML_PAGE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Get Device Location</title>
  </head>
  <body>
    <h2>Get device location (browser)</h2>
    <p id="status">Click the button and allow location access when prompted.</p>
    <button id="btn">Get my precise location</button>
    <pre id="result"></pre>

    <script>
      const status = document.getElementById('status');
      const result = document.getElementById('result');
      document.getElementById('btn').onclick = () => {
        if (!navigator.geolocation) {
          status.textContent = 'Geolocation not supported by this browser.';
          return;
        }
        status.textContent = 'Requesting location...';
        navigator.geolocation.getCurrentPosition(success, error, {enableHighAccuracy:true, timeout:20000});
      };

      function success(pos) {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const payload = {latitude: lat, longitude: lon};
        status.textContent = `Got coords: ${lat}, ${lon}. Sending to server for reverse-geocoding...`;
        fetch('/reverse', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        }).then(r => r.json())
          .then(data => {
            result.textContent = JSON.stringify(data, null, 2);
            status.textContent = 'Done.';
          })
          .catch(err => {
            status.textContent = 'Error contacting server: ' + err;
          });
      }

      function error(err) {
        status.textContent = 'Error getting location: ' + err.message;
      }
    </script>
  </body>
</html>
"""

def get_local_ip():
    """Return the local IP used to reach the internet (not loopback)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"

def get_public_ip():
    """Return the public IP address seen by external services."""
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return r.json().get('ip', 'N/A')
    except Exception:
        return "N/A"

def ip_geolocation(ip=None):
    """IP-based geolocation (best-effort). Uses ipapi.co free endpoint as fallback.
       This will usually return city/region/postal/country — not a building address.
    """
    try:
        url = "https://ipapi.co/json/" if ip is None else f"https://ipapi.co/{ip}/json/"
        r = requests.get(url, timeout=6)
        data = r.json()
        # Collect the common fields
        return {
            "ip": data.get("ip"),
            "city": data.get("city"),
            "region": data.get("region"),
            "postal": data.get("postal"),
            "country": data.get("country_name"),
            "latitude": data.get("latitude") or data.get("lat"),
            "longitude": data.get("longitude") or data.get("lon"),
            "raw": data
        }
    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def index():
    local_ip = get_local_ip()
    public_ip = get_public_ip()
    ip_geo = ip_geolocation(public_ip if public_ip != "N/A" else None)
    summary = {
        "local_ip": local_ip,
        "public_ip": public_ip,
        "ip_geolocation": ip_geo,
        "note": "IP-based geolocation typically does NOT return a precise street/building address."
    }
    # Render page with small UI (and link to open the geolocation UI)
    return render_template_string("""
    <h1>IP + Location demo</h1>
    <pre>{{summary}}</pre>
    <p><a href="/geo">Open browser geolocation page (requires permission)</a></p>
    """, summary=summary)

@app.route("/geo")
def geo_page():
    return HTML_PAGE

@app.route("/reverse", methods=["POST"])
def reverse_geocode():
    """
    Receive {latitude, longitude} and reverse geocode using OpenStreetMap Nominatim.
    Nominatim usage policy requires a valid User-Agent and rate-limiting on heavy use.
    """
    data = request.get_json()
    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is None or lon is None:
        return jsonify({"error": "latitude/longitude required"}), 400

    # Use OSM Nominatim reverse geocoding
    nominatim_url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "jsonv2",
        "lat": lat,
        "lon": lon,
        "addressdetails": 1,
        "zoom": 18  # higher zoom returns more granular address components
    }
    headers = {"User-Agent": "IP-to-Address-Demo/1.0 (+youremail@example.com)"}
    try:
        r = requests.get(nominatim_url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        resp = r.json()
        address = resp.get("display_name")
        address_details = resp.get("address", {})
        return jsonify({
            "latitude": lat,
            "longitude": lon,
            "display_name": address,
            "address_details": address_details,
            "raw": resp
        })
    except Exception as e:
        return jsonify({"error": f"reverse geocode failed: {e}"}), 500

if __name__ == "__main__":
    print("Starting app. Open http://127.0.0.1:5000 in a browser on the target device.")
    app.run(debug=True)
