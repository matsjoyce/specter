import abc
import string

# Tuples in the form (numeric code, short description, long description)
# from wiki
MNEMONIC_INFO = {
    "HLT": ("000", "Halt              ", "Stop the processor. The program sh"
            "ould always end with this."),
    "ADD": ("1xx", "Add               ", "Add the contents of address `xx` t"
            "o the accumulator"),
    "SUB": ("2xx", "Subtract          ", "Subtract the contents of address `"
            "xx` from the accumulator"),
    "STA": ("3xx", "Store             ", "Store the value of the accumulator"
            " to address `xx`"),
    "LDA": ("5xx", "Load              ", "Load the value at address `xx` to "
            "the accumulator"),
    "BRA": ("6xx", "Branch            ", "Unconditionally change the mnemuc"
            "tion counter to `xx`"),
    "BRZ": ("7xx", "Branch if zero    ", "Change the mnemuction counter to "
            "`xx` if the accumulator is `0`"),
    "BRP": ("8xx", "Branch if positive", "Change the mnemuction counter to "
            "`xx` if the accumulator is `0` or greater [1]"),
    "INP": ("901", "Input             ", "Sets the accumulator to the value "
            "given by the user"),
    "OUT": ("902", "Output            ", "Outputs the value of the accumulat"
            "or"),
    "DAT": ("xxx", "Data declaration  ", "Sets the value at its address to `"
            "xxx`. Defaults to `0` [2]")
    }


class Position:
    def __init__(self, lineno, start_index, end_index):
        self.lineno = lineno
        self.start_index = start_index
        self.end_index = end_index
        self.length = end_index - start_index

    def get_line(self, codelines):
        return codelines[self.lineno]

    def get_descriptive_line(self, codelines, fmt="On line {}:"):
        out = [fmt.format(self.lineno + 1)]
        out.append("    " + self.get_line(codelines))
        out.append("    " + " " * self.start_index + "^" * self.length)
        return "\n".join(out)


class CodeProblem:
    def __init__(self, msg, position, name, extra=None):
        self.msg = msg
        self.position = position
        self.name = name
        if isinstance(extra, list):
            self.extra = extra
        elif extra is None:
            self.extra = []
        else:
            self.extra = [extra]

    def set_info(self, textbox):
        pass

    def show(self, codelines):
        out = """{}
{}: {}""".format(self.position.get_descriptive_line(codelines), self.name, self.msg)
        for msg, pos in self.extra:
            out += "\n\n" + pos.get_descriptive_line(codelines, msg + " on line {}:")
        return out


class CodeError(CodeProblem):
    pass


class InvalidSyntax(CodeError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="Invalid Syntax", **kwargs)


class CodeWarning(CodeProblem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="Warning", **kwargs)


class Token:
    def __init__(self, text, position, problems=None, style="text"):
        self.text = text
        self.position = position
        self.style = style
        self.problems = problems or []

    @property
    def in_error(self):
        return any(isinstance(problem, CodeError) for problem in self.problems)

    def show_problems(self, codelines):
        return "\n\n".join(problem.show(codelines) for problem in self.problems)

    def __repr__(self):
        return "<{}({}) {!r}>".format(self.__class__.__name__, self.style,
                                      self.text)

    def set_info(self, textbox):
        pass


class Comment(Token):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="comment", **kwargs)


class Mnemonic(Token):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="mnemonic", **kwargs)
        self.mnemonic = self.text.upper()
        self.numeric, self.short, self.long = MNEMONIC_INFO[self.mnemonic]
        self.arg = None

    def link_arg(self, arg):
        self.arg = arg

    def machine_instruction(self):
        if self.takes_arg:
            arg = self.arg.resolve() if self.arg else None
            if self.numeric == "xxx":
                arg = arg or 0
            if arg is None:
                return None
            return int(self.numeric.replace("x", "") + str(arg).zfill(2))
        else:
            return int(self.numeric)

    @property
    def takes_arg(self):
        return "x" in self.numeric

    @property
    def needs_arg(self):
        return "x" in self.numeric and not self.numeric == "xxx"  # DAT has an optional arg

    def set_info(self, textbox):
        super().set_info(textbox)


class Label(Token):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="label", **kwargs)
        self.address = None

    def set_info(self, textbox):
        super().set_info(textbox)


class Argument(Token, abc.ABC):
    def __init__(self, *args, **kwargs):
        abc.ABC.__init__(self)
        Token.__init__(self, *args, **kwargs)

    @abc.abstractmethod
    def resolve(self):
        pass


class LabelRef(Argument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="label", **kwargs)
        self.label = None

    def link_label(self, label):
        self.label = label

    def set_info(self, textbox):
        super().set_info(textbox)

    def resolve(self):
        return self.label.address


class Number(Argument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="number", **kwargs)
        self.value = int(self.text)
        self.capped_value = (1000 if self.value < 0 else 0) + self.value

    def resolve(self):
        return self.capped_value


