from .base import FunctionalTest


class WebsocketPageTest(FunctionalTest):

    def test_static(self):
        # Moe signs up
        self.browser.get(self.server_url)
        import pdb; pdb.set_trace()
