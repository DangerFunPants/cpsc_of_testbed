import requests     as req
import json         as json

class OnMonitor:

    def __init__(self, onos_controller_ip, onos_controller_port):
        self._onos_controller_ip        = onos_controller_ip
        self._onos_controller_port      = onos_controller_port
        self._monitor_token             = None
        self._credentials               = ("onos", "rocks")
        self._stop_monitor_response     = None

    def start_monitor(self):
        if self._monitor_token != None:
            raise ValueError("Monitor is already running.")

        on_mon_url = ("http://%s:%d/onos/on-mon/v1/start-monitor" % 
                (self._onos_controller_ip, self._onos_controller_port))
        start_monitor_request = req.post(on_mon_url, auth=self._credentials)
        if start_monitor_request.status_code == 200:
            start_monitor_response = json.loads(start_monitor_request.text)
            self._monitor_token = start_monitor_response["token"]
        else:
            raise ValueError("Failed to start OnMonitor. Status %d, Reason %s." %
                    (start_monitor_request.status_code, start_monitor_request.reason))

    def stop_monitor(self):
        if self._monitor_token == None:
            raise ValueError("Monitor was not running.")

        on_mon_url = ("http://%s:%d/onos/on-mon/v1/stop-monitor?monitor-token=%s" %
                (self._onos_controller_ip, self._onos_controller_port, self._monitor_token))
        stop_monitor_request = req.post(on_mon_url, auth=self._credentials)
        if stop_monitor_request.status_code == 200:
            stop_monitor_response = json.loads(stop_monitor_request.text)
            self._stop_monitor_response = stop_monitor_response
            self._monitor_token = None
        else:
            raise ValueError("Failed to stop OnMonitor. Status %d, Reason %s." % 
                    (stop_monitor_request.status_code, stop_monitor_request.reason))

    def get_monitor_statistics(self):
        if self._stop_monitor_response == None:
            raise ValueError("No results have been collected yet! Did you remember to start/stop the monitor.")
        return [d["netUtilStats"]["utilizationStats"] for d in self._stop_monitor_response]
