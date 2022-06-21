from banal import ensure_list
from memorious.operations.db import db


def _get_tablename(context):
    return context.params.get("table", context.crawler.name)


def upsert_many(context, data):
    data_key = context.params.get("data", "rows")
    if data_key in data:
        rows = ensure_list(data.get(data_key))
        fields = ensure_list(context.params.get("fields"))
        for row in rows:
            if fields is not None:
                row = {k: v for k, v in row.items() if k in fields}
            db(context, row)
        if context.params.get("drop_data", True):
            del data[data_key]
    context.emit(data=data, optional=True)


def insert_many(context, data):
    data_key = context.params.get("data", "rows")
    if data_key in data:
        rows = ensure_list(data.get(data_key))
        unique = ensure_list(context.params.get("unique"))
        with context.datastore as tx:
            table = tx[_get_tablename(context)]
            if context.params.get("overwrite", False):
                table.delete()
            table.insert_many(rows, unique)
        if context.params.get("drop_data", True):
            del data[data_key]
    context.emit(data=data, optional=True)


def query_db(context, data):
    # attempt to replace the query parameters with data dict
    query = context.params.get("query", "")
    query = query.format(**data)
    res = context.datastore.query(query)
    for row in res:
        context.emit(data=row)
