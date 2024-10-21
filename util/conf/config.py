import base64
import json
import os
import re
import sys
from typing import Optional, Union

import yaml

from ..get_logger import get_logger

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

    pass


DEFAULT_NOT_PROVIDED = object()
GET_MAX_DEPTH = 10

logger = get_logger(__name__)


class Config:

    verbose = False
    config: dict

    def __init__(self):
        self.conffile = '%s/../../config.yaml' % os.path.dirname(os.path.realpath(__file__))  # noqa: E501
        self.load_conf()
        pass

    def load_conf(self):
        with open(self.conffile) as f:
            self.config = self._config_merge_down(yaml.load(f, Loader=Loader))
            pass
        pass

    def show_conf(self):
        if not self.get('show_conf'):
            return

        self.verbose = True
        self.log_conf()
        sys.exit(0)
        pass

    def log_conf(self):
        config = {}
        for k in self.config.keys():
            val = self.get(k)
            if type(val) == str and 'secret' in k or '_key' in k or 'key_' in k:
                val = 'xxxxxxxxx'
                pass
            config[k] = val
        logger.info('config: %s' % config)
        pass

    def set(self, key: str, val):
        if key in self.config and type(self.config[key]) != type(val):
            raise TypeError(
                f'Cannot change type of config variable {key}'
            )
        self.config[key] = val
        pass

    def get(self, key, def_val=DEFAULT_NOT_PROVIDED, depth=0):
        if depth == GET_MAX_DEPTH:
            raise RecursionError(
                f'Recursion depth limit of {depth} reached for config variable "{key}"'  # noqa: E501
            )

        suffix = self.config.get('conf_suffix', '')
        key_suffix = ('_%s' % suffix) if suffix else ''
        key_plus_suffix = '%s%s' % (key, key_suffix)

        retval = self.config.get(
            key_plus_suffix,
            self.config.get(key, def_val)
        )

        if retval == DEFAULT_NOT_PROVIDED:
            raise KeyError(f"missing config variable '{key}'")

        return self._subst_vars(
            retval,
            depth
        )

    @classmethod
    def _get_override_envvar(cls, key: str, test_id_parts: [str]) -> Optional[str]:  # noqa: E501
        candidates: [str] = []
        while test_id_parts:
            candidates.append('_'.join(test_id_parts))
            test_id_parts.pop()
            pass
        candidates.append(key)

        for i in candidates:
            envvar = os.environ.get(i.upper(), None)
            if envvar is not None:
                return cls._try_base64(envvar)
            pass

        return None

    @staticmethod
    def _override_conf(config: dict, conf_local: dict):
        for key in conf_local.keys():
            config[key] = conf_local[key]
            pass
        pass

    def _config_merge_down(self, config):
        test_id_parts = os.environ.get('CONF_SUB_PATH')

        if test_id_parts:

            logger.info('TEST CONF: reading conf for %s' % '.'.join(test_id_parts))  # noqa: E501

            for conf_name in test_id_parts:
                if conf_name in config:
                    self._override_conf(config, config[conf_name])
                    pass
                pass
            pass

        for key in config.keys():
            val = config[key]

            envvar = self._get_override_envvar(key, test_id_parts)

            if envvar is not None:
                fix_type = type(val)
                if fix_type == int:
                    config[key] = int(envvar)
                elif fix_type == float:
                    config[key] = float(envvar)
                elif fix_type == bool:
                    config[key] = bool(int(envvar))
                elif fix_type == dict:
                    config[key] = json.loads(envvar)
                elif fix_type == list:
                    try:
                        config[key] = json.loads(envvar)
                    except json.decoder.JSONDecodeError:
                        config[key] = envvar.split(',')
                        pass
                elif fix_type == str:
                    config[key] = envvar
                else:
                    raise Exception(
                        'testbase.TestBase#config_merge_down: HDIGH! (type: %s)' % fix_type)  # noqa: E501
            pass

        return config

    @staticmethod
    def _try_base64(s: str) -> str:
        if s[:len('data:')] == 'data:':
            dummy, data = s.split('data:')
            bb = base64.b64decode(data)
            return bb.decode('UTF-8')

        return s

    pass

    def _subst_vars(
            self,
            retval: Union[int, str, dict, list, float, bool, None],
            depth: int
    ):
        t = type(retval)

        def subst_vars(m):
            return self.get(m.group(1), DEFAULT_NOT_PROVIDED, depth + 1)

        if t == str:
            retval = re.sub(
                r'\${([a-zA-Z0-9_]+)}',
                subst_vars,
                retval
            )
        if t == list:
            retval = [self._subst_vars(i, depth) for i in retval]
        if t == dict:
            keys = list(retval.keys())
            for k in keys:
                retval[k] = self._subst_vars(retval[k], depth)
        return retval
    pass
