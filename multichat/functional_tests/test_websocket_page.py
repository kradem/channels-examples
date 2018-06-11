from .base import FunctionalTest


class WebsocketPageTest(FunctionalTest):

    def test_websocket(self):
        # Moe signs up
        self.create_cookie_and_go_to_page('moews@email.com')
