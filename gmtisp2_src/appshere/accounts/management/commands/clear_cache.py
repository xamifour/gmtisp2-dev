# mpi_src/usermanager/management/commands/clear_cache.py

import logging
from django.core.management.base import BaseCommand
from django.core.cache import cache

logger = logging.getLogger('usermanager')

class Command(BaseCommand):
    help = 'Clears the cache'

    def handle(self, *args, **options):
        cache.clear()
        logger.info('Cache has been cleared via management command by user.')
        self.stdout.write(self.style.SUCCESS('Cache has been cleared successfully'))


# Usage: You can run this command from the command line as follows:
# python manage.py clear_cache
