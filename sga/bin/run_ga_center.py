#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动 ga_center
"""

import argparse
import os.path as op
import logging
import logging.config

import sys
sys.path.insert(0, '../../')
import sga
from sga.ga_center import GACenter
from sga import constants


# 日志
# 为了保证邮件只有在正式环境发送
class RequireDebugOrNot(logging.Filter):
    _need_debug = False

    def __init__(self, need_debug, *args, **kwargs):
        super(RequireDebugOrNot, self).__init__(*args, **kwargs)
        self._need_debug = need_debug
        
    def filter(self, record):
        return debug if self._need_debug else not debug


FILE_MODULE_NAME = op.splitext(op.basename(__file__))[0]

LOG_FILE_PATH = "/tmp/ga_center.log"

LOG_FORMAT = '\n'.join((
    '/' + '-' * 80,
    '[%(levelname)s][%(asctime)s][%(process)d:%(thread)d][%(filename)s:%(lineno)d %(funcName)s]:',
    '%(message)s',
    '-' * 80 + '/',
))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'standard': {
            'format': LOG_FORMAT,
        },
    },

    'filters': {
        'require_debug_false': {
            '()': RequireDebugOrNot,
            'need_debug': False,
        },
        'require_debug_true': {
            '()': RequireDebugOrNot,
            'need_debug': True,
        },
    },

    'handlers': {
        'rotating_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': LOG_FILE_PATH,
            'maxBytes': 1024 * 1024 * 500,  # 500 MB
            'backupCount': 5,
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'filters': ['require_debug_true'],
        },
    },

    'loggers': {
        'default': {
            'handlers': ['console', 'rotating_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'ga_center': {
            'handlers': ['console', 'rotating_file'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}


logger = logging.getLogger('default')
debug = False


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--host', default=constants.GA_CENTER_DEFAULT_HOST, help='bind host', action='store')
    parser.add_argument('-p', '--port', default=constants.GA_CENTER_DEFAULT_PORT, type=int, help='bind port', action='store')
    parser.add_argument('-d', '--debug', default=False, help='debug mode', action='store_true')
    parser.add_argument('-v', '--version', action='version', version='%s' % sga.__version__)
    return parser


def configure_logging():
    logging.config.dictConfig(LOGGING)

 
def run_ga_center():
    global debug

    configure_logging()

    args = build_parser().parse_args()

    # 设置到全局配置里
    debug = args.debug

    logger.info("Running GACenter on %(host)s:%(port)s, debug:%(debug)s" % dict(
        host=args.host, port=args.port, debug=args.debug)
    )

    prog = GACenter(args.host, args.port)
    try:
        prog.run()
    except KeyboardInterrupt:
        sys.exit(0)
 
if __name__ == '__main__':
    run_ga_center()
