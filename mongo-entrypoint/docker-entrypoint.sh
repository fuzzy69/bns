#!/usr/bin/env bash

echo "Creating mongo users..."
# chmod 600 /etc/mongo.keyfile
# chown 999 /etc/mongo.keyfile
# mongo admin --host localhost -u USER_PREVIOUSLY_DEFINED -p PASS_YOU_PREVIOUSLY_DEFINED --eval "db.createUser({user: 'ANOTHER_USER', pwd: 'PASS', roles: [{role: 'readWrite', db: 'xxx'}]}); db.createUser({user: 'admin', pwd: 'PASS', roles: [{role: 'userAdminAnyDatabase', db: 'admin'}]});"
# mongodb mongo admin --eval "db.createUser({user: '$MONGO_ROOT_USER', pwd: '$MONGO_ROOT_PASSWORD', roles:[{ role: 'root', db: 'admin' }]});"
# mongo admin --eval "db.createUser({user: 'bns', pwd: 'bns', roles:[{ role: 'root', db: 'admin' }]});"
mongo admin --eval "if(db.system.users.find({user:'$MONGO_ROOT_USERNAME'}).count() == 0){db.createUser({user: '$MONGO_ROOT_USERNAME', pwd: '$MONGO_ROOT_PASSWORD', roles:[{ role: 'root', db: 'admin' }]});}"
# mongo admin -u $MONGO_ROOT_USERNAME -p $MONGO_ROOT_PASSWORD --eval "if(db.system.users.find({user:'$MONGO_ROOT_USERNAME'}).count() == 0){db.createUser({user: '$MONGO_ROOT_USERNAME', pwd: '$MONGO_ROOT_PASSWORD', roles:[{ role: 'root', db: 'admin' }]});}"
# if [[ $(mongo admin --eval "db.system.users.find({user:'$MONGO_ROOT_USERNAME'}).count()") = *0* ]]; then
# if mongo admin --eval "db.system.users.find({user:'$MONGO_ROOT_USERNAME'}).count()" | grep -q 0; then
#   echo "Creating Mongo users ..."
#   # mongo admin --eval "db.createUser({user: '$MONGO_ROOT_USERNAME', pwd: '$MONGO_ROOT_PASSWORD', roles:[{ role: 'root', db: 'admin' }]});"
#   echo "Mongo users created."
# fi

# mongo admin --eval <<EOF
# if(db.system.users.find({user:'$MONGO_ROOT_USERNAME'}).count() > 0) {
#     print("Ok");
# }
# EOF