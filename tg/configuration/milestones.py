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
        self._actions = dict()
        self._reached = False
        self._keep_on_reset = []

    @property
    def reached(self):
        return self._reached

    def register(self, action, persist_on_reset=False):
        """Registers an action to be called on milestone completion.

        If milestone is already passed action is immediately called

        """
        if persist_on_reset:
            self._keep_on_reset.append(action)

        if self._reached:
            log.debug('%s milestone passed, calling %s directly', self.name, action)
            action()
        else:
            log.debug('Register %s to be called when %s reached', action, self.name)
            self._actions[id(action)] = action

    def reach(self):
        """Marks the milestone as reached.

        Runs the registered actions. Calling this
        method multiple times should lead to nothing.

        """
        log.debug('%s milestone reached', self.name)

        try:
            while True:
                try:
                    __, action = self._actions.popitem()
                    action()
                except KeyError:
                    break
        finally:
            self._reached = True

    def _reset(self):
        """This is just for testing purposes"""
        self._reached = False
        self._actions = dict()
        for action in self._keep_on_reset:
            self.register(action)


config_ready = _ConfigMilestoneTracker('config_ready')
renderers_ready = _ConfigMilestoneTracker('renderers_ready')
environment_loaded = _ConfigMilestoneTracker('environment_loaded')


def _reset_all():
    """Utility method for the test suite to reset milestones"""
    config_ready._reset()
    renderers_ready._reset()
    environment_loaded._reset()


def _reach_all():
    """Utility method for the test suite to reach all milestones"""
    config_ready.reach()
    renderers_ready.reach()
    environment_loaded.reach()
