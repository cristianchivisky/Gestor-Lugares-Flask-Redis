#app con Flask
from flask import Flask, request, jsonify, render_template
from redis import Redis, ConnectionError
from flask_bootstrap import Bootstrap
from lugares import places, groups_interest

app = Flask(__name__)
bootstrap = Bootstrap(app)

def connect_db():
    """Función para conectar a la base de datos Redis"""
    try:
        conexion = Redis(host='db-redis', port=6379, decode_responses=True)
        conexion.ping()
        print("Conectado a Redis")
        return conexion
    except ConnectionError as e:
        print("Error de conexión con Redis:", e)
        return None

def load_places():
    """Función para cargar los capítulos en la base de datos Redis"""
    con = connect_db()
    if con and con.dbsize() == 0:
        for place in places:
            group = place['grupo']
            longitude = place['longitud']
            latitude = place['latitud']
            name = place['nombre']
            coordinates = (longitude, latitude, name)
            con.geoadd(group, coordinates)

load_places()

def get_all_places():
    """Función para obtener todos los nombres de los lugares de cada grupo de interés"""
    con = connect_db()
    all_places = {}
    for group in groups_interest:
        places = con.zrange(group, 0, -1)  # Obtiene todos los lugares del grupo
        all_places[group] = places
    return all_places

def validate_coordinates(latitude, longitude):
    """Valida que las coordenadas de latitud y longitud estén dentro de los rangos permitidos."""
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        return False, "Las coordenadas deben ser números."
    
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return False, "La latitud debe estar en el rango [-90, 90] y la longitud en el rango [-180, 180]."
    return True, None

@app.route('/', methods=['GET', 'POST'])
def index():  
    """Renderizar la plantilla index.html"""
    return render_template('index.html')

@app.route('/cargar_lugar', methods=['GET'])
def add_place():
    """Agrega un lugar al grupo de interés correspondiente"""
    group_interest = request.args.get('grupo')
    latitude = request.args.get('latitud')
    longitude = request.args.get('longitud')
    name = request.args.get('nombre')
    message = None
    if latitude and longitude and name:
        valid, error_message = validate_coordinates(latitude, longitude)
        if not valid:
            return render_template('cargar_lugar.html', message=error_message)
    
        con = connect_db()
        coordinates = (longitude, latitude, name)
        con.geoadd(group_interest, coordinates)
        message = f'{name} fue agregado correctamente al grupo {group_interest}.'

    return render_template('cargar_lugar.html', message=message)

@app.route('/lugares_cerca', methods=['GET'])
def get_places():
    """Muestra los lugares cercanos a la ubicación del usuario"""
    longitude = request.args.get('longitud', default=None)
    latitude = request.args.get('latitud', default=None)
    filtered_places=[]
    
    if latitude and longitude:
        valid, error_message = validate_coordinates(latitude, longitude)
        if not valid:
            return render_template('lugares_cerca.html', message=error_message)
    
        con = connect_db()
        for group in groups_interest:
            places = con.georadius(group, longitude, latitude, 5000, unit='m')
            for place in places:
                place_info = con.geopos(group, place)[0]
                place_obj = {
                    'grupo': group,
                    'nombre': place,
                    'latitud': place_info[1],
                    'longitud': place_info[0]
                }
                filtered_places.append(place_obj)

    return render_template("lugares_cerca.html", places=filtered_places)

@app.route('/calcular_distancia', methods=['GET'])
def get_distance():
    """Calcula la distancia entre la ubicación del usuario y un lugar seleccionado"""
    user_longitude = request.args.get('longitud')
    user_latitude = request.args.get('latitud')
    selected_option = request.args.get('place')
    message = None
    all_places = get_all_places()

    if user_latitude and user_longitude:
        valid, error_message = validate_coordinates(user_latitude, user_longitude)
        if not valid:
            return render_template('calcular_distancia.html', all_places=all_places, message=error_message)
    
        user_location = (user_longitude, user_latitude, 'mi_ubicacion')
        place, group = selected_option.split('|')
        con = connect_db()
        con.geoadd(group, user_location)
        distance = con.geodist(group, 'mi_ubicacion', place, unit='m')
        message = f'La distancia entre la ubicación ingresada y {place} es: {distance} metros'
        con.zrem(group, 'mi_ubicacion')

    return render_template('calcular_distancia.html', all_places=all_places, message=message)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', error="¡Ooops! La página que buscas no está en el servidor!"), 404

if __name__ == '__main__':
    app.run(host='web-api-flask', port='5000', debug=True)
