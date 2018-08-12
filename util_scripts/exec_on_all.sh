for ip in $(dig @192.168.0.2 management.cpsc. axfr | egrep "host[0-9]{1,2}.*A" | awk '{print $5}'); 
do 
    echo "Host $ip with command $1";
    sshpass -pcpsc ssh alexj@$ip "$1"; 
done
