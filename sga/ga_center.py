#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用来作为接受google统计上报的center
通过udp通道。
"""

import json
import functools
import logging
import logging.config
import socket
import threading
import SocketServer
import signal
import sys
import time
import constants

logger = logging.getLogger('ga_center')


def record_exception(func):
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            logger.error('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())
            return None

    return func_wrapper


def alloc_ga_obj_by_name(name):
    """
    通过名字生成对应的obj
    """
    from pyga.requests import Tracker, Page, Session, Visitor, Transaction, Event, SocialInteraction, Campaign

    obj = None
    if name == 'tracker':
        obj = Tracker()
    elif name == 'campaign':
        obj = Campaign(Campaign.TYPE_REFERRAL)
    elif name == 'session':
        obj = Session()
    elif name == 'page':
        obj = Page(None)
    elif name == 'visitor':
        obj = Visitor()
    elif name == 'transaction':
        obj = Transaction()
    elif name == 'event':
        obj = Event()
    elif name == 'social_interaction':
        obj = SocialInteraction()

    return obj


def recur_make_obj(name, conf):
    """
    递归生成
    """
    if isinstance(conf, dict) and conf.get('__ga'):
        obj = alloc_ga_obj_by_name(name)
        if not obj:
            return obj

        for attr_name, attr_value in conf.items():
            if attr_name == '__ga':
                continue
            real_value = recur_make_obj(attr_name, attr_value)
            setattr(obj, attr_name, real_value)

        return obj
    else:
        return conf


@record_exception
def handle_message(message):
    recv_dict = json.loads(message)

    # 就可以直接删除了
    funcname = recv_dict.pop('funcname', None)
    caller = None
    kwargs = dict()

    for name, conf in recv_dict.items():
        obj = recur_make_obj(name, conf)

        if name == 'tracker':
            caller = obj
        else:
            kwargs[name] = obj
    return getattr(caller, funcname)(**kwargs)


class ThreadedUDPRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        message = self.request[0]
        logger.debug("message, len: %s, content: %s", len(message), message)
        #cur_thread = threading.current_thread()
        handle_message(message)


class GACenter(SocketServer.ThreadingUDPServer):

    def __init__(self, host=None, port=None):
        # 因为父类继承是用的老风格，所以必须按照下面的方式来写。 不能使用 super(GACenter, self).__init__
        SocketServer.ThreadingUDPServer.__init__(self,
                                                 (host or constants.GA_CENTER_DEFAULT_HOST,
                                                  port or constants.GA_CENTER_DEFAULT_PORT),
                                                 ThreadedUDPRequestHandler)

    @record_exception
    def run(self):
        server_thread = threading.Thread(target=self.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()

        # 因为daemon设置为true，所以不做while循环会直接退出
        # 而之所以把 daemon 设置为true，是为了防止进程不结束的问题
        while True:
            time.sleep(1)
