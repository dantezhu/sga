# -*- coding: utf-8 -*-

"""
flask插件，绑定之后可以自动给本地的ga_center发送数据
要求配置:
    GA_ID : Google分析的跟踪ID
    GA_CENTER_HOST : GACenter的启动IP
    GA_CENTER_PORT : GACenter的启动端口
    GA_FORBID_PATHS : 被拒绝的paths，优先级高于 GA_ALLOW_PATHS
    GA_ALLOW_PATHS : 被允许的paths
    GA_LOG_NAME : 用来打印log的name
"""
import logging
import json
import socket
import errno
import time
import re
import urlparse

from flask import current_app, request, g

import constants


class FlaskGA(object):
    _ga_id = None
    _ga_center_host = None
    _ga_center_port = None
    _ga_forbid_paths = None
    _ga_allow_paths = None
    _ga_log_name = None

    _local_ip = ''

    _socket = None

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def __del__(self):
        if self._socket:
            self._socket.close()

    def init_app(self, app):
        """
        绑定app
        """
        self._ga_id = app.config.get('GA_ID')
        self._ga_center_host = app.config.get('GA_CENTER_HOST') or constants.GA_CENTER_DEFAULT_HOST
        self._ga_center_port = app.config.get('GA_CENTER_PORT') or constants.GA_CENTER_DEFAULT_PORT
        self._ga_forbid_paths = app.config.get('GA_FORBID_PATHS') or []
        self._ga_allow_paths = app.config.get('GA_ALLOW_PATHS') or []
        self._ga_log_name = app.config.get('GA_LOG_NAME')

        self._local_ip = socket.gethostbyname(socket.gethostname()) or ''

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 非阻塞
        self._socket.setblocking(0)

        @app.before_request
        def prepare_ga_data():
            g.ga_begin_time = time.time()

        @app.teardown_request
        def send_ga_data(exc):
            self.logger.debug('ga_id:%s', self._ga_id)

            if not self._ga_id:
                return False

            if not self._is_ga_request():
                return False

            try:
                send_dict = self._gen_send_dict()
                if not send_dict:
                    # 这个时候不是正常的请求，比如是用test_request_context模拟的
                    self.logger.debug('invalid request, may be in test_request_context')
                    return False
                self.send_data_to_ga_center(send_dict)

                return True
            except Exception, e:
                self.logger.error('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())

            return False

    def send_data_to_ga_center(self, send_dict):
        """
        可以在网站中调用
        """
        try:
            self._socket.sendto(json.dumps(send_dict), (self._ga_center_host, self._ga_center_port))
        except socket.error, e:
            # errno.EWOULDBLOCK = errno.EAGAIN = 11
            if e.args[0] == errno.EWOULDBLOCK:
                self.logger.info('errno.EWOULDBLOCK')
            else:
                self.logger.error('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())

    @property
    def logger(self):
        return current_app.logger if not self._ga_log_name else logging.getLogger(self._ga_log_name)

    def _is_ga_request(self):
        """
        request是否要被统计
        """

        # 先判断是否在forbid列表里，只要发现就直接拒绝
        for pattern in self._ga_forbid_paths:
            if re.match(pattern, request.path):
                self.logger.debug('path is in forbid paths. patten: %s, path: %s', pattern, request.path)
                return False

        # 只有allow列表不为空的情况下，才有效
        if self._ga_allow_paths:
            for pattern in self._ga_allow_paths:
                if re.match(pattern, request.path):
                    return True
            else:
                self.logger.debug('path is not in allow paths. path: %s', request.path)
                return False

        return True

    def _gen_send_dict(self):
        """
        生成发送的dict
        """
        if not getattr(g, 'ga_begin_time', None):
            return None

        load_time = int((time.time()-g.ga_begin_time) * 1000)

        ga_referrer_path = ''
        if request.referrer:
            try:
                parse_result = urlparse.urlparse(request.referrer)
                ga_referrer_path = '/%s%s' % (parse_result.netloc, parse_result.path)
            except Exception, e:
                self.logger.info('urlparse fail. e: %s', e)

        send_dict = dict(
            funcname='track_pageview',
            tracker=dict(
                __ga=True,
                account_id=self._ga_id,
                domain_name=request.host,
                campaign=dict(
                    __ga=True,
                    source=self._local_ip,
                    content=ga_referrer_path,
                ),
            ),
            session=dict(
                __ga=True,
            ),
            page=dict(
                __ga=True,
                path=request.path,
                load_time=load_time,
            ),
            visitor=dict(
                __ga=True,
                ip_address=request.remote_addr,
            ),
        )

        return send_dict
