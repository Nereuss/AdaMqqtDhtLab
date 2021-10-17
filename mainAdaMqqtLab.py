import network
import time
import os
import urequests
import dht
import sys
from time import sleep
from umqtt.robust import MQTTClient
from machine import Pin, PWM

# counts while ticks to 1000 where it checks if connection
# is up or not, will try to reconnect if down
counter = 0

# wait until the device is connected to the WiFi network
MAX_ATTEMPTS = 20
attempt_count = 0

PING_INTERVAL = 60
client = None  # mqtt client
mqtt_con_flag = False  # mqtt connection flag
pingresp_rcv_flag = True  # indicator that we received PINGRESP

#LED 
frequency = 5000
start_duty = 1023

# Pins
sensor = dht.DHT11(Pin(17))
b = PWM(Pin(18), frequency, start_duty)

credentials = {
    "ssid": "----Insert here----",
    "password": "----Insert here----",
    "ADAFRUIT_IO_URL": b"io.adafruit.com",
    "ADAFRUIT_USERNAME": b"----Insert here----",
    "ADAFRUIT_IO_KEY": b"----Insert here----",
    "ADAFRUIT_IO_PUB_FEEDNAME": b"bot_pub",
    "ADAFRUIT_IO_SUB_FEEDNAME": b"bot_sub",
}
m = ""

# returns a new random ID to the API client connector
# Tried to give Ada a new id on connection attempt
def randomId():
    return bytes("client_" + str(int.from_bytes(os.urandom(3), "little")), "utf-8")

# create a random MQTT clientID
mqtt_client_id = randomId()
ADAFRUIT_IO_URL = credentials["ADAFRUIT_IO_URL"]
ADAFRUIT_USERNAME = credentials["ADAFRUIT_USERNAME"]
ADAFRUIT_IO_KEY = credentials["ADAFRUIT_IO_KEY"]
ADAFRUIT_IO_PUB_FEEDNAME = credentials["ADAFRUIT_IO_PUB_FEEDNAME"]
ADAFRUIT_IO_SUB_FEEDNAME = credentials["ADAFRUIT_IO_SUB_FEEDNAME"]

client = MQTTClient(
    client_id=mqtt_client_id,
    server=ADAFRUIT_IO_URL,
    user=ADAFRUIT_USERNAME,
    password=ADAFRUIT_IO_KEY,
    ssl=False,
)

# format of feed name:
#   "ADAFRUIT_USERNAME/feeds/ADAFRUIT_IO_FEEDNAME"
mqtt_pub_feedname = bytes(
    "{:s}/feeds/{:s}".format(ADAFRUIT_USERNAME, ADAFRUIT_IO_PUB_FEEDNAME), "utf-8"
)
mqtt_sub_feedname = bytes(
    "{:s}/feeds/{:s}".format(ADAFRUIT_USERNAME, ADAFRUIT_IO_SUB_FEEDNAME), "utf-8"
)

# WiFi connection information
WIFI_SSID = credentials["ssid"]
WIFI_PASSWORD = credentials["password"]

# turn off the WiFi Access Point
ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

# the following function is the callback which is
# called when subscribed data is received
def cb(topic, msg):
    if topic == mqtt_sub_feedname:
        global m
        m = msg.decode("utf-8")
        # print (m)
        m = m.lower()
        print(m)

#Checks if connected by pinging a google server and gets status code
def checkWifi():
    try:
        response = urequests.get("http://clients3.google.com/generate_204")
        print(response.status_code)
        if response.status_code == 204:
            print("online")
            return True
        elif response.status_code == 200:
            print("portal")
            return True
        else:
            print("offline")
            return False
    except Exception as e:
        print("Error: " , e)


def connectAda():
    try:
        # Disables connection to enable it again
        client.connect(False)
        time.sleep(3)
        print("Trying to connect to Ada")
        client.client_ID = randomId()
        client.connect(True)
        client.set_callback(cb)
        client.subscribe(mqtt_sub_feedname)
    except Exception as e:
        print("could not connect to MQTT server {}{}".format(type(e).__name__, e))
        # sys.exit()

def connectWifi():
    if not wifi.isconnected():
        wifi.disconnect()
        print("Connecting to network...")
        wifi.connect(WIFI_SSID, WIFI_PASSWORD)

        # connectAda()
    while not wifi.isconnected():
        pass
    print("network config: ", wifi.ifconfig())


# Runs connectWifi once
connectWifi()

# Runs once
connectAda()
print("mqtt script is done running")

while True:
    counter = counter + 1
    sensor.measure()
    temp = sensor.temperature()
    fahr = temp * (9/5) + 32.0 
    hum = sensor.humidity()
    try:
        sleep(2)
        print('Temperatur: %3.1f C, and %3.1f Fahrentheit' % (temp, fahr))
        print('Humidity:  ', hum, '%')
        #Note the reason for pass is that the try can get stuck inside a while loop
        #Pass makes it so the code can continue from this point
        pass
    except OSError as e:
        print('Failed to read sensor')
        pass
    
    
    try:
        if m == "hej bot":
            client.publish(topic=mqtt_pub_feedname, msg="Hej Master")
            # Tøm strengen igen, ellers vil den køre i en uendelighed og crashe :)
        if m == "fortael en joke":
            client.publish(topic=mqtt_pub_feedname, msg="Hvad er der i vejen med asfalt?")
        if m == "hvad er der galt med asfalt?":
            client.publish(topic=mqtt_pub_feedname, msg="Det ligger i vejen")
        if m == "fortael en joke mere":
            client.publish(topic=mqtt_pub_feedname, msg="Undskyld det kan jeg ikke, min far humor algoritmer er stadig under udvikling")
        if m == "hvad er temperaturen?":
            client.publish(topic=mqtt_pub_feedname, msg="temperaturen er %3.1f C"%temp)    
        if m == "hvad er fugtigheden?":
            client.publish(topic=mqtt_pub_feedname, msg="fugtigheden er %3.1f %%"%hum) 
        if temp >= 30:
            client.publish(topic=mqtt_pub_feedname, msg="Det er for varmt!!")
        if temp <= 18:
            client.publish(topic=mqtt_pub_feedname, msg="Det er for koldt!!")
        if m == "taend lys":
            b.duty(1)
            client.publish(topic=mqtt_pub_feedname, msg="Taender for lys") 
        if m == "sluk lys":
            b.duty(1023)
            client.publish(topic=mqtt_pub_feedname, msg="Slukker for lys") 
        m = ""
          
        # Tjekker for nye beskeder
        client.check_msg()
        pass
        
        # Stopper programmet når der trykkes Ctrl + c
    except KeyboardInterrupt:
        print("Ctrl-C pressed...exiting")
        client.disconnect()
        sys.exit()
   
    
    # Tried to see if I could reconnect to the internet and then Ada
    # However you need to go in and rewrite the mttq client import for async def functions for it to work
    # It is possible to reconnect to the internet again, but the mttq client is not made for it
    # if counter >= 15000:
#         print("Running Connect")
#         print("wifiConnected: ", checkWifi())
#         connectWifi()
#         connectAda()
#         counter = 0
