from machine import Pin, ADC
from time import sleep
import network
import dht
from umqttsimple import MQTTClient
from config import USUARIO, CLAVE

sensor = dht.DHT22(Pin(16))
luz = ADC(Pin(26))
led_verde = Pin(18, Pin.OUT)
led_rojo = Pin(19, Pin.OUT)

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("Wokwi-GUEST", "")

print("Conectando WiFi...")
for i in range(20):
    if wifi.isconnected():
        break
    sleep(1)

if not wifi.isconnected():
    raise RuntimeError("No se pudo conectar al WiFi")

print("WiFi conectado")

modo = "auto"

def recibir_mensaje(tema, mensaje):
    global modo
    comando = mensaje.decode().strip().lower()
    if comando in ("auto", "normal", "alerta"):
        modo = comando
        print("Comando recibido:", comando)
        cliente.publish((USUARIO + "/feeds/eventos").encode(), ("Comando: " + comando).encode())

cliente = MQTTClient("pico-industrial", "io.adafruit.com", 1883, USUARIO, CLAVE, keepalive=60)
cliente.set_callback(recibir_mensaje)
cliente.connect()
cliente.subscribe((USUARIO + "/feeds/comando").encode())
print("MQTT conectado")

while True:
    try:
        cliente.check_msg()
        sensor.measure()
        temperatura = sensor.temperature()
        humedad = sensor.humidity()
        lectura_luz = luz.read_u16()

        print("Temperatura:", temperatura, "C")
        print("Humedad:", humedad, "%")
        print("Luz:", lectura_luz)

        alerta = temperatura > 30 or humedad > 70 or lectura_luz < 15000
        if modo == "alerta":
            alerta = True
        elif modo == "normal":
            alerta = False

        if alerta:
            led_rojo.value(1)
            led_verde.value(0)
            estado = "alerta"
            print("Alerta en produccion")
        else:
            led_rojo.value(0)
            led_verde.value(1)
            estado = "normal"
            print("Produccion normal")

        cliente.publish((USUARIO + "/feeds/temperatura").encode(), str(temperatura).encode())
        cliente.publish((USUARIO + "/feeds/humedad").encode(), str(humedad).encode())
        cliente.publish((USUARIO + "/feeds/luz").encode(), str(lectura_luz).encode())
        cliente.publish((USUARIO + "/feeds/estado").encode(), estado.encode())
        print("Datos enviados")
        print("--------------------")
    except OSError as error:
        print("Error de sensor o conexion:", error)
        try:
            cliente.connect()
            cliente.subscribe((USUARIO + "/feeds/comando").encode())
        except OSError:
            print("Sin conexion MQTT")

    sleep(15)
