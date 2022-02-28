FROM centos/systemd
WORKDIR /tmp/nerd_install
USER root
COPY . .
COPY systemctl.py /usr/bin/systemctl
RUN chmod a+x /usr/bin/systemctl && chmod a+x /tmp/nerd_install/install/install_centos7.sh 
CMD /usr/bin/systemctl

## on your host
# docker build -t nerd -f ./Dockerfile .
# docker run -it -d --privileged  --name nerd nerd /usr/bin/systemctl
# docker exec -it nerd /bin/bash
## in the container
# ./install/install_centos7.sh 