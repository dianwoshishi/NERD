#!/bin/bash

# Download asdb database to /data/asdb.csv
#
# Usage:
#   ./donwload_asdb.sh 
#
#

user=$(whoami)
if [[ "$user" != "nerd" && "$user" != "root" ]]; then
  echo "Run as user 'nerd' or root." >&2
  exit 2
fi

# exit when any command fails
set -e

echo "Downloading asdb database to /data/asdb.csv "
# Download archive using the licence key
cd /data/
wget -q --no-check-certificate "https://asdb.stanford.edu/data/ases.csv" -O asdb.csv
# The archive contains a directory named by creation date, containing the DB
# and some txt file - extract just the DB file (*/GeoLite2-City.mmdb) to
# current dir
if [[ "$user" == "root" ]]; then
  echo "Setting ownership to 'nerd' account"
  chown -R nerd:nerd /data
fi

echo "Done"
