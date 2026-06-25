from datetime import datetime

from nebula_carina.models import models
from nebula_carina.models.fields import create_nebula_field as _
from nebula_carina.ngql.schema import data_types
from nebula_carina.ngql.statements.schema import Index


class Figure(models.TagModel):
    name: str = _(data_types.FixedString(30), ..., )
    age: int = _(data_types.Int16, ..., )
    valid_until: int = _(data_types.Int64, None, )
    hp: int = _(data_types.Int16, 100, )
    style: str = _(data_types.FixedString(10), 'rap', )
    is_virtual: bool = _(data_types.Bool, True)
    created_on: datetime = _(data_types.Datetime, data_types.Datetime.auto)
    some_dt: datetime = _(data_types.Datetime, datetime(2022, 1, 1))

    class Meta:
        ttl_duration = 100
        ttl_col = 'valid_until'
        indexes = [
            Index([]),                         # tag-only index, enables full scans
            Index(['is_virtual']),             # index a bool prop for filtering
            Index([('name', 10)], name='figure_name'),  # string prop needs a length
        ]


class Source(models.TagModel):
    name: str = _(data_types.FixedString(30), ..., )


class Belong(models.EdgeTypeModel):
    pass


class Love(models.EdgeTypeModel):
    way: str = _(data_types.FixedString(10), ..., )
    times: int = _(data_types.Int8, ..., )

    class Meta:
        indexes = [Index(['times'])]


class Support(models.EdgeTypeModel):
    food_amount: int = _(data_types.Int16, ..., )


class VirtualCharacter(models.VertexModel):
    figure: Figure
    source: Source


class LimitedCharacter(models.VertexModel):
    figure: Figure
