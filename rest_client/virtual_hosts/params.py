
import urllib.parse     as url

iface_name = "ens192"

password = "lab2019lab!"

of_controller_ip = "10.0.0.8"

of_controller_port = 8181

onos_url = url.urlparse("http://%s:%d/onos/" % (of_controller_ip, of_controller_port))

