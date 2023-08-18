import logging


def configure_logging(debug: bool = False):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s.%(msecs)03d - %(message)s",
        datefmt="%H:%M:%S",
    )
