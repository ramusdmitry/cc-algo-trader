import os
import logging
from datetime import datetime

from databases import Database
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import text
from tables import create_orders_table, create_metrics_table

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv('POSTGRES_USER', 'your-username')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'your-password')
DB_NAME = os.getenv('POSTGRES_DB', 'your-dbname')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

database = Database(DATABASE_URL)
metadata = MetaData()

metrics_table = create_metrics_table(metadata)
orders_table = create_orders_table(metadata)
orders_table_bt = create_orders_table(metadata, 'orders-backtest')

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)


async def connect():
    await database.connect()


async def disconnect():
    await database.disconnect()


async def write_data(measurement, tags, fields, table: Table = metrics_table):
    query = table.insert().values(
        time=datetime.utcnow(),
        measurement=measurement,
        tags=str(tags),
        fields=str(fields)
    )
    await database.execute(query)
    logger.info(f"Data written to database: {measurement}, {tags}, {fields}")


async def write_order(order_id, pair, side, price, volume, status, filled, table: Table = orders_table):
    query = table.insert().values(
        order_id=order_id,
        time=datetime.utcnow(),
        pair=pair,
        side=side,
        price=price,
        volume=volume,
        status=status,
        filled=filled
    )
    await database.execute(query)
    logger.info(f"Order written to database: {order_id}, {pair}, {side}, {price}, {volume}, {status}, {filled}")


async def query_data(query):
    rows = await database.fetch_all(query)
    logger.info(f"Query executed: {query}")
    return rows


async def delete_data(start, stop, measurement, table: Table = metrics_table):
    query = table.delete().where(
        text(f"time >= '{start}' AND time <= '{stop}' AND measurement = '{measurement}'")
    )
    await database.execute(query)
    logger.info(f"Data deleted from database: {measurement} from {start} to {stop}")


async def select_all(table: Table = metrics_table):
    query = table.select()
    return await database.fetch_all(query)


# Пример использования
async def main():
    await connect()

    await write_data('trade_results', {'strategy': 'SAR', 'pair': 'PAIR'}, {'profit': 150, 'volume': 123})
    print(await select_all())

    await disconnect()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
