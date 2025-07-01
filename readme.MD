# How to do
1. Copy all the file
2. Make sure there is docker in the local
3. Make sure you alrady install python
4. run docker compose up -d
5. Create connection using and adjust hostname, user, password, database.include.list, table.include.list:
    ```
    curl --location 'http://localhost:8083/connectors' \
    --header 'Content-Type: application/json' \ --data '{
    "name": "mariadb-connector",
    "config": {
        "connector.class": "io.debezium.connector.mysql.MySqlConnector",
        "database.hostname": "mariadb",
        "database.port": "3306",
        "database.user": "root",
        "database.password": "root",
        "database.server.id": "223344",
        "database.server.name": "source_db_server",
        "database.include.list": "source_db",
        "table.include.list": "source_db.toll_transactions",
        "topic.prefix": "mariadb",
        "database.history.kafka.bootstrap.servers": "redpanda:19092",
        "database.history.kafka.topic": "mariadb.history",
        "schema.history.internal.kafka.bootstrap.servers": "redpanda:9092",
        "schema.history.internal.kafka.topic": "mariadb.history",
        "snapshot.mode": "initial",
        "snapshot.locking.mode": "none",
        "include.schema.changes": "false",
        "database.connectionTimeZone": "Asia/Jakarta",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false",
        "decimal.handling.mode": "double"
    }
    }
6. Check in https://localhost:8080 if there is the topic
7. run consumer.py