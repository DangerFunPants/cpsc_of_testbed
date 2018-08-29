#!/usr/bin/env bash

trials=(prob_mean_1_sigma_1.0/ deter_mean_2.645/ deter_mean_1/)
# trials=(seed_5678/ seed_5678/deter_mean_2.645/ seed_5678/deter_mean_1/)
names=(prob_mean_1_sigma_1.0 deter_mean_2.645 deter_mean_1)
sshIps=$(dig @192.168.0.2 management.cpsc. axfr | egrep "host[0-9]{1,2].*A" | awk '{print $5}')

for i in $(seq 0 2);
do
    echo "Running trial ${names[$i]}" 
    test_driver.py start_ne ${trials[$i]};
    mkdir /home/ubuntu/cpsc_of_tb/results/${names[$i]};
    cp *.p /home/ubuntu/cpsc_of_tb/results/${names[$i]};
    cp ./name_hints.txt /home/ubuntu/cpsc_of_tb/results/${names[$i]}; 
    trialName=$(cat ./name_hints.txt)
    # for ip in $sshIps; 
    # do 
    #     sshpass -pcpsc scp alexj@$ip:~/packet_counts/receiver_*.p /home/ubuntu/packet_counts/rx/$trialName; 
    # done
    # for ip in $sshIps;
    # do
    #     sshpass -pcpsc scp alexj@$ip:~/packet_counts/sender_*.p /home/ubuntu/packet_counts/tx/$trialName;
    # done
    ./get_files.sh
done
