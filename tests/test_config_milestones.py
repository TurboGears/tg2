from tg.configuration.milestones import _ConfigMilestoneTracker


class Action:
    called = 0
    def __call__(self):
        self.called += 1


class TestMilestones(object):
    def setup(self):
        self.milestone = _ConfigMilestoneTracker('test_milestone')

    def test_multiple_registration(self):
        a = Action()
        self.milestone.register(a)
        self.milestone.register(a)
        self.milestone.register(a)

        self.milestone.reach()
        assert a.called == 1

    def test_register_after_reach(self):
        a = Action()

        self.milestone.reach()
        self.milestone.register(a)
        assert a.called == 1

    def test_call_all(self):
        a = Action()
        a2 = Action()
        a3 = Action()

        self.milestone.register(a)
        self.milestone.register(a2)
        self.milestone.register(a3)

        self.milestone.reach()
        assert a.called == a2.called == a3.called == 1

    def test_register_func_unique(self):
        called = []
        def f():
            called.append(True)

        self.milestone.register(f)
        self.milestone.register(f)

        self.milestone.reach()
        assert len(called) == 1



