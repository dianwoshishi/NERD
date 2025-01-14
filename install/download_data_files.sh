#!/bin/sh

BASEDIR=$(dirname $0)
. $BASEDIR/common.sh

echob "=============== Download data files ==============="

# Perform everything as "nerd" user instead of root
cd /
sudo -u nerd sh <<EOF
. $BASEDIR/common.sh
umask 0002

echob "** Copying CAIDA AS-type mapping file **"
# Copy caida file (if present)
if ! [ -f /data/caida-as2types.txt ]; then
  # TODO: the data seem to be updated every month, download the latest one automatically (and write an update script)
  wget -q https://publicdata.caida.org/datasets/as-classification_restricted/20210401.as2types.txt.gz -O /data/caida-as2types.txt.gz
  gunzip -f /data/caida-as2types.txt.gz
fi

echob "** Copying/downloading whois data **"

if ! [ -f /data/nerd-whois-asn.csv -a -f /data/nerd-whois-ipv4.csv ]; then
    echo "Downloading and processing whois data from RIRs"
    cd /data/
    python3 /nerd/scripts/get_iana_assignment_files.py
    cd -
fi

if ! [ -f /data/asdb.csv]; then
    echo "Downloading and processing asdb data"
    cd /data/
    wget -q --no-check-certificate "https://asdb.stanford.edu/data/ases.csv" -O asdb.csv
    cd -
fi
if ! [ -f /data/cloudips.csv]; then
    echo "Downloading and processing cloudips from Dshield"
    cd /data/
    wget -q --no-check-certificate "://asdb.stanford.edu/data/ases.cs://isc.sans.edu/api/cloudips\?csv" -O cloudips.csv
    cd -
fi
EOF
