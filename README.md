# unifimonitor2mqtt

Simple UniFi controller monitor tool to recognize new client devices and forward result to MQTT broker.

## Environament variables

See commonn environment variables from [MQTT-Framework](https://github.com/paulianttila/MQTT-Framework).

| **Variable**               | **Default**        | **Descrition**                                              |
|----------------------------|--------------------|-------------------------------------------------------------|
| CFG_APP_NAME               | unifimonitor2mqtt  | Name of the app.                                            |
| CFG_UNIFI_HOST             |                    | UniFi controller address.                                   |
| CFG_UNIFI_PORT             | 443                | UniFi controller port.                                      |
| CFG_UNIFI_USERNAME         |                    | Username for UniFi controller.                              |
| CFG_UNIFI_PASSWORD         |                    | Password for UniFi controller.                              |
| CFG_UNIFI_VERSION          | UDMP-unifiOS       | UniFi controller API version. v4|v5|unifiOS|UDMP-unifiOS    |
| DATA_FILE                  | /data/data.txt     | File name for data.                                         |


## Example docker-compose.yaml

```yaml
version: "3.5"

services:
  unifimonitor2mqtt:
    container_name: unifimonitor2mqtt
    image: paulianttila/unifimonitor2mqtt:2.0.0
    restart: unless-stopped
    environment:
      - CFG_LOG_LEVEL=DEBUG
      - CFG_MQTT_BROKER_URL=127.0.0.1
      - CFG_MQTT_BROKER_PORT=1883
      - CFG_UNIFI_HOST=<host>
      - CFG_UNIFI_PORT=8443
      - CFG_UNIFI_USERNAME=<username>
      - CFG_UNIFI_PASSWORD=<password>
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/healthy"]
      interval: 60s
      timeout: 3s
      start_period: 5s
      retries: 3
 ```