# -*- coding: utf-8 -*-

import time
import logging
from ga_adapter import GAAdapter
import constants


class KolaGA(GAAdapter):
    """
    上报GA
    使用:
        KolaGA(dict(...))).init_app(app)
    config: dict类型
    """

    def __init__(self, config, app=None):
        super(KolaGA, self).__init__()

        self._ga_id = config.get('GA_ID')
        self._ga_agent_host = config.get('GA_AGENT_HOST') or constants.GA_AGENT_HOST
        self._ga_agent_port = config.get('GA_AGENT_PORT') or constants.GA_AGENT_PORT
        self._ga_forbid_paths = config.get('GA_FORBID_PATHS')
        self._ga_allow_paths = config.get('GA_ALLOW_PATHS')
        self._ga_hack_paths = config.get('GA_HACK_PATHS')
        self._ga_logger_name = config.get('GA_LOGGER_NAME')

        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        注册相关的函数
        """

        @app.before_request
        def prepare_ga_data(request):
            request.ga_begin_time = time.time()

        @app.after_request
        def send_ga_data(request, result):
            self.logger.debug('ga_id:%s', self._ga_id)

            if not self._ga_id:
                return False

            if not self.is_ga_request(request.endpoint):
                return

            try:
                send_dict = self._gen_send_dict(request)
                if not send_dict:
                    # 这个时候不是正常的请求，比如是用test_request_context模拟的
                    self.logger.debug('invalid request')
                    return False
                self.send_data_to_ga_agent(send_dict)

                return True
            except Exception, e:
                self.logger.exception('exception')

            return False

    @property
    def logger(self):
        return logging.getLogger(self._ga_logger_name or 'kola_ga')

    def _gen_send_dict(self, request):
        """
        生成发送的dict
        """
        if not getattr(request, 'ga_begin_time', None):
            return None

        # 为了解决总是0的问题
        load_time = int((time.time()-request.ga_begin_time) * 1000 * 1000)

        send_dict = dict(
            funcname='track_pageview',
            tracker=dict(
                __ga=True,
                account_id=self._ga_id,
                domain_name=self._local_ip,
                campaign=dict(
                    __ga=True,
                    source=self._local_ip,
                    content='',
                ),
            ),
            session=dict(
                __ga=True,
            ),
            page=dict(
                __ga=True,
                path='/' + self.hack_path(request.endpoint),
                load_time=load_time,
            ),
            visitor=dict(
                __ga=True,
                ip_address=request.address,
            ),
        )

        return send_dict
