# convert a sql row into a dictionary

from sqlalchemy import inspect

# this is the only important part
# everything else was just to create a test case
# handles the special case of one row using sqlalchemy orm
# where the column names match class attributes 

def dict_from(obj):
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}
