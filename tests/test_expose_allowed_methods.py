# -*- coding: utf-8 -*-
import json
import pytest
import tg

from tests.base import TestWSGIController, make_app
from tg.controllers import TGController
from tg.decorators import expose


class AllowedMethodsController(TGController):
    @expose(allowed_methods=["POST"])
    def only_post(self):
        return "posted"

    @expose(allowed_methods=["GET"])
    def only_get(self):
        return "readable"


class TestExposeAllowedMethods(TestWSGIController):
    def setup_method(self):
        TestWSGIController.setup_method(self)
        self.app = make_app(AllowedMethodsController)

    def test_disallowed_method_returns_405(self):
        response = self.app.get("/only_post", status=405)
        assert response.status_code == 405
        assert response.headers["Allow"] == "POST"

    def test_allowed_method_succeeds(self):
        response = self.app.post("/only_post")
        assert response.text == "posted"

    def test_get_request_allows_head_and_lists_header(self):
        response = self.app.post("/only_get", status=405)
        assert response.headers["Allow"] == "GET, HEAD"
        head_response = self.app.head("/only_get", status=200)
        assert head_response.status_code == 200


class StackedMethodsController(TGController):
    @expose()
    @expose(allowed_methods=["POST"])
    @expose("json", allowed_methods=["DELETE"])
    def stacked(self):
        return getattr(tg.request, "method", "UNKNOWN").lower()


class TestStackedExposeAllowedMethods(TestWSGIController):
    def setup_method(self):
        TestWSGIController.setup_method(self)
        self.app = make_app(StackedMethodsController)

    def test_methods_from_multiple_expose_are_merged(self):
        post_response = self.app.post("/stacked")
        assert "post" in post_response.text
        delete_response = self.app.delete("/stacked")
        assert "delete" in delete_response.text
        self.app.get("/stacked", status=405)


class ParentAllowedMethodsController(TGController):
    @expose("json", allowed_methods=["GET"])
    def endpoint(self):
        return dict(message="parent")


class ChildAllowedMethodsController(ParentAllowedMethodsController):
    @expose(inherit=True, allowed_methods=["POST"])
    def endpoint(self):
        return dict(message="child")


class TestInheritedExposeAllowedMethods(TestWSGIController):
    def setup_method(self):
        TestWSGIController.setup_method(self)
        self.app = make_app(ChildAllowedMethodsController)

    def test_inherited_methods_are_merged(self):
        get_data = json.loads(self.app.get("/endpoint").text)
        assert get_data["message"] == "child"
        self.app.head("/endpoint", status=200)
        post_data = json.loads(self.app.post("/endpoint").text)
        assert post_data["message"] == "child"
        self.app.put("/endpoint", status=405)


class CustomDispatchController(TGController):
    """Dispatches to a method that was never exposed, like a JSON-RPC
    controller that picks the method to call from the request body."""

    def _dispatch(self, state, remainder=None):
        state.set_action(self._rpc_call, [])
        state.set_params({"value": "called"})
        return state

    def _rpc_call(self, value):
        return value


class TestCustomDispatchToUnexposedAction(TestWSGIController):
    def setup_method(self):
        TestWSGIController.setup_method(self)
        self.app = make_app(CustomDispatchController)

    def test_unexposed_action_is_not_method_restricted(self):
        assert self.app.get("/").text == "called"
        assert self.app.post("/").text == "called"
