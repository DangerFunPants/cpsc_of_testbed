#!/usr/bin/env bash

trials=(prob_mean_1_sigma_1.0 deter_mean_2.645 deter_mean_1)
names=(prob_mean_1_sigma_1.0 deter_mean_2.645 deter_mean_1)

time=900

for i in $(seq 0 2);
do
    echo "Running trial ${names[$i]}" 
    let s=12500000*12500000;
    # let s=1
    test_driver.py start var_rate ${trials[$i]} 4065 --time $time --mu 12500000 --sigma $s;
    mkdir /home/ubuntu/cpsc_of_tb/results/${names[$i]};
    cp *.p /home/ubuntu/cpsc_of_tb/results/${names[$i]};
    cp ./name_hints.txt /home/ubuntu/cpsc_of_tb/results/${names[$i]}; 
    ./get_files.sh
done
