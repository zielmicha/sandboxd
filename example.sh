#!/bin/bash
ls /
ls -l /opt
ls -l /data

sudo # should return Operation not permitted

echo "hey!"
for i in {0..9}; do
    echo "work $i"
    sleep 1
done
