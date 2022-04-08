#./install/install_centos7.sh:
#mv /nerd /nerd_old
rm -rf /nerd
mkdir /nerd
ln -s /tmp/nerd_install/common /nerd/common
ln -s /tmp/nerd_install/NERDd /nerd/NERDd
ln -s /tmp/nerd_install/NERDweb /nerd/NERDweb
ln -s /tmp/nerd_install/scripts /nerd/scripts

#mv /etc/nerd /etc/nerd_old
rm -rf /etc/nerd
ln -s /tmp/nerd_install/etc /etc/nerd

#./install/configure_cron.sh
mv /etc/cron.d/nerd /etc/cron.d/nerd_old
ln -s /tmp/nerd_install/install/cron/nerd /etc/cron.d/nerd
#./install/install_configure_munin.sh
mv /etc/httpd/conf.d/munin.conf /etc/httpd/conf.d/munin.conf_old
ln -s /tmp/nerd_install/install/httpd/munin.conf /etc/httpd/conf.d/munin.conf
#./install/configure_supervisor.sh:
mv /etc/systemd/system/nerd-supervisor.service /etc/systemd/system/nerd-supervisor.service_old
ln -s /tmp/nerd_install/install/nerd-supervisor.service /etc/systemd/system/nerd-supervisor.service
ln -s /tmp/nerd_install/install/supervisord.conf.d /etc/nerd/supervisord.conf.d
ln -s /tmp/nerd_install/install/supervisord.conf /etc/nerd/supervisord.conf
#./install/configure_apache.sh:
mv /etc/httpd/conf.d/nerd.conf /etc/httpd/conf.d/nerd.conf_old
ln -s /tmp/nerd_install/install/httpd/nerd.conf /etc/httpd/conf.d/nerd.conf
# ln -s /tmp/nerd_install/install/httpd/nerd-debug.conf /etc/httpd/conf.d/nerd.conf
