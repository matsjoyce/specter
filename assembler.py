import abc
import string
import re

import problems

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
    "BRA": ("6xx", "Branch            ", "Unconditionally change the instruc"
            "tion counter to `xx`"),
    "BRZ": ("7xx", "Branch if zero    ", "Change the instruction counter to "
            "`xx` if the accumulator is `0`"),
    "BRP": ("8xx", "Branch if positive", "Change the instruction counter to "
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

    def __eq__(self, other):
        return (isinstance(other, Position)
                and self.lineno == other.lineno
                and self.start_index == other.start_index
                and self.end_index == other.end_index)

    def __str__(self):
        return "Position({}, {}, {})".format(self.lineno, self.start_index,
                                             self.end_index)

    @classmethod
    def from_string(self, s):
        m = re.match(r"Position\((\d+), (\d+), (\d+)\)", s)
        return Position(*map(int, m.groups()))


class Token:
    def __init__(self, text, position, problems=None, style="text"):
        self.text = text
        self.position = position
        self.style = style
        self.problems = problems or []

    @property
    def in_error(self):
        return any(isinstance(problem, problems.Error) for problem in self.problems)

    def show_problems(self, codelines):
        return "\n\n".join(problem.show(codelines) for problem in self.problems)

    def __repr__(self):
        return "<{}({}) {!r}>".format(self.__class__.__name__, self.style,
                                      self.text)


class InteractiveToken(Token, abc.ABC):
    @abc.abstractmethod
    def set_interactive(self, tooltip):
        pass


class Comment(Token):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="comment", **kwargs)


class Mnemonic(InteractiveToken):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="mnemonic", **kwargs)
        self.mnemonic = self.text.upper()
        self.numeric, self.short, self.long = MNEMONIC_INFO[self.mnemonic]
        self.arg = None
        self.address = None

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

    def set_interactive(self, tooltip):
        tooltip.type("mnemonic")
        tooltip.value(self.text)
        tooltip.newline()

        tooltip.text("Machine instruction:")
        mi = self.machine_instruction()
        if mi is not None and self.takes_arg:
            tooltip.number("{:03}".format(mi))
            tooltip.text("(", space=False)
            tooltip.number(self.numeric, space=False)
            tooltip.text(")")
        else:
            tooltip.number(self.numeric)
        tooltip.newline()

        if self.address is not None:
            tooltip.text("Address:")
            tooltip.number("{:03}".format(self.address))
            tooltip.newline()

        tooltip.newline()
        tooltip.text(self.long)
        tooltip.newline()


class Label(InteractiveToken):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="label", **kwargs)
        self.address = None
        self.refs = []

    def set_interactive(self, tooltip):
        tooltip.type("label definition")
        tooltip.value(self.text)
        tooltip.newline()

        if self.address is not None:
            tooltip.text("Address:")
            tooltip.number("{:03}".format(self.address))
            tooltip.newline()


class Argument(InteractiveToken):
    def __init__(self, *args, **kwargs):
        abc.ABC.__init__(self)
        Token.__init__(self, *args, **kwargs)

    @abc.abstractmethod
    def resolve(self):
        pass


class LabelRef(Argument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="labelref", **kwargs)
        self.label = None

    def link_label(self, label):
        self.label = label
        label.refs.append(self)

    def set_interactive(self, tooltip):
        tooltip.type("label (argument)")
        tooltip.value(self.text)
        tooltip.newline()

        if self.label is not None:
            if self.resolve() is not None:
                tooltip.text("Value:")
                tooltip.number("{:03}".format(self.resolve()))
                tooltip.newline()

            tooltip.text("Defined at:")
            tooltip.goto_token(self.label)
            tooltip.newline()

    def resolve(self):
        return self.label.address if self.label else None


class Number(Argument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style="number", **kwargs)
        self.value = int(self.text)
        self.capped_value = (1000 if self.value < 0 else 0) + self.value

    def resolve(self):
        return self.capped_value

    def set_interactive(self, tooltip):
        tooltip.type("number (argument)")
        tooltip.value(self.text)
        tooltip.newline()

        tooltip.text("Value:")
        tooltip.number("{:03}".format(self.capped_value))
        tooltip.newline()