class Assembler:
    def __init__(self):
        self.tokenised = self.parsed = self.assembled = False

    def update_code(self, code):
        if isinstance(code, str):
            self.code = code.split("\n")
        else:
            self.code = list(code)
        self.tokenised = self.parsed = self.assembled = False

    def tokenise(self):
        if self.tokenised:
            return self.tokenised_code
        self.tokenised_code = []
        for line in self.code:
            if line.endswith("\n"):
                line = line[:-1]
            line = list(line)
            tok_line = []
            c = line.pop(0) if line else ""
            while c:
                if c == "#":
                    tok_line.append("".join([c] + line))
                    break
                elif c.isalnum() or c == "-":
                    building = []
                    while (c.isalnum() or c == "-"):
                        building.append(c)
                        c = line.pop(0) if line else ""
                    tok_line.append("".join(building))
                else:
                    building = []
                    while c and not c.isalnum() and c not in "-#":
                        building.append(c)
                        c = line.pop(0) if line else ""
                    tok_line.append("".join(building))
            self.tokenised_code.append(tok_line)
        self.tokenised = True
        return self.tokenised_code

    def parse(self):
        if self.parsed:
            return self.parsed_code
        self.tokenise()
        self.parsed_code = []
        self.labels = {}
        for lineno, line in enumerate(self.tokenised_code):
            parsed_line = []
            found_label = found_mnem = found_arg = False
            start_index = end_index = 0
            for token in line:
                start_index = end_index
                end_index = start_index + len(token)
                position = Position(lineno, start_index, end_index)
                problems = []
                if token and (token[0].isalnum() or token[0] == "-"):
                    if token.upper() in MNEMONIC_INFO:
                        if found_mnem:
                            problems.append(InvalidSyntax("Multiple mnemonics on one line", position))
                        if not token.isupper():
                            problems.append(CodeWarning("Mnemonics should be uppercase", position))
                        parsed_line.append(Mnemonic(token, position, problems=problems))
                        found_mnem = True
                    elif found_mnem:
                        if found_arg:
                            problems.append(InvalidSyntax("Multiple arguments for mnemonic", position))
                        try:
                            int(token)
                        except ValueError:
                            parsed_line.append(LabelRef(token, position, problems=problems))
                        else:
                            if int(token) > 499:
                                problems.append(InvalidSyntax("Number too large (> 499)", position))
                            if int(token) < -500:
                                problems.append(InvalidSyntax("Number too small (< -500)", position))
                            parsed_line.append(Number(token, position, problems=problems))
                        found_arg = True
                    else:
                        if found_label:
                            problems.append(InvalidSyntax("Multiple labels for one line", position))
                        if token in self.labels:
                            original_pos = self.labels[token][1].position
                            problems.append(InvalidSyntax("Duplicate label", position, extra=("First defined", original_pos)))
                        l = Label(token, position, problems=problems)
                        self.labels[token] = (None, l)
                        parsed_line.append(l)
                        found_label = True
                elif token.startswith("#"):
                    parsed_line.append(Comment(token, position, problems=problems))
                else:
                    parsed_line.append(Token(token, position, problems=problems))
            self.parsed_code.append(parsed_line)
        # Check for missing labels etc. which can't be checked above
        for line in self.parsed_code:
            for token in line:
                if isinstance(token, LabelRef):
                    if token.text not in self.labels:
                        token.problems.append(InvalidSyntax("Label not defined", token.position))
                    else:
                        token.link_label(self.labels[token.text][1])
                elif isinstance(token, Mnemonic):
                    found_arg = False
                    for arg in line:
                        if isinstance(arg, Argument):
                            found_arg = True
                            break
                    if found_arg:
                        if token.takes_arg:
                            token.link_arg(arg)
                        elif not token.needs_arg:
                            token.problems.append(InvalidSyntax("Mnemonic does not take an argument", token.position))
                    else:
                        if token.needs_arg:
                            token.problems.append(InvalidSyntax("Mnemonic takes an argument", token.position))
        self.in_error = any(token.in_error for line in self.parsed_code for token in line)
        self.parsed = True
        return self.parsed_code

    def problems(self):
        return sum((token.problems for line in self.parsed_code for token in line), [])

    def set_addresses(self):
        address = 0
        for line in self.parsed_code:
            for token in line:
                if isinstance(token, Label):
                    token.address = address
            address += any(isinstance(token, Mnemonic) for token in line)

    def assemble(self):
        if self.assembled:
            return self.machine_code
        self.parse()
        self.machine_code = []
        if not self.in_error:
            self.set_addresses()
            for line in self.parsed_code:
                for token in line:
                    if isinstance(token, Mnemonic):
                        self.machine_code.append(token.machine_instruction())
        self.machine_code_length = len(self.machine_code)
        while len(self.machine_code) < 100:
            self.machine_code.append(0)
        self.assembled = True
        return self.machine_code


if __name__ == "__main__":
    import sys
    import pprint
    import difflib

    code = open(sys.argv[1]).read()

    a = Assembler()
    d = difflib.Differ()

    print("=" * 25, "Tokenising", "=" * 25)

    a.update_code(code)
    a.tokenise()

    pprint.pprint(a.tokenised_code)

    recode = "\n".join("".join(line) for line in a.tokenised_code)
    if recode != code:
        sys.stdout.writelines(d.compare(code.splitlines(keepends=True),
                                        recode.splitlines(keepends=True)))
        print()
    print("Reconstruction succeeded:", recode == code)
    print()

    print("=" * 25, "Parsing", "=" * 25)

    a.parse()

    pprint.pprint(a.parsed_code)

    rerecode = "\n".join("".join(i.text for i in line) for line in a.parsed_code)
    if rerecode != code:
        sys.stdout.writelines(d.compare(code.splitlines(keepends=True),
                                        recode.splitlines(keepends=True)))
        print()
    print("Reconstruction succeeded:", rerecode == code)
    print()

    print("=" * 25, "Assembling", "=" * 25)

    print(" ".join(map(str, a.assemble())))
    print()

    print("=" * 25, "Problems", "=" * 25)

    print(*[i.show(code.splitlines()) for i in a.problems()])
