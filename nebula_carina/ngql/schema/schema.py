from typing import Optional

from nebula_carina.ngql.connection.connection import run_ngql
from nebula_carina.ngql.schema.data_types import string_to_data_type
from nebula_carina.ngql.statements.schema import Alter, Index, Ttl, SchemaType, SchemaField
from nebula_carina.utils.utils import read_str


def show_schemas(schema: SchemaType) -> list[str]:
    return [i.as_string() for i in run_ngql(f'SHOW {schema.value}S;').column_values('Name')]


def show_tags() -> list[str]:
    return show_schemas(SchemaType.TAG)


def show_edges() -> list[str]:
    return show_schemas(SchemaType.EDGE)


def describe_schema(schema: SchemaType, schema_name: str) -> list[SchemaField]:
    tag_info = run_ngql(f'DESCRIBE {schema.value} {schema_name};')
    keys = tag_info.keys()
    fields = []
    for row in tag_info.rows():
        dic = {
            keys[i]: read_str(v.value)
            for i, v in enumerate(row.values)
        }
        data_type = string_to_data_type(dic['Type'])
        fields.append(SchemaField(
            dic['Field'], data_type, nullable=dic['Null'] == 'YES',
            default=data_type.ttype2python_type(dic['Default']), comment=dic['Comment']
        ))
    return fields


def describe_tag(tag_name: str) -> list[SchemaField]:
    return describe_schema(SchemaType.TAG, tag_name)


def describe_edge(edge_name: str) -> list[SchemaField]:
    return describe_schema(SchemaType.EDGE, edge_name)


def create_schema_ngql(
        schema: SchemaType,
        schema_name: str, properties: list[SchemaField], *, if_not_exists: bool = True,
        ttl_definition: Optional[Ttl] = None
) -> str:
    return f'CREATE {schema.value}{" IF NOT EXISTS" if if_not_exists else ""} ' \
           f'{schema_name}({", ".join(str(p) for p in properties)}) {str(ttl_definition) if ttl_definition else ""};'


def create_tag_ngql(
        tag_name: str, properties: list[SchemaField], *, if_not_exists: bool = True,
        ttl_definition: Optional[Ttl] = None
) -> str:
    return create_schema_ngql(
        SchemaType.TAG, tag_name, properties, if_not_exists=if_not_exists, ttl_definition=ttl_definition
    )


def create_edge_ngql(
        edge_name: str, properties: list[SchemaField], *, if_not_exists: bool = True,
        ttl_definition: Optional[Ttl] = None
) -> str:
    return create_schema_ngql(
        SchemaType.EDGE, edge_name, properties, if_not_exists=if_not_exists, ttl_definition=ttl_definition
    )


def drop_schema_ngql(schema: SchemaType, schema_name: str, *, if_exists: bool = True) -> str:
    return f'DROP {schema.value}{" IF EXISTS" if if_exists else ""} {schema_name};'


def drop_tag_ngql(tag_name: str, *, if_exists: bool = True) -> str:
    return drop_schema_ngql(SchemaType.TAG, tag_name, if_exists=if_exists)


def drop_edge_ngql(edge_name: str, *, if_exists: bool = True) -> str:
    return drop_schema_ngql(SchemaType.EDGE, edge_name, if_exists=if_exists)


def alter_schema_ngql(
        schema: SchemaType,
        schema_name: str,
        *,
        alter_definitions: Optional[list[Alter]] = None,
        ttl_definition: Optional[Ttl] = None
) -> str:
    assert alter_definitions or ttl_definition
    return f'ALTER {schema.value} {schema_name} ' \
           f'{", ".join(str(a) for a in alter_definitions) if alter_definitions else ""}' \
           f'{str(ttl_definition) if ttl_definition else ""};'


def alter_tag_ngql(
        tag_name: str,
        *,
        alter_definitions: Optional[list[Alter]] = None,
        ttl_definition: Optional[Ttl] = None
) -> str:
    return alter_schema_ngql(
        SchemaType.TAG, tag_name, alter_definitions=alter_definitions, ttl_definition=ttl_definition
    )


def alter_edge_ngql(
        edge_name: str,
        *,
        alter_definitions: Optional[list[Alter]] = None,
        ttl_definition: Optional[Ttl] = None
) -> str:
    return alter_schema_ngql(
        SchemaType.EDGE, edge_name, alter_definitions=alter_definitions, ttl_definition=ttl_definition
    )


# ---- indexes ----

def create_index_ngql(
        schema: SchemaType, schema_name: str, index: Index, *, if_not_exists: bool = True
) -> str:
    comment = f' COMMENT "{index.comment}"' if index.comment else ''
    return f'CREATE {schema.value} INDEX{" IF NOT EXISTS" if if_not_exists else ""} ' \
           f'{index.get_name(schema_name)} ON {schema_name}{str(index)}{comment};'


def drop_index_ngql(schema: SchemaType, index_name: str, *, if_exists: bool = True) -> str:
    return f'DROP {schema.value} INDEX{" IF EXISTS" if if_exists else ""} {index_name};'


def rebuild_index_ngql(schema: SchemaType, index_names: str | list[str]) -> str:
    names = index_names if isinstance(index_names, str) else ', '.join(index_names)
    return f'REBUILD {schema.value} INDEX {names};'


def show_indexes(schema: SchemaType) -> dict[str, str]:
    """return {index name: the tag/edge it is built on} for the current space"""
    rs = run_ngql(f'SHOW {schema.value} INDEXES;')
    by_column = 'By Tag' if schema == SchemaType.TAG else 'By Edge'
    return {
        name.as_string(): by.as_string()
        for name, by in zip(rs.column_values('Index Name'), rs.column_values(by_column))
    }


def describe_index(schema: SchemaType, index_name: str) -> list[str]:
    """return the ordered field names covered by an existing index"""
    rs = run_ngql(f'DESCRIBE {schema.value} INDEX {index_name};')
    return [v.as_string() for v in rs.column_values('Field')]


def show_index_status(schema: SchemaType) -> dict[str, str]:
    """return {index name: build status} (e.g. 'FINISHED') for the current space.

    An index that has never been rebuilt does not index pre-existing data; this is
    how callers tell a created-but-not-rebuilt index from a fully-built one.
    """
    rs = run_ngql(f'SHOW {schema.value} INDEX STATUS;')
    return {
        name.as_string(): status.as_string()
        for name, status in zip(rs.column_values('Name'), rs.column_values('Index Status'))
    }
