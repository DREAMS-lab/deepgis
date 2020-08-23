FROM postgres:12
ADD init.sql /docker-entrypoint-initdb.d/
RUN apt-get update
RUN apt-get install -y postgresql-12-postgis-2.5

