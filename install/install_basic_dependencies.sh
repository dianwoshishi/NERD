#!/bin/sh
# Install all packages needed to run NERD and run all the services

BASEDIR=$(dirname $0)
. $BASEDIR/common.sh

echob "=============== Install basic dependencies ==============="

echob "** Installing basic RPM packages **"
cp_systemctl
yum install -y -q https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum install -y -q git wget gcc vim python36 python36-devel python36-setuptools
yum install -y -q centos-release-scl # needed to get llvm-toolset-7-clang, a dependency of postgresql11-devel


echob "** Installing PostgreSQL **"
if ! yum list installed postgresql11-server >/dev/null 2>&1 ; then
  yum install -y -q https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
  yum install -y -q postgresql11-server postgresql11-devel
fi
cp_systemctl
export PATH="$PATH:/usr/pgsql-11/bin/"

# Initialize database (creates DB files in /var/lib/pgsql/11/data/)
if ! [ -e /var/lib/pgsql/11/data/PG_VERSION ] ; then
  /usr/pgsql-11/bin/postgresql-11-setup initdb
fi

# Non-default DB path:
# mkdir -p /data/pgsql
# chown -R postgres /data/pgsql
# sudo -u postgres /usr/pgsql-11/bin/initdb -D /data/pgsql
# sed -i "s,PGDATA=.*$,PGDATA=/data/pgsql," /lib/systemd/system/postgresql-11.service

# Edit /db/pgsql/pg_hba.conf to trust all local connections
# It allows to use "psql -U user" instead of "sudo -u USER psql"
# and it allows easier connection from web server
sed -i -E '/^local|127\.0\.0\.1\/32|::1\/128/ s/[^ ]+$/trust/' /var/lib/pgsql/11/data/pg_hba.conf
cp_systemctl
# Start PostgreSQL
systemctl enable postgresql-11.service
systemctl restart postgresql-11.service
cp_systemctl

# Note: Installation of Python packages must be after installation of postgresql11-devel, since psycopg2 package is compiled from source and needs it.
echob "** Installing pip **"
easy_install-3.6 --prefix /usr pip
# for some reason, this creates file /usr/bin/pip3.7 instead of pip3.6 (but everything works OK)

# Allow to run python3.6 as python3 (not needed, is created automatically)
# ln -s /usr/bin/python3.6 /usr/bin/python3

echob "** Installing Python packages **"
pip3 install --upgrade pip
pip3 install -q -r $BASEDIR/pip_requirements_nerdd.txt
pip3 install -q -r $BASEDIR/pip_requirements_nerdweb.txt


echob "** Installing MongoDB **"

cp_systemctl
# Add repository
echo '[mongodb-org-5.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/5.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-5.0.asc
' > /etc/yum.repos.d/mongodb-org-5.0.repo
cp_systemctl
yum install -y -q mongodb-org

# ** Set up logrotate **
# Configure Mongod to only reopen file after receiving SIGUSR1
if ! grep '^\s*logRotate: reopen' /etc/mongod.conf ; then
  sed -i '/logAppend: true/a \ \ logRotate: reopen' /etc/mongod.conf
fi
# Configure logrotate
echo '/var/log/mongodb/mongod.log {
    weekly
    missingok
    rotate 8
    compress
    delaycompress
    notifempty
    postrotate
        /usr/bin/pkill -USR1 mongod
    endscript
}
' > /etc/logrotate.d/mongodb
cp_systemctl
echob "** Starting MongoDB **"
# /sbin/chkconfig mongod on
systemctl enable mongod.service
systemctl start mongod.service
cp_systemctl


echob "** Installing Redis **"
yum install -y -q redis
cp_systemctl
echob "** Starting Redis **"
systemctl enable redis.service
systemctl start redis.service
cp_systemctl


echob "** Installing RabbitMQ **"
# We need more recent version than in CentOS7 (>=3.7.0), so install from developer sites

# Install Erlang (dependency)
echo '[rabbitmq_erlang]
name=rabbitmq_erlang
baseurl=https://packagecloud.io/rabbitmq/erlang/el/6/$basearch
repo_gpgcheck=1
gpgcheck=0
enabled=1
gpgkey=https://packagecloud.io/rabbitmq/erlang/gpgkey
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300

[rabbitmq_erlang-source]
name=rabbitmq_erlang-source
baseurl=https://packagecloud.io/rabbitmq/erlang/el/6/SRPMS
repo_gpgcheck=1
gpgcheck=0
enabled=1
gpgkey=https://packagecloud.io/rabbitmq/erlang/gpgkey
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
metadata_expire=300
' > /etc/yum.repos.d/rabbitmq_erlang.repo
cp_systemctl
yum install -y -q erlang

# Install RabbitMQ
if ! yum list installed rabbitmq-server >/dev/null 2>&1 ; then
  yum install -y -q https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.7.15/rabbitmq-server-3.7.15-1.el7.noarch.rpm
  #yum install -y -q https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.9.14/rabbitmq-server-3.9.14-1.el7.noarch.rpm
fi

# For some reason, hostname in Vagrant is often not set to anything meaningful,
# but erlang needs to know it - this helps. 
# Reference: https://stackoverflow.com/questions/45425286/rabbitmq-server-dont-start-unable-to-connect-to-epmd-ubuntu-16-04 
# echo "HOSTNAME=localhost" >/etc/rabbitmq/rabbitmq-env.conf

# Allow guest user to login remotely (allowed only from localhost by default)
# This is necessary for Vagrant, but DON'T DO THIS IN PRODUCTION!
# (rabbitmq.conf is not present after installation, so we just create it)
if [ -d /vagrant/NERDd ] ; then
  echor "It seems we run in Vagrant, allowing RabbitMQ guest user to login remotely."
  echo "loopback_users = none" > /etc/rabbitmq/rabbitmq.conf
fi

# Enable necessary plugins
rabbitmq-plugins enable rabbitmq_management
# rabbitmq-plugins enable rabbitmq_consistent_hash_exchange
cp_systemctl
echob "** Starting RabbitMQ **"
systemctl enable rabbitmq-server
systemctl start rabbitmq-server
cp_systemctl
# Get rabbitmqadmin tool (provided via local API by the management plugin)
if ! [ -f /usr/bin/rabbitmqadmin ] ; then
  wget -q http://localhost:15672/cli/rabbitmqadmin -O /usr/bin/rabbitmqadmin
  chmod +x /usr/bin/rabbitmqadmin
fi

cp_systemctl
echob "** Installing Supervisor **"
pip -q install "supervisor==4.*"
ln -s /usr/local/bin/supervisord /usr/bin/supervisord
ln -s /usr/local/bin/supervisorctl /usr/bin/supervisorctl

cp_systemctl
echob "** All main dependencies installed **"
