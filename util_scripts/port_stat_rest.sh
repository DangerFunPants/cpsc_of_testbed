#!/usr/bin/env bash
sw_8=845512722656064
sw_9=1408462676077376
sw_5=1126987699366720

curl -X POST http://10.0.1.1:8080/stats/portdesc/modify -d '{
    "dpid": $sw_8,
    "port_no": 13,
    "config": 1,
    "mask" : 1
    }'
