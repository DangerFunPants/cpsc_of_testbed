#!/usr/bin/env bash

trials=(prob_mean_1_sigma_1.0 deter_mean_2.645 deter_mean_1)
names=(prob_mean_1_sigma_1.0 deter_mean_2.645 deter_mean_1)
seed_nos=(1234 4065 5678 9812)

time=900
for j in $(seq 0 3);
do
    current_seed=${seed_nos[$j]}
    for i in $(seq 0 2);
    do
        echo "Running trial ${names[$i]}" 
        let s=12500000;
        test_driver.py start var_rate ${trials[$i]} $current_seed --time $time --mu 12500000 --sigma $s;
        mkdir /home/ubuntu/cpsc_of_tb/results/${seed_nos[$j]}_${names[$i]};
        cp *.p /home/ubuntu/cpsc_of_tb/results/${seed_nos[$j]}_${names[$i]};
        cp ./name_hints.txt /home/ubuntu/cpsc_of_tb/results/${seed_nos[$j]}_${names[$i]}; 
        ./get_files.sh
    done
done
