from Publishertest import MqttPublisher
from Subscribertest import MqttSubscriber

BROKER_IP = "test.mosquitto.org"

with MqttSubscriber(broker=BROKER_IP, port=1883) as sub, MqttPublisher(broker=BROKER_IP, port=1883) as pub:
    sub.subscribe("Lighting/#", qos=0)

    pub.publish("Lighting/topic1", "Hallo aus main.py")
    pub.publish("Lighting/sensortemp", "23.7")

    input("Enter zum Beenden (Subscriber bleibt aktiv)...\n")