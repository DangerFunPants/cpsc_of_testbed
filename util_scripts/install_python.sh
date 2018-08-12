#!/usr/bin/env bash
dig_comm="dig @::1 http://ftb.debian.org.; dig @::1 ftp.ca.debian.org. &>/dev/null;"
# comm_str="sudo apt -y update; sudo apt -y upgrade --fix-broken; sudo apt -y install python-pip; sudo apt -y install python-enum34; sudo apt -y install python-scipy;"

comm_str="sudo update-rc.d -f isc-dhcp-server remove; sudo reboot now"
# comm_str="sshpass -V"
comms="$dig_comm$comm_str"
# comms="pip --version"

sshIps=$(dig @192.168.0.2 management.cpsc. axfr | egrep "host[0-9]{1,2}.*A" | awk '{print $5}')
echo $sshIps
for ip in $sshIps;
do
    echo "Connecting to $ip"
    sshpass -pcpsc ssh -t alexj@$ip $comm_str;
done


