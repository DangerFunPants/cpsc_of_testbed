for f in $(find . -maxdepth 1 -type d);
do
    for v in $(find ./$f -maxdepth 1 -type d | egrep "VN_Req_[0-9]{4}");
    do
        seed=${v: -4};
        echo $seed;
        echo $f/seed_$seed/rate_files;
        mkdir $f/seed_$seed/rate_files/;
        mv $f/$(basename $v)/* $f/seed_$seed/rate_files/;
    done
done
