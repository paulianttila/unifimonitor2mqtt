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

    UNIFI_HOST = "127.0.0.1"
    UNIFI_PORT = 443
    UNIFI_SITE = "default"
    UNIFI_USERNAME = "admin"
    UNIFI_PASSWORD = None
    LOG_TO_FILE = None
    DATA_FILE = "~/data.txt"


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
        self.exit = False

    def get_version(self) -> str:
        return "1.0.0"

    def stop(self) -> None:
        self.logger.debug("Stopping...")
        self.exit = True
        self.logger.debug("Exit")

    def subscribe_to_mqtt_topics(self) -> None:
        pass

    def mqtt_message_received(self, topic: str, message: str) -> None:
        pass

    def do_healthy_check(self) -> bool:
        return True

    # Do work
    def do_update(self, trigger_source: TriggerSource) -> None:
        self.logger.debug("update called, trigger_source=%s", trigger_source)

        allusers = self.fetch_user_list()
        old_user_list = self.read_list_from_file(self.config["DATA_FILE"])

        new_user_list = [user["mac"] for user in allusers]
        new_user_list.sort()

        difference = self.diff(old_user_list, new_user_list)
        length = len(difference)
        self.logger.info("New users found: %d", length)

        new_users = []

        if length > 0:
            self.write_list_to_file(self.config["DATA_FILE"], new_user_list)
            for usr in difference:
                for user in allusers:
                    if usr == user["mac"]:
                        if self.config["LOG_TO_FILE"]:
                            self.append_line_to_file(
                                self.config["LOG_TO_FILE"],
                                f"{datetime.now()}: {user}",
                            )
                        new_users.append(user)
                        self.logger.info(
                            "%20s | %-30s  %-40s",
                            user.get("mac"),
                            user.get("hostname"),
                            user.get("name"),
                        )

        if new_users:
            jsonString = json.dumps(new_users)
            self.publish_value_to_mqtt_topic(
                "newUsersChanged",
                str(datetime.now().replace(microsecond=0).isoformat()),
                True,
            )
            self.publish_value_to_mqtt_topic("newUsers", jsonString, True)

    def result_page(self):
        allusers = self.fetch_user_list()
        return render_template("index.html", userlist=json.dumps(allusers, indent=2))

    def fetch_user_list(self):
        self.logger.debug(
            "Fetch users from host %s:%d",
            self.config["UNIFI_HOST"],
            self.config["UNIFI_PORT"],
        )
        self.succesfull_fecth_metric.inc()

        ctrl = Controller(
            self.config["UNIFI_HOST"],
            self.config["UNIFI_USERNAME"],
            self.config["UNIFI_PASSWORD"],
            site_id=self.config["UNIFI_SITE"],
            version="UDMP-unifiOS",
            ssl_verify=False,
        )

        try:
            allusers = ctrl.get_users()
        except Exception as e:
            self.fecth_errors_metric.inc()
            raise
        self.logger.debug(allusers)
        self.log_users(allusers)
        return allusers

    def log_users(self, allusers):
        self.logger.debug("Current user list: %d", len(allusers))
        for user in allusers:
            self.logger.debug(
                "%20s | %-30s  %-40s",
                user.get("mac"),
                user.get("hostname"),
                user.get("name"),
            )

    def diff(self, list1, list2):
        return list(set(list1).symmetric_difference(set(list2)))

    def write_list_to_file(self, filename, list):
        with open(filename, "w") as f:
            for i in list:
                f.write(i + "\n")

    def read_list_from_file(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return [line.rstrip("\n") for line in f]
        else:
            return []

    def append_line_to_file(self, filename, line):
        with open(filename, "a+") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    Framework().start(MyApp(), MyConfig(), blocked=True)
