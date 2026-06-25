import inspect
import re
import time
from importlib import import_module

from nebula_carina.models.models import TagModel, EdgeTypeModel
from nebula_carina.ngql.connection.connection import run_ngql
from nebula_carina.ngql.errors import NGqlError
from nebula_carina.ngql.schema.schema import show_tags, show_edges, show_indexes
from nebula_carina.ngql.statements.schema import SchemaType
from nebula_carina.settings import database_settings


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


# NebulaGraph propagates schema / index DDL asynchronously (it becomes visible
# after the next heartbeat), so a statement that depends on a just-issued one can
# fail with "not found". These patterns let migrate() wait for the dependency to
# show up before running the dependent statement.
_CREATE_INDEX_RE = re.compile(
    r'^\s*CREATE\s+(TAG|EDGE)\s+INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?\S+\s+ON\s+(\w+)',
    re.IGNORECASE,
)
_REBUILD_INDEX_RE = re.compile(
    r'^\s*REBUILD\s+(TAG|EDGE)\s+INDEX\s+(.+?);?\s*$', re.IGNORECASE,
)


def _wait_until(fetch_existing, names, *, timeout: int = 60, interval: int = 2):
    """Poll ``fetch_existing()`` until every name in ``names`` is present.

    Returns once all names are found or the timeout elapses; on timeout it returns
    quietly and lets the following ngql raise its own precise error.
    """
    pending = set(names)
    deadline = time.time() + timeout
    while pending:
        pending -= set(fetch_existing())
        if not pending:
            return
        if time.time() >= deadline:
            return
        time.sleep(interval)


def _await_dependencies(ngql: str):
    create_match = _CREATE_INDEX_RE.match(ngql)
    if create_match:
        is_tag = create_match.group(1).upper() == 'TAG'
        # the index's tag/edge must be visible before CREATE INDEX runs
        _wait_until(show_tags if is_tag else show_edges, [create_match.group(2)])
        return None
    rebuild_match = _REBUILD_INDEX_RE.match(ngql)
    if rebuild_match:
        schema_type = SchemaType.TAG if rebuild_match.group(1).upper() == 'TAG' else SchemaType.EDGE
        names = [n.strip() for n in rebuild_match.group(2).split(',')]
        # the index must be visible before REBUILD runs
        _wait_until(lambda: list(show_indexes(schema_type)), names)
        return rebuild_match
    return None


def _run_rebuild(ngql: str, *, attempts: int = 10, interval: int = 3):
    """Run a REBUILD, retrying on "not found".

    Even after SHOW ... INDEXES lists a freshly created index, the job-manager
    path REBUILD uses can briefly still report it as missing while the metadata
    finishes propagating; retrying rides out that window.
    """
    for attempt in range(attempts):
        try:
            return run_ngql(ngql)
        except NGqlError as e:
            if 'not found' not in str(e).lower() or attempt == attempts - 1:
                raise
            time.sleep(interval)


def migrate(ngql_list):
    for ngql in ngql_list:
        is_rebuild = _await_dependencies(ngql)
        if is_rebuild:
            _run_rebuild(ngql)
        else:
            run_ngql(ngql)
