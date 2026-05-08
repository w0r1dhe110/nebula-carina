try:
    import time

    from django.core.management.base import BaseCommand, CommandError
    from nebula_carina.models.migrations import make_migrations, migrate
    from nebula_carina.ngql.schema.space import create_space, show_spaces
    from nebula_carina.settings import database_settings
    from nebula_carina.ngql.connection.connection import run_ngql


    class Command(BaseCommand):
        help = 'Run Nebula Graph migrations'

        def add_arguments(self, parser):
            parser.add_argument(
                '--noinput', '--no-input',
                dest='interactive', action='store_false', default=True,
                help='Do not prompt for confirmation.',
            )

        def _ensure_default_space(self):
            spec = database_settings.auto_create_default_space_with_vid_desc
            if not spec:
                return
            space = database_settings.default_space
            if space in show_spaces():
                return
            self.stdout.write(f'Creating default space {space!r} ...')
            create_space(space, spec, if_not_exists=True)
            # CREATE SPACE 异步广播给 storaged，poll 直到可见
            for i in range(30):
                if space in show_spaces():
                    self.stdout.write(f'Space {space!r} ready (after {i + 1}s).')

                    time.sleep(3)
                    run_ngql(f'USE `{space}`;')
                    return
                time.sleep(1)
            raise CommandError(f'Space {space!r} not visible after 30s.')

        def handle(self, *args, **options):
            self._ensure_default_space()

            migrations = make_migrations()
            if not migrations:
                self.stdout.write('No Nebula Graph schema change found')
                return
            self.stdout.write('The following migration NGQLs will be executed: \n\n%s' % ('\n'.join(migrations)))
            if options['interactive'] and input("Type 'yes' to continue, or 'no' to cancel\n") != 'yes':
                self.stdout.write(self.style.NOTICE('Nebula migration cancelled.'))
                return
            migrate(make_migrations())
            self.stdout.write(self.style.SUCCESS('Nebula migration succeeded.'))

except ModuleNotFoundError:
    pass