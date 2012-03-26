import tg
import random, logging

try:
    from sqlalchemy.orm import Session
except ImportError:
    class Session(object):
        """SQLAlchemy Session"""

log = logging.getLogger(__name__)

class BalancedSession(Session):
    def get_bind(self, mapper=None, clause=None):
        config = tg.config._current_obj()
        engines = config.get('balanced_engines')
        if not engines:
            log.debug('Balancing disabled, using master')
            return config['pylons.app_globals'].sa_engine

        forced_engine = self._force_engine
        if not forced_engine:
            try:
                forced_engine = tg.request._tg_force_sqla_engine
            except TypeError:
                forced_engine = 'master'
            except AttributeError:
                pass

        if forced_engine:
            log.debug('Forced engine: %s', forced_engine)
            return engines['all'][forced_engine]
        elif self._flushing:
            log.debug('Choose engine: master')
            return engines['master']
        else:
            choosen_slave = random.choice(engines['slaves'].keys())
            log.debug('Choose engine: %s', choosen_slave)
            return engines['slaves'][choosen_slave]

    _force_engine = None
    def using_engine(self, engine_name):
        s = BalancedSession()
        vars(s).update(vars(self))
        s._force_engine = engine_name
        return s

def force_request_engine(engine_name):
    tg.request._tg_force_sqla_engine = engine_name
