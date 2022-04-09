# NERD - Network Entity Reputation Database

NERD is a software and a service which acquires, stores and aggregates various data about known malicious network entities (mostly IP addresses) and provides them in a comprehensible way to users.

The main NERD instance runs at [nerd.cesnet.cz](https://nerd.cesnet.cz/).

See the [project wiki](https://github.com/CESNET/NERD/wiki) for more information.

---

_This software was developed within the scope of the Security Research
Programme of the Czech Republic 2015 - 2020 (BV III / 1 VS) granted by
the Ministry of the Interior of the Czech Republic under the project No.
VI20162019029 The Sharing and analysis of security events in the Czech
Republic._

---

## Docker supported

So far, I've now finished getting this project supported by Docker.

there are some changes:

- add Dockerfile to the root

- download `systemctl.py` from https://github.com/gdraheim/docker-systemctl-replacement

- add `cp_systemctl` function in install script `common.sh` and use it multi-place, for copy systemctl.py "After "yum install" and before the next "systemctl" execution."
  
  the reason for that is ref: can not start the service when reboot? gdraheim/docker-systemctl-replacement#137 (comment)
  
  root reason: can not start the service when reboot? gdraheim/docker-systemctl-replacement#137 (comment)，[Not able to use systemd on ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/39169403/not-able-to-use-systemd-on-ubuntu-docker-container)

## install

you can deploy this project into a container simplely.

```
## on your host
docker build -t nerd -f ./Dockerfile .
docker run -it -d --privileged  --name nerd nerd /usr/bin/systemctl
docker exec -it nerd /bin/bash
## in the container, /tmp/nerd_install/
./install/install_centos7.sh 

## now you can commit your container to a image. 
docker commit -a "dianwoshishi@sina.com" nerd nerd_v1.0

## you can use the nerd_v1.0 every where, just like this 
docker run -itd -p 80:80 -p 9001:9001 nerd_v1.0
```

## errors process

if errors occur, check your these:

### services

```shell
#list the running services, make sure they are all running state.

$ docker exec -it nerd_v1.0 systemctl list-units --state=running
crond.service
httpd.service
mongod.service
named.service
nerd-supervisor.service
postgresql-11.service
rabbitmq-server.service
redis.servic
```

### log

location in `/var/log/nerd/*`
you can simplely found them by access http://localhost:9001 in your container.

### Finally

Also, issues are welcomed!