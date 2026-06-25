from enum import Enum

from nebula_carina.ngql.schema import data_types
from nebula_carina.ngql.statements.core import Statement


class SchemaField(Statement):
    __slots__ = ('prop_name', 'data_type', 'nullable', 'default', 'comment')

    def __init__(
            self, prop_name: str, data_type: data_types.DataType,
            nullable: bool = False, default: any = None, comment: str = None
    ):
        self.prop_name = prop_name
        self.data_type = data_type
        self.nullable = nullable
        self.default = self.data_type.clean_default(default)
        self.comment = comment

    def __str__(self):
        comment = f' COMMENT "{self.comment}"' if self.comment else ''
        return f'{self.prop_name} {self.data_type} {"NULL" if self.nullable else "NOT NULL"}' \
               f'{f" DEFAULT {self.data_type.value2db_str(self.default)}" if self.default is not None else ""}' \
               f'{comment}'


class AlterType(Enum):
    ADD = 'ADD'
    DROP = 'DROP'
    CHANGE = 'CHANGE'


class SchemaType(Enum):
    TAG = 'TAG'
    EDGE = 'EDGE'


class Ttl(Statement):
    __slots__ = ('ttl_duration', 'ttl_col')

    def __init__(self, ttl_duration: int, ttl_col: str):
        self.ttl_duration = ttl_duration
        self.ttl_col = ttl_col

    def __str__(self):
        ttl_col = f', TTL_COL = "{self.ttl_col}"' if self.ttl_col else ''
        return f'TTL_DURATION = {self.ttl_duration}{ttl_col}'


class IndexField(Statement):
    """A single property within an index.

    ``length`` is required by NebulaGraph for variable-length ``string`` columns
    and optional (up to the declared length) for ``fixed_string`` columns; it
    must be omitted for every other data type.
    """
    __slots__ = ('prop_name', 'length')

    def __init__(self, prop_name: str, length: int | None = None):
        self.prop_name = prop_name
        self.length = length

    def __str__(self):
        return f'{self.prop_name}({self.length})' if self.length else self.prop_name


class Index(Statement):
    """An index declaration for a TAG or EDGE type.

    ``fields`` accepts property names (``str``), ``(name, length)`` tuples, or
    :class:`IndexField` instances. An empty ``fields`` list builds an index over
    the schema itself, which is what enables full ``MATCH`` / ``LOOKUP`` scans
    that carry no property predicate.
    """
    __slots__ = ('name', 'fields', 'comment')

    def __init__(
            self, fields: list, *, name: str | None = None, comment: str | None = None
    ):
        self.fields = [
            f if isinstance(f, IndexField)
            else IndexField(*f) if isinstance(f, (tuple, list))
            else IndexField(f)
            for f in fields
        ]
        self.name = name
        self.comment = comment

    def get_name(self, schema_name: str) -> str:
        if self.name:
            return self.name
        suffix = '_'.join(f.prop_name for f in self.fields)
        return f'i_{schema_name}_{suffix}' if suffix else f'i_{schema_name}'

    def field_names(self) -> list[str]:
        return [f.prop_name for f in self.fields]

    def __str__(self):
        return f'({", ".join(str(f) for f in self.fields)})'


class Alter(Statement):
    __slots__ = ('alter_definition_type', 'properties', 'prop_names')

    def __init__(
            self, alter_definition_type: AlterType, *,
            properties: list[SchemaField] | None = None, prop_names: list[str] = None
    ):
        self.alter_definition_type = alter_definition_type
        if self.alter_definition_type == AlterType.DROP:
            assert prop_names
            self.prop_names = prop_names
        else:
            assert properties
            self.properties = properties

    def __str__(self):
        if self.alter_definition_type == AlterType.DROP:
            return f'{self.alter_definition_type.value} ({",".join(self.prop_names)})'
        return f'{self.alter_definition_type.value} ({", ".join(str(p) for p in self.properties)})'
