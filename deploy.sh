#!/bin/sh

docker-compose down
docker-compose up -d

docker exec -it postgres psql -U ${POSTGRESQL_USER} -d ${POSTGRESQL_DB} -a -f /data/schemas.sql
docker exec -it postgres psql -U ${POSTGRESQL_USER} -d ${POSTGRESQL_DB} -f /data/relevant_locations_data.sql
docker exec -it postgres psql -U ${POSTGRESQL_USER} -d ${POSTGRESQL_DB} -f /data/country_code_data.sql
docker exec -it postgres psql -U ${POSTGRESQL_USER} -d ${POSTGRESQL_DB} -f /data/location_country_codes.data.sql
