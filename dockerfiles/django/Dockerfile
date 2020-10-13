FROM ubuntu:16.04
MAINTAINER dreamslab

RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:ubuntugis/ppa
RUN apt-get update
RUN apt-get install -y python3-pip python3-dev software-properties-common \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

FROM python:3.7
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip3.7 install -r requirements.txt
RUN apt-get update
RUN apt-get install -y dnsutils vim
RUN apt-get install -y libgdal-dev gdal-bin python3-gdal libmagickwand-dev imagemagick inkscape postgresql-client-common postgresql-client
RUN pip install --upgrade pip
RUN pip3.7 install --upgrade pip
RUN export CPLUS_INCLUDE_PATH=/usr/include/gdal >> /root/.bashrc
RUN export C_INCLUDE_PATH=/usr/include/gdal >> /root/.bashrc
RUN pip3.7 install GDAL==2.4.0 django-adminplus django-extensions==3.0.2 cairosvg requests matplotlib descartes ipython scipy shapely geojson bs4
RUN pip3.7 install -U https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow_cpu-2.1.0-cp37-cp37m-manylinux2010_x86_64.whl
ENV DJANGO_SETTINGS_MODULE agdss.settings.common
