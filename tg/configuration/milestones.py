# -*- coding: utf-8 -*-
"""
Utilities for lazy resolution of configurations.

Provides a bunch of tools to perform actions that need
the configuration to be in place when performed

"""

from logging import getLogger
log = getLogger(__name__)


class _ConfigMilestoneTracker(object):
    """Tracks actions that need to be performed
    when a specific configuration point is reached
    and required options are correctly initialized

    """
    def __init__(self, name):
        self.name = name
        self._actions = set()
        self._reached = False

    def register(self, action):
        """Registers an action to be called on milestone completion.

        If milestone is already passed action is immediately called

        """
        if self._reached:
            log.debug('%s milestone passed, calling %s directly', self.name, action)
            action()
        else:
            log.debug('Register %s to be called when %s reached', action, self.name)
            self._actions.add(action)

    def reach(self):
        """Marks the milestone as reached.

        Runs the registered actions. Calling this
        method multiple times should lead to nothing.

        """
        self._reached = True

        log.debug('%s milestone reached', self.name)
        while True:
            try:
                action = self._actions.pop()
                action()
            except KeyError:
                break

    def _reset(self):
        """This is just for testing purposes"""
        self._reached = False
        self._actions = set()


config_ready = _ConfigMilestoneTracker('config_ready')
renderers_ready = _ConfigMilestoneTracker('renderers_ready')

