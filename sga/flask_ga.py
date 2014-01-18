# -*- coding: utf-8 -*-

"""
flask插件，绑定之后可以自动给本地的ga_agent发送数据
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
from ga_adapter import GAAdapter


class FlaskGA(GAAdapter):

    def __init__(self, app=None):
        super(FlaskGA, self).__init__()

        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        绑定app
        """
        self._ga_id = app.config.get('GA_ID')
        self._ga_agent_host = app.config.get('GA_AGENT_HOST') or constants.GA_AGENT_HOST
        self._ga_agent_port = app.config.get('GA_AGENT_PORT') or constants.GA_AGENT_PORT
        self._ga_forbid_paths = app.config.get('GA_FORBID_PATHS')
        self._ga_allow_paths = app.config.get('GA_ALLOW_PATHS')
        self._ga_hack_paths = app.config.get('GA_HACK_PATHS')
        self._ga_logger_name = app.config.get('GA_LOGGER_NAME')

        @app.before_request
        def prepare_ga_data():
            g.ga_begin_time = time.time()

        @app.teardown_request
        def send_ga_data(exc):
            self.logger.debug('ga_id:%s', self._ga_id)

            if not self._ga_id:
                return False

            if not self.is_ga_request(request.path):
                return False

            try:
                send_dict = self._gen_send_dict()
                if not send_dict:
                    # 这个时候不是正常的请求，比如是用test_request_context模拟的
                    self.logger.debug('invalid request, may be in test_request_context')
                    return False
                self.send_data_to_ga_agent(send_dict)

                return True
            except Exception, e:
                self.logger.error('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())

            return False

    @property
    def logger(self):
        return current_app.logger if not self._ga_logger_name else logging.getLogger(self._ga_logger_name)

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
                path=self.hack_path(request.path),
                load_time=load_time,
            ),
            visitor=dict(
                __ga=True,
                ip_address=request.remote_addr,
            ),
        )

        return send_dict
