from mqtt_framework import Framework
from mqtt_framework import Config
from mqtt_framework.callbacks import Callbacks
from mqtt_framework.app import TriggerSource

from prometheus_client import Counter

from datetime import datetime
from pyunifi.controller import Controller
import os
import json
from flask import render_template


class MyConfig(Config):
    def __init__(self):
        super().__init__(self.APP_NAME)

    APP_NAME = "unifimonitor2mqtt"

    # App specific variables

    UNIFI_HOST = None
    UNIFI_PORT = 443
    UNIFI_SITE = "default"
    UNIFI_USERNAME = None
    UNIFI_PASSWORD = None
    LOG_TO_FILE = None
    DATA_FILE = "/data/data.txt"


class MyApp:
    def init(self, callbacks: Callbacks) -> None:
        self.logger = callbacks.get_logger()
        self.config = callbacks.get_config()
        self.metrics_registry = callbacks.get_metrics_registry()
        self.add_url_rule = callbacks.add_url_rule
        self.publish_value_to_mqtt_topic = callbacks.publish_value_to_mqtt_topic
        self.subscribe_to_mqtt_topic = callbacks.subscribe_to_mqtt_topic
        self.succesfull_fecth_metric = Counter(
            "succesfull_fecth", "", registry=self.metrics_registry
        )
        self.fecth_errors_metric = Counter(
            "fecth_errors", "", registry=self.metrics_registry
        )

        self.add_url_rule("/", view_func=self.result_page)

    def get_version(self) -> str:
        return "2.0.0"

    def stop(self) -> None:
        self.logger.debug("Exit")

    def subscribe_to_mqtt_topics(self) -> None:
        pass

    def mqtt_message_received(self, topic: str, message: str) -> None:
        pass

    def do_healthy_check(self) -> bool:
        return True

    # Do work
    def do_update(self, trigger_source: TriggerSource) -> None:
        self.logger.debug(f"update called, trigger_source={trigger_source}")

        self.succesfull_fecth_metric.inc()

        try:
            users = self.fetch_user_list()
        except Exception as e:
            self.fecth_errors_metric.inc()
            self.logger.error(f"Error occured: {e}")
            return
        
        old_user_macs = self.read_list_from_file(self.config["DATA_FILE"])

        new_user_macs = [user["mac"] for user in users]
        new_user_macs.sort()

        new_macs = self.diff(old_user_macs, new_user_macs)
        new_macs_count = len(new_macs)
        self.logger.info(f"New users found: {new_macs_count}")

        new_users = []

        if new_macs_count > 0:
            self.write_list_to_file(self.config["DATA_FILE"], new_user_macs)
            for mac in new_macs:
                if user := self.get_user(mac, users):
                    new_users.append(user)
                    self.hanle_new_user(user)

        if new_users:
            jsonString = json.dumps(new_users)
            self.publish_value_to_mqtt_topic(
                "newUsersChanged",
                str(datetime.now().replace(microsecond=0).isoformat()),
                True,
            )
            self.publish_value_to_mqtt_topic("newUsers", jsonString, True)

    def get_user(self, mac, users):
        for user in users:
            if mac == user["mac"]:
                return user

    def hanle_new_user(self, user):
        if self.config["LOG_TO_FILE"]:
            self.append_line_to_file(
                self.config["LOG_TO_FILE"],
                f"{datetime.now()}: {user}",
            )

        mac = user.get("mac")
        hostname = user.get("hostname")
        name = user.get("name")
        self.logger.info(
            f"New user details: mac={mac}, hostname={hostname}, name={name}"
        )

    def result_page(self):
        allusers = self.fetch_user_list()
        user_list = [
            {
                "mac": user.get("mac"),
                "hostname": user.get("hostname"),
                "name": user.get("name"),
            }
            for user in allusers
        ]
        return render_template(
            "index.html", json=json.dumps(allusers, indent=2), users=user_list
        )

    def fetch_user_list(self):
        self.logger.debug(
            "Fetch users from host %s:%d",
            self.config["UNIFI_HOST"],
            self.config["UNIFI_PORT"],
        )

        ctrl = Controller(
            self.config["UNIFI_HOST"],
            self.config["UNIFI_USERNAME"],
            self.config["UNIFI_PASSWORD"],
            site_id=self.config["UNIFI_SITE"],
            version="UDMP-unifiOS",
            ssl_verify=False,
        )

        allusers = ctrl.get_users()
        self.logger.debug(allusers)
        self.log_users(allusers)
        return allusers

    def log_users(self, allusers) -> None:
        self.logger.debug("Current user list: %d", len(allusers))
        self.logger.debug(" %-17s  %-40s %-40s", "MAC", "HOSTNAME", "NAME")
        self.logger.debug("".ljust(100, "-"))

        for user in allusers:
            self.logger.debug(
                " %-17s  %-40s %-40s",
                user.get("mac"),
                user.get("hostname"),
                user.get("name"),
            )

    def diff(self, list1, list2) -> list:
        return list(set(list1).symmetric_difference(set(list2)))

    def write_list_to_file(self, filename, list) -> None:
        with open(filename, "w") as f:
            for i in list:
                f.write(i + "\n")

    def read_list_from_file(self, filename) -> list:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return [line.rstrip("\n") for line in f]
        else:
            return []

    def append_line_to_file(self, filename, line) -> None:
        with open(filename, "a+") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    Framework().run(MyApp(), MyConfig())
