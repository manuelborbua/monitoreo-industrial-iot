import sqlite3
from datetime import datetime
import paho.mqtt.client as mqtt
from config import USUARIO, CLAVE

conexion = sqlite3.connect("industrial.db", check_same_thread=False)
conexion.executescript(open("database.sql", encoding="utf-8").read().split("SELECT *")[0])
datos = {}

def al_conectar(cliente, userdata, flags, rc):
    if rc == 0:
        print("Conectado a Adafruit IO")
        cliente.subscribe(USUARIO + "/feeds/+")
    else:
        print("Error de conexion:", rc)

def al_mensaje(cliente, userdata, mensaje):
    nombre = mensaje.topic.split("/")[-1]
    valor = mensaje.payload.decode()
    fecha = datetime.now().isoformat(timespec="seconds")
    print(fecha, nombre, valor)

    if nombre in ("comando", "eventos"):
        conexion.execute("INSERT INTO eventos (fecha, tipo, detalle) VALUES (?, ?, ?)", (fecha, nombre, valor))
    elif nombre in ("temperatura", "humedad", "luz", "estado"):
        datos[nombre] = valor
        if nombre == "estado" and all(k in datos for k in ("temperatura", "humedad", "luz")):
            conexion.execute("INSERT INTO lecturas (fecha, temperatura, humedad, luz, estado) VALUES (?, ?, ?, ?, ?)",
                             (fecha, float(datos["temperatura"]), float(datos["humedad"]), int(datos["luz"]), valor))
            datos.clear()
    conexion.commit()

cliente = mqtt.Client(client_id="pc-industrial", protocol=mqtt.MQTTv311)
cliente.username_pw_set(USUARIO, CLAVE)
cliente.on_connect = al_conectar
cliente.on_message = al_mensaje
cliente.connect("io.adafruit.com", 1883, 60)
print("Guardando datos. Ctrl+C para salir")
try:
    cliente.loop_forever()
finally:
    conexion.close()
