import abc


class Problem(abc.ABC):
    def __init__(self, cat, msg, position, name=None, extra=None):
        self.cat = cat
        self.msg = msg
        self.position = position
        self.name = name
        if isinstance(extra, list):
            self.extra = extra
        elif extra is None:
            self.extra = []
        else:
            self.extra = [extra]

    @abc.abstractmethod
    def set_interactive(self, tooltip):
        pass

    def show(self, codelines):
        out = """{}
{}: {}""".format(self.position.get_descriptive_line(codelines), self.name, self.msg)
        for msg, tok in self.extra:
            out += "\n\n" + tok.position.get_descriptive_line(codelines, msg + " on line {}:")
        return out


class Error(Problem):
    def __init__(self, *args, **kwargs):
        super().__init__("error", *args, **kwargs)

    def set_interactive(self, tooltip):
        tooltip.error_header("Error" if self.name is None else self.name)
        tooltip.newline()

        tooltip.text(self.msg)
        tooltip.newline()
        tooltip.newline()

        for msg, token in self.extra:
            tooltip.text(msg + ":")
            tooltip.goto_token(token)
            tooltip.newline()


class Warning(Problem):
    def __init__(self, *args, **kwargs):
        super().__init__("warning", *args, **kwargs)

    def set_interactive(self, tooltip):
        tooltip.warning_header("Warning" if self.name is None else self.name)
        tooltip.newline()

        tooltip.text(self.msg)
        tooltip.newline()
        tooltip.newline()

        for msg, token in self.extra:
            tooltip.text(msg + ":")
            tooltip.goto_token(token)
            tooltip.newline()


class SyntaxError(Error):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="Syntax Error", **kwargs)


class SemanticError(Error):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="Semantic Error", **kwargs)


class RuntimeWarning(Warning):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="Runtime Warning", **kwargs)


class StyleWarning(Warning):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="Style Warning", **kwargs)
