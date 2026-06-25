import unittest

from nebula_carina.ngql.schema.schema import (
    create_index_ngql, drop_index_ngql, rebuild_index_ngql,
)
from nebula_carina.ngql.statements.schema import Index, IndexField, SchemaType


class TestIndexStatements(unittest.TestCase):
    """Pure ngql-string tests, no database connection required."""

    def test_index_field(self):
        self.assertEqual(str(IndexField('age')), 'age')
        self.assertEqual(str(IndexField('name', 20)), 'name(20)')

    def test_index_name_and_columns(self):
        # explicit name wins
        self.assertEqual(Index(['age'], name='my_idx').get_name('figure'), 'my_idx')
        # auto name from schema + fields
        self.assertEqual(Index(['age']).get_name('figure'), 'i_figure_age')
        self.assertEqual(Index(['a', 'b']).get_name('figure'), 'i_figure_a_b')
        # empty fields -> schema-only index name and column list
        self.assertEqual(Index([]).get_name('figure'), 'i_figure')
        self.assertEqual(str(Index([])), '()')

    def test_field_normalization(self):
        index = Index(['age', ('name', 20), IndexField('style', 5)])
        self.assertEqual(index.field_names(), ['age', 'name', 'style'])
        self.assertEqual(str(index), '(age, name(20), style(5))')

    def test_create_index_ngql(self):
        self.assertEqual(
            create_index_ngql(SchemaType.TAG, 'figure', Index([('name', 10)], name='figure_name')),
            'CREATE TAG INDEX IF NOT EXISTS figure_name ON figure(name(10));',
        )
        self.assertEqual(
            create_index_ngql(SchemaType.EDGE, 'love', Index(['times']), if_not_exists=False),
            'CREATE EDGE INDEX i_love_times ON love(times);',
        )
        self.assertEqual(
            create_index_ngql(SchemaType.TAG, 'figure', Index([], comment='scan all')),
            'CREATE TAG INDEX IF NOT EXISTS i_figure ON figure() COMMENT "scan all";',
        )

    def test_drop_and_rebuild_index_ngql(self):
        self.assertEqual(
            drop_index_ngql(SchemaType.TAG, 'figure_name'),
            'DROP TAG INDEX IF EXISTS figure_name;',
        )
        self.assertEqual(
            rebuild_index_ngql(SchemaType.EDGE, 'i_love_times'),
            'REBUILD EDGE INDEX i_love_times;',
        )
        self.assertEqual(
            rebuild_index_ngql(SchemaType.TAG, ['a', 'b']),
            'REBUILD TAG INDEX a, b;',
        )


if __name__ == '__main__':
    unittest.main()
