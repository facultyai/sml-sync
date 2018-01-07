
import logging

import daiquiri

from .cli import parse_command_line
from .ssh import get_ssh_details
from .pubsub import PubSubExchange
from .ui import View
from .controller import Controller


def main():
    try:
        configuration = parse_command_line()
    except Exception as e:
        print(e)
        exit(1)

    daiquiri.setup(
        level=logging.ERROR if configuration.debug else logging.INFO,
        outputs=[daiquiri.output.File('/tmp/sml-sync.log')]
    )

    exchange = PubSubExchange()
    exchange.start()
    view = View(configuration, exchange)
    view.start()

    with get_ssh_details(configuration) as ssh_details:
        controller = Controller(configuration, ssh_details, view, exchange)
        controller.start()

        # Run until the controller stops
        controller.join()

    view.stop()
    exchange.stop()
    exchange.join()


main()
