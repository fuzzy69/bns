#!/bin/bash

chmod 600 /etc/mogo.keyfile
mongod --config /etc/mongod.conf
