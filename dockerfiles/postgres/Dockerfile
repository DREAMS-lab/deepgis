FROM postgres:12
ADD init.sql /docker-entrypoint-initdb.d/
RUN apt-get update
RUN apt-get install postgresql-12-postgis-3 -y

