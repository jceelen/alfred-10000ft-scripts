#!/usr/bin/python
# encoding: utf-8
#
# rename_workflow
#
# Copyright (c) 2015 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2015-08-02
#

"""rename_workflow [options] [<workflow-dir>...]

Rename workflow directory after bundle ID.

Usage:
    rename_workflow [-v|-q] [-n] [<workflow-dir>...]
    rename_workflow (-h|--help|--version)

Options:
    -n, --nothing  Don't actually rename workflow
    --version      Show version number and exit
    -h, --help     Show this message and exit
    -q, --quiet    Only show warnings and errors
    -v, --verbose  Show debug messages

"""

from __future__ import print_function, unicode_literals, absolute_import

import logging
import logging.handlers
import os
import plistlib
import sys

__version__ = '0.1'
__author__ = 'deanishe@deanishe.net'


DEFAULT_LOG_LEVEL = logging.INFO
LOGPATH = os.path.expanduser('~/Library/Logs/MyScripts.log')
LOGSIZE = 1024 * 1024 * 1  # 1 megabyte

# Populated by init_logging()
log = None


class TechnicolorFormatter(logging.Formatter):
    """
    Prepend level name to any message not level logging.INFO.

    Also, colour!

    """

    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

    RESET = '\033[0m'
    COLOUR_BASE = '\033[1;{:d}m'
    BOLD = '\033[1m'

    LEVEL_COLOURS = {
        logging.DEBUG:    BLUE,
        logging.INFO:     WHITE,
        logging.WARNING:  YELLOW,
        logging.ERROR:    MAGENTA,
        logging.CRITICAL: RED
    }

    def __init__(self, fmt=None, datefmt=None, technicolor=True):
        logging.Formatter.__init__(self, fmt, datefmt)
        self.technicolor = technicolor
        self._isatty = sys.stderr.isatty()

    def format(self, record):
        if record.levelno == logging.INFO:
            msg = logging.Formatter.format(self, record)
            return msg
        if self.technicolor and self._isatty:
            colour = self.LEVEL_COLOURS[record.levelno]
            bold = (False, True)[record.levelno > logging.INFO]
            levelname = self.colourise('{:9s}'.format(record.levelname),
                                       colour, bold)
        else:
            levelname = '{:9s}'.format(record.levelname)
        return (levelname + logging.Formatter.format(self, record))

    def colourise(self, text, colour, bold=False):
        colour = self.COLOUR_BASE.format(colour + 30)
        output = []
        if bold:
            output.append(self.BOLD)
        output.append(colour)
        output.append(text)
        output.append(self.RESET)
        return ''.join(output)


def init_logging():
    global log
    # logfile
    logfile = logging.handlers.RotatingFileHandler(LOGPATH,
                                                   maxBytes=LOGSIZE,
                                                   backupCount=1)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s [%(name)-12s] %(message)s',
        datefmt="%d/%m %H:%M:%S")
    logfile.setFormatter(formatter)
    logfile.setLevel(logging.DEBUG)

    # console output
    console = logging.StreamHandler()
    formatter = TechnicolorFormatter('%(message)s')
    console.setFormatter(formatter)
    console.setLevel(logging.DEBUG)

    log = logging.getLogger('rename_workflow')
    log.addHandler(logfile)
    log.addHandler(console)


def printable_path(dirpath):
    """Replace $HOME with ~"""
    return dirpath.replace(os.getenv('HOME'), '~')


def is_workflow(dirpath):
    """Return True if `dirpath` is an Alfred workflow"""
    return os.path.exists(os.path.join(dirpath, 'info.plist'))


def get_bundle_id(dirpath):
    """Return bundle ID of workflow in `dirpath`"""
    ip_path = os.path.join(dirpath, 'info.plist')
    data = plistlib.readPlist(ip_path)
    return data.get('bundleid').replace('/', '.')


def rename_workflow(dirpath, simulate=False):
    """Rename workflow at `dirpath` after its bundle ID"""
    if not is_workflow(dirpath):
        log.warning('Not a workflow : %s', dirpath)
        return None

    bundle_id = get_bundle_id(dirpath)
    if not bundle_id:
        log.warning('No bundle ID : %s', dirpath)
        return None

    log.debug('Bundle ID for `%s` : `%s`', dirpath, bundle_id)

    newpath = os.path.join(os.path.dirname(dirpath), bundle_id)

    if dirpath == newpath:
        log.debug('No change : %s', dirpath)
        return True

    if os.path.exists(newpath):
        log.warning('Destination already exists : %s', newpath)
        return False

    if not simulate:
        os.rename(dirpath, newpath)

    action = ('Renamed', 'Would rename')[simulate]
    log.info('%s `%s` to `%s`',
             action,
             printable_path(dirpath),
             printable_path(newpath))

    return True


def main(args=None):

    init_logging()
    from docopt import docopt
    args = docopt(__doc__, version=__version__)

    if args.get('--verbose'):
        log.setLevel(logging.DEBUG)
    elif args.get('--quiet'):
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(DEFAULT_LOG_LEVEL)
    log.debug("Set log level to %s" %
              logging.getLevelName(log.level))

    log.debug('args : %s', args)

    dirpaths = args.get('<workflow-dir>')
    dirpaths = [os.path.abspath(p) for p in dirpaths]

    for dirpath in dirpaths:
        if not os.path.exists(dirpath):
            log.warning('Does not exist : %s', dirpath)
            continue
        elif not os.path.isdir(dirpath):
            log.warning('Not a directory : %s', dirpath)
            continue
        rename_workflow(dirpath, args.get('--nothing'))

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))