class Assembler:
    def __init__(self):
        self.tokenised = self.parsed = self.assembled = False

    def update_code(self, code):
        self.raw_code = code
        self.code = code.split("\n")
        self.tokenised = self.parsed = self.assembled = False

    @property
    def tokens(self):
        return [token for line in self.parsed_code for token in line]

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
                tok_problems = []
                if token and (token[0].isalnum() or token[0] == "-"):
                    if token.upper() in MNEMONIC_INFO:
                        if found_mnem:
                            tok_problems.append(problems.SyntaxError("Multiple mnemonics on one line", position))
                        if not token.isupper():
                            tok_problems.append(problems.StyleWarning("Mnemonics should be uppercase", position))
                        parsed_line.append(Mnemonic(token, position, problems=tok_problems))
                        found_mnem = True
                    elif found_mnem:
                        if found_arg:
                            tok_problems.append(problems.SyntaxError("Multiple arguments for mnemonic", position))
                        try:
                            int(token)
                        except ValueError:
                            parsed_line.append(LabelRef(token, position, problems=tok_problems))
                        else:
                            if int(token) > 499:
                                tok_problems.append(problems.SemanticError("Number too large (> 499)", position))
                            if int(token) < -500:
                                tok_problems.append(problems.SemanticError("Number too small (< -500)", position))
                            parsed_line.append(Number(token, position, problems=tok_problems))
                        found_arg = True
                    else:
                        if found_label:
                            tok_problems.append(problems.SyntaxError("Multiple labels for one line", position))
                        if token in self.labels:
                            linked_token = self.labels[token][1]
                            tok_problems.append(problems.SemanticError("Label already defined", position, extra=("First defined", linked_token)))
                        l = Label(token, position, problems=tok_problems)
                        if token not in self.labels:
                            self.labels[token] = (None, l)
                        parsed_line.append(l)
                        found_label = True
                elif token.startswith("#"):
                    parsed_line.append(Comment(token, position, problems=tok_problems))
                else:
                    parsed_line.append(Token(token, position, problems=tok_problems))
            self.parsed_code.append(parsed_line)

        # Check for missing labels etc. which can't be checked above

        self.instructions = []
        for line in self.parsed_code:
            for token in line:
                if isinstance(token, LabelRef):
                    if token.text not in self.labels:
                        token.problems.append(problems.SemanticError("Label not defined", token.position))
                    else:
                        token.link_label(self.labels[token.text][1])
                elif isinstance(token, Mnemonic):
                    token.address = len(self.instructions)
                    self.instructions.append(token)
                    found_arg = False
                    for arg in line:
                        if isinstance(arg, Argument):
                            found_arg = True
                            break
                    if found_arg:
                        if token.takes_arg:
                            token.link_arg(arg)
                        elif not token.needs_arg:
                            token.problems.append(problems.SyntaxError("Mnemonic does not take an argument", token.position))
                    else:
                        if token.needs_arg:
                            token.problems.append(problems.SyntaxError("Mnemonic takes an argument", token.position))
                elif isinstance(token, Label):
                    token.address = len(self.instructions)

        # Extra warnings

        if not any(isinstance(token, Mnemonic) and token.mnemonic == "HLT" for token in self.tokens):
            self.tokens[-1].problems.append(problems.RuntimeWarning("No HLT instruction", self.tokens[-1].position))

        for bra in filter(lambda tok: tok.mnemonic == "BRA", self.instructions):
            if bra.arg and isinstance(bra.arg, (LabelRef, Number)) and bra.arg.resolve() is not None:
                for mnem in self.instructions[bra.arg.resolve():bra.address]:
                    if mnem.mnemonic in ("BRP", "BRZ", "BRA"):
                        break
                else:
                    bra.problems.append(problems.RuntimeWarning("Possible infinite loop", bra.position, extra=("Starting at", self.instructions[bra.arg.resolve()])))

        for instr in filter(lambda tok: tok.mnemonic != "DAT", self.instructions):
            print(instr, instr.arg)
            if instr.arg and isinstance(instr.arg, Number):
                if instr.arg.capped_value >= len(self.instructions):
                    instr.problems.append(problems.RuntimeWarning("Argument does not point at a initialised position", instr.position))
                else:
                    instr.problems.append(problems.StyleWarning("Use labels instead of numerical addresses", instr.position))

        last_dats = []
        for instr in self.instructions:
            if instr.mnemonic == "DAT":
                last_dats.append(instr)
            else:
                for i in last_dats:
                    i.problems.append(problems.StyleWarning("DAT not at end of program", i.position))
                last_dats.clear()

        for instr in filter(lambda tok: tok.mnemonic in ("LDA", "STA"), self.instructions):
            if instr.arg and instr.arg.resolve():
                if 0 <= instr.arg.resolve() < len(self.instructions):
                    i = self.instructions[instr.arg.resolve()]
                    if i.mnemonic != "DAT":
                        instr.problems.append(problems.RuntimeWarning("{} will not {} a DAT instruction".format(instr.mnemonic, "store to" if instr.mnemonic == "STA" else "load from"), instr.position))

        self.in_error = any(token.in_error for token in self.tokens)
        self.parsed = True
        return self.parsed_code

    def problems(self):
        return sum((token.problems for token in self.tokens), [])

    def assemble(self):
        if self.assembled:
            return self.machine_code
        self.parse()
        self.machine_code = []
        if not self.in_error:
            for line in self.parsed_code:
                for token in line:
                    if isinstance(token, Mnemonic):
                        self.machine_code.append(token.machine_instruction())
        self.machine_code_length = len(self.machine_code)
        while len(self.machine_code) < 100:
            self.machine_code.append(0)
        self.assembled = True
        return self.machine_code

    def get_token_at(self, row, col=None):
        self.parse()
        if col is None and isinstance(row, Position):
            line = self.parsed_code[row.lineno]
            for token in line:
                print(token.position, row, token.position == row)
                if token.position == row:
                    return token
        else:
            line = self.parsed_code[row]
            for token in line:
                if token.position.start_index <= col < token.position.end_index:
                    return token
        return None


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

    rerecode = "\n".join("".join(i.text for i in line)
                         for line in a.parsed_code)
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
