import logging
import sys
from colorama import Fore, Style


LOG_COLORS = {
    'DEBUG': '%sDEBU%s' % (Fore.GREEN, Style.RESET_ALL),
    'INFO': '%sINFO%s' % (Fore.BLUE, Style.RESET_ALL),
    'WARNING': '%sWARN%s' % (Fore.YELLOW, Style.RESET_ALL),
    'ERROR': '%sERRO%s' % (Fore.RED, Style.RESET_ALL),
    'CRITICAL': '%sCRIT%s' % (Fore.RED, Style.RESET_ALL),
}


class ColoredFormatter(logging.Formatter):
    NAME_MAX_LEN = 8

    def __init__(self, fmt, datefmt):
        if sys.version_info > (3, 2):
            super(ColoredFormatter, self).__init__(fmt, datefmt, "%")
        elif sys.version_info > (2, 7):
            super(ColoredFormatter, self).__init__(fmt, datefmt)

    def format(self, record):
        if record.levelname in LOG_COLORS:
            record.levelname = LOG_COLORS[record.levelname]

        record.name = ("{:^" + str(self.NAME_MAX_LEN) + "}").format(record.name)

        # Truncating the name to make sure it is below 8 characters
        if len(record.name) > self.NAME_MAX_LEN:
            record.name = record.name[0:self.NAME_MAX_LEN]

        if sys.version_info > (2, 7):
            message = super(ColoredFormatter, self).format(record)
        else:
            message = logging.Formatter.format(self, record)

        return message
