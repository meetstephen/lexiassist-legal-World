def esc(value):
    return str(value).replace('"', '\"')

def new_id():
    import uuid
    return str(uuid.uuid4())

def hash_password(password):
    from hashlib import sha256
    return sha256(password.encode('utf-8')).hexdigest()


def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)


def estimate_tokens(text):
    return len(text.split())


def days_until(target_date):
    from datetime import datetime
    target = datetime.strptime(target_date, '%Y-%m-%d')
    return (target - datetime.utcnow()).days


def fmt_date(date):
    return date.strftime('%Y-%m-%d')


def relative_date(date):
    # Placeholder for relative date formatting
    return date.strftime('%Y-%m-%d')


def fmt_currency(amount):
    return f'${amount:,.2f}'

def db_count(collection):
    # Placeholder for database count
    return len(collection)

def db_sum(collection, field):
    return sum(item[field] for item in collection)

def db_fetch_all(collection):
    return collection

def db_fetch_where(collection, filter):
    return [item for item in collection if all(item[k] == v for k, v in filter.items())]

def db_insert(collection, item):
    collection.append(item)


def db_update(collection, item_id, updated_item):
    for index, item in enumerate(collection):
        if item['id'] == item_id:
            collection[index] = updated_item


def db_delete(collection, item_id):
    return [item for item in collection if item['id'] != item_id]

def seed_defaults(db):
    defaults = [
        {'name': 'default_item_1'},
        {'name': 'default_item_2'},
    ]
    for item in defaults:
        db_insert(db, item)