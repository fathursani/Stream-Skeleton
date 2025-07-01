import json
import re
from datetime import datetime
from confluent_kafka import Consumer
import psycopg2

# Kafka and PostgreSQL Configs
KAFKA_CONF = {
    'bootstrap.servers': 'localhost:19092',
    'group.id': 'toll_consumer_group',
    'auto.offset.reset': 'earliest'
}
TOPIC = 'mariadb.source_db.toll_transactions'

PG_CONF = {
    'host': 'localhost',
    'port': 5432,
    'user': 'user',
    'password': 'password',
    'dbname': 'source_db'
}

# Utils
def sanitize_column(name):
    return re.sub(r'\W|^(?=\d)', '_', name.lower())

def convert_epoch_to_datetime(epoch_ms):
    """
    Converts epoch time in milliseconds to a datetime string in 'YYYY-MM-DD HH:MM:SS.sss' format.
    """
    if isinstance(epoch_ms, str):
        try:
            epoch_ms = int(epoch_ms)
        except ValueError:
            return None
    return datetime.fromtimestamp(epoch_ms / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def create_dim_table(conn, table, columns):
    defs = ",\n  ".join(f"{sanitize_column(c)} TEXT" for c in columns)
    sql = f"CREATE TABLE IF NOT EXISTS {table} (id SERIAL PRIMARY KEY, {defs});"
    with conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
        print("DONE CREATE DIM TABLE")

def get_or_create_dim_id(conn, table, keys, data):
    cols = [sanitize_column(k) for k in keys]
    values = [data.get(k) for k in keys]
    conds = " AND ".join(f"{col} = %s" for col in cols)

    with conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {table} WHERE {conds} LIMIT 1;", values)
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))}) RETURNING id;",
            values
        )
        conn.commit()
        print("DONE INSERTING DIM TABLE")
        return cur.fetchone()[0]

def create_fact_table(conn):
    '''
    ADJUST THIS TABLE
    '''
    sql = """
    CREATE TABLE IF NOT EXISTS fact_toll_transactions (
        transaction_id TEXT PRIMARY KEY,
        tgl_transaksi TIMESTAMP,
        periode VARCHAR(10),
        tarif INT,
        saldo INT,
        no_kartu VARCHAR(20),
        no_resi VARCHAR(20),
        shift VARCHAR(10),
        flag_id CHAR(1),
        dim_cabang_id INT,
        dim_gerbang_id INT,
        dim_bank_id INT,
        dim_vehicle_id INT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()

# Main Kafka Consumer
def main():
    consumer = Consumer(KAFKA_CONF)
    consumer.subscribe([TOPIC])
    pg_conn = psycopg2.connect(**PG_CONF)

    # Setup tables
    create_fact_table(pg_conn)
    create_dim_table(pg_conn, "dim_cabang", ["kode_cabang", "nama_cabang"])
    create_dim_table(pg_conn, "dim_gerbang", ["gerbang", "nama_gerbang", "kode_gerbang_asal", "nama_gerbang_asal"])
    create_dim_table(pg_conn, "dim_bank", ["bank"])
    create_dim_table(pg_conn, "dim_vehicle", ["golongan"])

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None or msg.error():
                break
                # continue

            try:
                raw = json.loads(msg.value().decode('utf-8'))
            except Exception as e:
                print(f"❌ Invalid JSON: {e}")
                break
                # continue

            if raw.get("op") not in ["c", "u", "r"]:
                print('BUKAN R atau C atau U')
                break
                # continue

            payload = raw.get("after")
            if not payload:
                print('AFTER KOSONG')
                break
                # continue

            try:
                # Get dimension keys
                '''
                ADJUST THE COLUMN BELOW WITH THE AVAILABLE COLUMN
                '''
                print('START EXECUTION')
                dim_cabang_id = get_or_create_dim_id(pg_conn, "dim_cabang", ["kode_cabang", "nama_cabang"], payload)
                dim_gerbang_id = get_or_create_dim_id(pg_conn, "dim_gerbang", ["gerbang", "nama_gerbang", "kode_gerbang_asal", "nama_gerbang_asal"], payload)
                dim_bank_id = get_or_create_dim_id(pg_conn, "dim_bank", ["bank"], payload)
                dim_vehicle_id = get_or_create_dim_id(pg_conn, "dim_vehicle", ["golongan"], payload)

                # Insert fact record
                '''
                ADJUST THE COLUMN NAME BELOW
                '''
                payload['tgl_transaksi'] = convert_epoch_to_datetime(payload['tgl_transaksi'])
                payload['created_at'] = convert_epoch_to_datetime(payload['created_at'])
                payload['updated_at'] = convert_epoch_to_datetime(payload['updated_at'])

                with pg_conn.cursor() as cur:
                    cur.execute("""
                    INSERT INTO fact_toll_transactions (
                        transaction_id, tgl_transaksi, periode, tarif, saldo, no_kartu,
                        no_resi, shift, flag_id, dim_cabang_id, dim_gerbang_id, dim_bank_id,
                        dim_vehicle_id, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO NOTHING;
                    """, (
                        payload.get("no_resi"),
                        payload.get("tgl_transaksi"),
                        payload.get("periode"),
                        payload.get("tarif"),
                        payload.get("saldo"),
                        payload.get("no_kartu"),
                        payload.get("no_resi"),
                        payload.get("shift"),
                        payload.get("flag_id"),
                        dim_cabang_id,
                        dim_gerbang_id,
                        dim_bank_id,
                        dim_vehicle_id,
                        payload.get("created_at"),
                        payload.get("updated_at")
                    ))
                    pg_conn.commit()
                print(f"✅ Inserted transaction {payload.get('no_resi')}")
            except Exception as e:
                print(f"🔥 Error during insert: {e}")
                break

    except KeyboardInterrupt:
        print("🛑 Stopped by user")
    finally:
        # consumer.close()
        pg_conn.close()

if __name__ == "__main__":
    main()