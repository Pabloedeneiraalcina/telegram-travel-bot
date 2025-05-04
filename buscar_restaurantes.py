

import requests
import time
import folium
from geopy.geocoders import Nominatim
import math

# ---------- INPUT DE USUARIO ----------
input_ejemplo = {
    "ciudad": "Moncloa",
    "categoria": "hamburguesa",  # Esto se usará como keyword
    "rating_minimo": 3
}

API_KEY = api_key  # Asegúrate de que esto contiene tu API Key válida

# ---------- FUNCIONES DE GEOGRAFÍA ----------
def obtener_coordenadas(ciudad):
    geolocator = Nominatim(user_agent="mi_geocoder")
    location = geolocator.geocode(ciudad)
    if location:
        return location.latitude, location.longitude
    else:
        raise ValueError("Ciudad no encontrada")

def generar_limites_cuadrado(lat_centro, lng_centro, metros=480):
    delta_lat = metros / 111_000
    delta_lng = metros / (111_000 * math.cos(math.radians(lat_centro)))
    Sup_Izq = {'lat': lat_centro + delta_lat, 'lng': lng_centro - delta_lng}
    Inf_Der = {'lat': lat_centro - delta_lat, 'lng': lng_centro + delta_lng}
    return Sup_Izq, Inf_Der

def generar_minicuadrados(Sup_Izq, Inf_Der, lado_celda_m=120):
    min_lat, max_lat = Inf_Der['lat'], Sup_Izq['lat']
    min_lng, max_lng = Sup_Izq['lng'], Inf_Der['lng']
    lat_step = lado_celda_m / 111_000
    lng_step = lado_celda_m / (111_000 * math.cos(math.radians((min_lat + max_lat) / 2)))
    minicuadrados = []
    for i in range(int((max_lat - min_lat) / lat_step)):
        for j in range(int((max_lng - min_lng) / lng_step)):
            bottom_left = (min_lat + i * lat_step, min_lng + j * lng_step)
            bottom_right = (bottom_left[0], bottom_left[1] + lng_step)
            top_left = (bottom_left[0] + lat_step, bottom_left[1])
            top_right = (top_left[0], bottom_right[1])
            centro = ((top_left[0] + bottom_left[0]) / 2, (top_left[1] + top_right[1]) / 2)
            minicuadrados.append({
                "bottom_left": bottom_left,
                "bottom_right": bottom_right,
                "top_left": top_left,
                "top_right": top_right,
                "centro": centro
            })
    return minicuadrados

def dentro_de_limites(lat, lng, Sup_Izq, Inf_Der):
    return (Inf_Der['lat'] <= lat <= Sup_Izq['lat']) and (Sup_Izq['lng'] <= lng <= Inf_Der['lng'])

# ---------- COORDENADAS Y CUADRÍCULA ----------
ciudad = input_ejemplo["ciudad"]
lat, lng = obtener_coordenadas(ciudad)
Sup_Izq, Inf_Der = generar_limites_cuadrado(lat, lng)
minicuadrados = generar_minicuadrados(Sup_Izq, Inf_Der)

# ---------- FUNCIÓN DE BÚSQUEDA (USANDO KEYWORD) ----------
def buscar_lugares_google(lat, lng, keyword, radio=60):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radio,
        "type": "restaurant",         # SIEMPRE restaurant como base
        "keyword": keyword,           # Aquí usamos "pizza", "japanese", etc.
        "key": API_KEY
    }
    response = requests.get(url, params=params)
    return response.json()

# ---------- BÚSQUEDA EN LA CUADRÍCULA ----------
resultados_unicos = {}

for celda in minicuadrados:
    lat_c, lng_c = celda["centro"]
    data = buscar_lugares_google(lat_c, lng_c, input_ejemplo["categoria"])

    if data["status"] != "OK":
        continue

    for lugar in data["results"]:
        place_id = lugar.get("place_id")
        rating = lugar.get("rating", 0)
        coords = lugar["geometry"]["location"]
        lat_lugar = coords["lat"]
        lng_lugar = coords["lng"]

        if rating < input_ejemplo["rating_minimo"]:
            continue

        if not dentro_de_limites(lat_lugar, lng_lugar, Sup_Izq, Inf_Der):
            continue

        if place_id not in resultados_unicos:
            resultados_unicos[place_id] = {
                "nombre": lugar.get("name"),
                "direccion": lugar.get("vicinity"),
                "rating": rating,
                "coordenadas": coords
            }

    time.sleep(0.2)

# ---------- RESULTADOS Y MAPA ----------
print(f"\n🔎 Total lugares encontrados con rating >= {input_ejemplo['rating_minimo']}: {len(resultados_unicos)}")
for lugar in resultados_unicos.values():
    print(f"- {lugar['nombre']} ({lugar['rating']}) - {lugar['direccion']}")

# Crear mapa centrado en la ciudad
m = folium.Map(location=[lat, lng], zoom_start=16)

# 🔴 SOLO AÑADIMOS MARCADORES DE RESTAURANTES (SIN CUADRÍCULAS NI PUNTOS VERDES)
for lugar in resultados_unicos.values():
    folium.Marker(
        location=[lugar["coordenadas"]["lat"], lugar["coordenadas"]["lng"]],
        popup=f"<b>{lugar['nombre']}</b><br>{lugar['direccion']}<br>⭐ {lugar['rating']}",
        icon=folium.Icon(color="red", icon="cutlery", prefix="fa")
    ).add_to(m)

m
