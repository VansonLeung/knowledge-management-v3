docker run \
--name neo4j-apoc \
--env=NEO4JLABS_PLUGINS=["apoc"] \
--env=NEO4J_AUTH=neo4j/password \
--env=NEO4J_apoc_export_file_enabled=true \
--env=NEO4J_apoc_import_file_enabled=true \
--env=NEO4J_apoc_import_file_use__neo4j__config=true \
--env=NEO4J_EDITION=community --env=NEO4J_HOME=/var/lib/neo4j \
--env=LANG=C.UTF-8 \
-p 7474:7474 -p 7687:7687 --restart=no --runtime=runc -d \
neo4j:latest
