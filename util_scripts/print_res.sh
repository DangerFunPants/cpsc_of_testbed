#!/usr/bin/env bash

rx_path=~/packet_counts/rx/$1/
tx_path=~/packet_counts/tx/$1/

echo "Results for $rx_path and $tx_path"
echo "--------------------------"

for f in $(find $rx_path -type f -name "*.p"); 
do 
    ~/print_pkl.py $f;
done

for f in $(find $tx_path -type f -name "*.txt");
do
    echo -n "$(basename $f)     ||      ";
    cat $f;
done
