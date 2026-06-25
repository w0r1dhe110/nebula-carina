from nebula_carina.models.models import TagModel, EdgeTypeModel
from nebula_carina.ngql.connection.connection import run_ngql
from nebula_carina.ngql.schema.schema import show_tags, show_edges
from nebula_carina.settings import database_settings
from importlib import import_module
import inspect


def make_migrations():
    existing_tags = show_tags()
    existing_edges = show_edges()
    schema_ngqls = []
    index_ngqls = []
    model_paths = database_settings.model_paths
    for model_path in model_paths:
        module = import_module(model_path)
        for name, cls in module.__dict__.items():
            if inspect.isclass(cls) and (issubclass(cls, TagModel) or issubclass(cls, EdgeTypeModel)):
                if cls.db_name() in existing_tags or cls.db_name() in existing_edges:
                    alter_schema_ngql = cls.alter_schema_ngql()
                    alter_schema_ngql and schema_ngqls.append(alter_schema_ngql)
                else:
                    schema_ngqls.append(cls.create_schema_ngql())
                index_ngqls.extend(cls.index_migration_ngqls())
    # index DDL is emitted after all tag/edge DDL so the schema it references
    # has had a chance to be created/altered first
    return schema_ngqls + index_ngqls


def migrate(ngql_list):
    for ngql in ngql_list:
        run_ngql(ngql)
