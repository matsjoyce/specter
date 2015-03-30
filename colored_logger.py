import logging
import re
import traceback
import difflib


def log_record_factory(name, level, fn, lno, msg, args, exc_info, func=None,
                       sinfo=None, old_log_record_factory=logging.getLogRecordFactory(), **kwargs):
    """Allow str.format style for log messages"""
    msg = str(msg)
    if args:
        try:
            msg = msg % args
        except TypeError:
            msg = msg.format(*args)

    return old_log_record_factory(name, level, fn, lno, msg, (), exc_info,
                                  func, sinfo, **kwargs)

logging.setLogRecordFactory(log_record_factory)


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)
exc_file_line_re = re.compile("  File (?P<file>\".*?\"), line (?P<line>\d+)(, in (?P<function>[\w<>]+))?")
color_re = re.compile("\033\[1;\\d*?m")


def colorise(s, col, bg=False):
    if bg:
        col += 10
    return "\033[1;%dm%s\033[1;m" % (col, s)


def decolorise(s):
    return color_re.sub("", s)


class ColoredFormatter(logging.Formatter):
    def __init__(self, use_color=True, *args, **kwargs):
        if not kwargs:
            kwargs = {"fmt": "{message} [{name}:{funcName} - {asctime} -"
                             " {filename}:{lineno}]",
                      "datefmt": "%H:%M:%S"}
        super().__init__(*args, **kwargs)
        self.use_color = use_color
        self.levels = {logging.DEBUG: (BLUE, "D", "", " ->"),
                       logging.INFO: (GREEN, "I", "", "==>"),
                       logging.WARNING: (YELLOW, "W", "WARNING: ", "==>"),
                       logging.ERROR: (RED, "E", "ERROR: ", "==>"),
                       logging.CRITICAL: (RED, "C", "CRITICAL: ", "==>")}

    def format_traceback(self, exc):
        if exc.__cause__:
            yield from self.format_traceback(exc.__context__)
            yield ""
            yield colorise("The above exception was the direct cause of the following exception:", YELLOW)
            yield ""
        if exc.__context__ and not exc.__suppress_context__:
            yield from self.format_traceback(exc.__context__)
            yield ""
            yield colorise("During handling of the above exception, another exception occurred:", YELLOW)
            yield ""

        yield colorise("Traceback", RED) + colorise(" (most recent call last):", WHITE)
        for fname, lineno, function, text in traceback.extract_tb(exc.__traceback__):
            line = ""
            line += colorise("  File ", WHITE) + colorise("\"" + fname + "\"", BLACK)
            line += colorise(", line ", WHITE) + colorise(lineno, BLACK)
            if function is not None:
                line += colorise(", in ", WHITE) + colorise(function, YELLOW)
            yield line
            yield "    " + text
        yield colorise(exc.__class__.__name__ + (": " if exc.args else ""), RED) + colorise(" ".join(exc.args), WHITE)

    def format(self, record):
        color, letter, name, arrow = self.levels[record.levelno]

        msg = self._fmt.format(message=str(record.msg),
                               asctime=self.formatTime(record, self.datefmt),
                               **record.__dict__)

        text = colorise(arrow + " " + name, color) + colorise(msg, WHITE)

        if record.exc_info is not None:
            text += "\n" + "\n".join(self.format_traceback(record.exc_info[1])) + "\n"

        if not self.use_color:
            text = letter + decolorise(text)
        return text
