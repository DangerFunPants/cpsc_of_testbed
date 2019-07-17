ip_list=$(dig @10.0.0.1 -t axfr hosts.sdn. | egrep "host[0-9]{1,2}.*A" | awk '{print $5}')
echo $ip_list
for ip in $ip_list
do 
    echo "Host $ip with command $1";
    sshpass -pcpsc ssh alexj@$ip "$1";
done
