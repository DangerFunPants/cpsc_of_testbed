#!/usr/bin/env bash

trials=(seed_5678/prob_mean_1_sigma_1.0/ seed_5678/deter_mean_2.645/ seed_5678/deter_mean_1/)
names=(prob_mean_1_sigma_1.0 deter_mean_2.645 deter_mean_1)

for i in echo $(seq 0 2);
do
    echo "Running trial ${names[$i]}" 
    test_driver.py start ${trials[$i]};
    mkdir /home/ubuntu/cpsc_of_tb/results/${names[$i]};
    cp *.p /home/ubuntu/cpsc_of_tb/results/${names[$i]};
    cp ./name_hints.txt /home/ubuntu/cpsc_of_tb/results/${names[$i]}; 
done
