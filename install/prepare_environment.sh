#!/bin/sh
# Creates a system user and various directories

BASEDIR=$(dirname $0)
. $BASEDIR/common.sh

echob "=============== Prepare environment =============="

echob "** Creating user 'nerd' **"

groupadd nerd
useradd --system --home-dir /nerd --shell /sbin/nologin -g nerd nerd


echob "** Creating NERD directories and setting up permissions **"
# Note: "chown" and "chown" use -R flag for a case there already is something 
# in the directories from a previous installation.

## Code base (executables, scripts, etc.)
#mkdir -p /nerd
#chown -R nerd:nerd /nerd/
#chmod -R 775 /nerd

## Configuration directory
#mkdir -p /etc/nerd
#chown -R nerd:nerd /etc/nerd/
#chmod -R 775 /etc/nerd

# Log directory
mkdir -p /var/log/nerd
chown -R nerd:nerd /var/log/nerd/
chmod -R 775 /var/log/nerd

# Run directory - not needed, is created automatically by systemd thanks to RuntimeDirectory in nerd-supervisor.service
#mkdir -p /var/run/nerd
#chown -R nerd:nerd /var/run/nerd/
#chmod -R 775 /var/run/nerd

# Data directory
mkdir -p /data
chown -R nerd:nerd /data/
chmod -R 775 /data

# local_bl plugin stores data into /data/local_bl  # TODO: should modules be handled in the main installation script?
mkdir -p /data/local_bl
chown -R nerd:nerd /data/local_bl/
chmod -R 775 /data/local_bl

# directory to where blacklists are rsync'ed
mkdir -p /data/blacklists
chown -R nerd:nerd /data/blacklists/
chmod -R 775 /data/blacklists

# directory for precomputed IP lists users can download
mkdir -p /data/web_data
chown -R nerd:nerd /data/web_data
chmod -R 775 /data/web_data

