import os
import logging
from datetime import datetime

from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, String, Float, TIMESTAMP, Boolean
from sqlalchemy.orm import sessionmaker

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_USER = os.getenv('POSTGRES_USER', 'your-username')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'your-password')
DB_NAME = os.getenv('POSTGRES_DB', 'your-dbname')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Создание подключения
# database = Database(DATABASE_URL)
# metadata = MetaData()
#
# metrics_table = create_metrics_table(metadata)
# orders_table = create_orders_table(metadata)
# orders_table_bt = create_orders_table(metadata, 'orders-backtest')
#
# engine = create_engine(DATABASE_URL)
# metadata.create_all(engine)

class TimescaleDBClient:
    def __init__(self, database_url=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"):
        self.database_url = database_url
        self.engine = create_engine(self.database_url)
        self.metadata = MetaData()
        self.Session = sessionmaker(bind=self.engine)
        self.session = None
        self.metrics_table = self.create_metrics_table()
        self.orders_table = self.create_orders_table()

    def connect(self):
        self.metadata.create_all(self.engine)
        self.session = self.Session()
        logger.info("Connected to TimescaleDB")

    def close(self):
        if self.session:
            self.session.close()
        logger.info("Connection to TimescaleDB closed")

    def create_metrics_table(self):
        return Table('metrics', self.metadata,
                     Column('time', TIMESTAMP, primary_key=True),
                     Column('measurement', String),
                     Column('tags', String),
                     Column('fields', String))

    def create_orders_table(self):
        return Table('orders', self.metadata,
                     Column('order_id', String, primary_key=True),
                     Column('time', TIMESTAMP),
                     Column('pair', String),
                     Column('side', String),
                     Column('price', Float),
                     Column('volume', Float),
                     Column('status', String),
                     Column('filled', Boolean))

    def create(self, table, data):
        ins = table.insert().values(**data)
        self.session.execute(ins)
        self.session.commit()
        logger.info(f"Data inserted into {table.name}: {data}")

    def read(self, table, conditions=None):
        query = table.select()
        if conditions:
            for col, val in conditions.items():
                query = query.where(getattr(table.c, col) == val)
        result = self.session.execute(query)
        return result.fetchall()

    def update(self, table, data, conditions):
        upd = table.update().values(**data)
        for col, val in conditions.items():
            upd = upd.where(getattr(table.c, col) == val)
        self.session.execute(upd)
        self.session.commit()
        logger.info(f"Data in {table.name} updated: {data} where {conditions}")

    def delete(self, table, conditions):
        del_stmt = table.delete()
        for col, val in conditions.items():
            del_stmt = del_stmt.where(getattr(table.c, col) == val)
        self.session.execute(del_stmt)
        self.session.commit()
        logger.info(f"Data deleted from {table.name} where {conditions}")


# Пример использования
if __name__ == '__main__':
    client = TimescaleDBClient(DATABASE_URL)
    client.connect()

    # Пример CRUD операций
    client.create(client.metrics_table,
                  {"time": datetime.utcnow(), "measurement": "test", "tags": "tag1", "fields": "field1"})
    records = client.read(client.metrics_table)
    print(records)
    client.update(client.metrics_table, {"tags": "tag2"}, {"measurement": "test"})
    # client.delete(client.metrics_table, {"measurement": "test"})

    client.close()
