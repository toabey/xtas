# Copyright 2013-2015 Netherlands eScience Center and University of Amsterdam
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Core functionality. Contains the configuration and the (singleton) Celery
"app" instance.
"""

from __future__ import absolute_import

import importlib
import logging

from celery import Celery

from . import _defaultconfig


__all__ = ['app', 'configure', 'get_config']


_config = {}

logger = logging.getLogger(__name__)

app = Celery('xtas', include=['xtas.tasks'])

_CONFIG_KEYS = frozenset(['CELERY', 'ELASTICSEARCH', 'EXTRA_MODULES'])


def configure(config, import_error="raise", unknown_key="raise"):
    """Configure xtas. Settings made here override defaults and settings
    made in the configuration file.

    Parameters
    ----------
    config : dict
        Dict with keys ``CELERY``, ``ELASTICSEARCH`` and ``EXTRA_MODULES``
        will be used to configure the xtas Celery app.

        ``config.CELERY`` will be passed to Celery's ``config_from_object``
        with the flag ``force=True``.

        ``ELASTICSEARCH`` should be a list of dicts with at least the key
        'host'. These are passed to the Elasticsearch constructor (from the
        official client) unchanged.

        ``EXTRA_MODULES`` should be a list of module names to load.

        Failure to supply ``CELERY`` or ``ELASTICSEARCH`` causes the default
        configuration to be re-set. Extra modules will not be unloaded,
        though.

    import_error : string
        Action to take when one of the ``EXTRA_MODULES`` cannot be imported.
        Either "log", "raise" or "ignore".

    unknown_key : string
        Action to take when a member not matching the ones listed above is
        encountered in the config argument (except when its name starts
        with an underscore). Either "log", "raise" or "ignore".
    """

    if unknown_key != 'ignore':
        unknown_keys = set(config.keys()) - _CONFIG_KEYS
        if unknown_keys:
            msg = ("unknown keys %r found on config object %r"
                   % (unknown_keys, config))
            if unknown_keys == 'raise':
                raise ValueError(msg)
            else:
                logger.warn(msg)

    celery_conf = config.get('CELERY', _defaultconfig.CELERY)
    app.config_from_object(celery_conf)

    es = config.get('ELASTICSEARCH', _defaultconfig.ELASTICSEARCH)
    logger.info('Using Elasticsearch with configuration %r' % es)

    extra = config.get('EXTRA_MODULES', [])
    for m in extra:
        try:
            importlib.import_module(m)
        except ImportError as e:
            if import_error == 'raise':
                raise
            elif import_error == 'log':
                logger.warn(str(e))

    _config['CELERY'] = celery_conf
    _config['ELASTICSEARCH'] = es
    _config['EXTRA_MODULES'] = extra


def get_config(key):
    """Get part of the xtas configuration.

    Parameters
    ----------
    key : string
        Either ``CELERY``, ``ELASTICSEARCH`` or ``EXTRA_MODULES``.
        See ``xtas.core.configure`` for the meaning of these.
    """
    if key not in _CONFIG_KEYS:
        raise ValueError("key should be one of %r, got %r"
                         % (list(_CONFIG_KEYS), key))
    return _config.get(key)


try:
    config_module = importlib.import_module('xtas_config')
    content = {name: getattr(config_module, name)
               for name in dir(config_module)}
    configure(content, unknown_key='ignore')
except ImportError:
    logger.info('Cannot import xtas_config, falling back to default')
    configure({})
