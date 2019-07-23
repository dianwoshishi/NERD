#!/bin/sh

BASEDIR=$(dirname $0)
. $BASEDIR/common.sh

echob "=============== Configure MongoDB ==============="

echob "** Configuring MongoDB **"

# Set up MongoDB for NERD (create indexes)
mongo nerd $BASEDIR/mongo_prepare_db.js
