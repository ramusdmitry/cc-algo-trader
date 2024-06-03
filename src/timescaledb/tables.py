from sqlalchemy import Table, Column, TIMESTAMP, String, Float, Boolean


def create_metrics_table(metadata, name='metrics'):
    return Table(name, metadata,
                 Column('time', TIMESTAMP, primary_key=True),
                 Column('measurement', String),
                 Column('tags', String),
                 Column('fields', String)
                 )


def create_orders_table(metadata, name='orders'):
    return Table(name, metadata,
                 Column('order_id', String, primary_key=True),
                 Column('time', TIMESTAMP),
                 Column('pair', String),
                 Column('side', String),
                 Column('price', Float),
                 Column('volume', Float),
                 Column('status', String),
                 Column('filled', Boolean)
                 )
