import os

instructions = {"ADD", "SUB", "STA", "LDA", "BRA", "BRZ", "BRP", "INP",
                "OUT", "HLT", "DAT"}

eightspaces = " " * 8
fourspaces = " " * 4


def check(lines):
    errors = []
    no_ending_nl = False
    if not lines[-1].endswith("\n"):
        no_ending_nl = True
        lines[-1] += "\n"

    for lineno, line in enumerate(lines):
        if line.startswith("#"):
            if not line.startswith("# "):
                errors.append((lineno, "comment does not begin with '# '"))
                continue
            continue
        if line.strip().startswith("#"):
            if not line.strip().startswith("# "):
                errors.append((lineno, "comment does not begin with '# '"))
                continue
            if not line.startswith(eightspaces + fourspaces + eightspaces) \
               or line[20] != "#":
                errors.append((lineno, "continuing comment should be "
                               "padded by twenty spaces"))
                continue
            if line[20] != "#":
                errors.append((lineno, "continuing comment should be "
                               "padded by twenty spaces"))
                continue
            continue
        if line == "\n":
            continue
        if line[-2].isspace():
            errors.append((lineno, "line ends with whitespace"))
            continue
        sline = line.split()
        if sline[0].upper() in instructions:
            if not line.startswith(eightspaces):
                errors.append((lineno, "line with no label should be"
                               " indented by 8 spaces"))
                continue
            if sline[0].upper() != sline[0]:
                errors.append((lineno, "mnemonics should be uppercase"))
                continue
        else:
            if line[0].isspace():
                errors.append((lineno, "line with label begins with space"))
                continue
            elif not line.startswith("{:<8}".format(sline[0])):
                errors.append((lineno, "label not padded to 8 spaces"))
                continue
            sline = sline[1:]
        nline = line[8:]
        if not len(sline) or sline[0].upper() not in instructions:
            errors.append((lineno, "mnemonic missing"))
            continue
        else:
            if sline[0].upper() != sline[0]:
                errors.append((lineno, "mnemonics should be uppercase"))
                continue
        if len(sline) > 1:
            if not nline.startswith(sline[0]):
                print(repr(sline[0]), repr(nline))
                errors.append((lineno, "mnemonic not padded to 4 spaces"))
                continue
        else:
            continue  # Done line containing no comment or arg
        sline = sline[1:]
        nline = nline[4:]
        if nline.strip().startswith("#"):
            if not nline.startswith(eightspaces + "#"):
                errors.append((lineno, "comment not padded enough"))
                continue
            if not nline.strip().startswith("# "):
                errors.append((lineno, "comment does not begin with '# '"))
                continue
        else:
            if nline[0].isspace():
                errors.append((lineno, "mnemonic padded too much"))
                continue
            if len(sline) > 1:
                if not nline.startswith("{:<8}".format(sline[0])):
                    errors.append((lineno, "argument not padded enough"))
                    continue
            else:
                continue  # Done line containing arg or comment
        sline = sline[1:]
        nline = nline[8:]
        if nline[0].isspace():
            errors.append((lineno, "argument padded too much"))
            continue
        if not nline.startswith("#"):
            errors.append((lineno, "too many arguments"))
            continue
        if not nline.startswith("# "):
            errors.append((lineno, "comment does not begin with '# '"))
            continue

    if no_ending_nl:
        errors.append((len(lines) - 1, "file does not end with newline"))

    if len(lines) > 1 and lines[-1] == "\n":
        errors.append((len(lines) - 1, "file ends with too many newlines"))
    return errors


def process_file(fname):
    if os.path.isfile(fname):
        if fname.endswith(".lmc"):
            data = open(fname).readlines()
            errs = check(data)
            if errs:
                print(fname)
                perrs = []
                for lineno, e in errs:
                    perrs.append("{}: {}".format(lineno + 1, e))
                    perrs.append("\t\"{}\"".format(data[lineno].replace("\n",
                                                                        "")))
                print("\n".join(perrs))
    else:
        for i in os.listdir(fname):
            process_file(os.path.join(fname, i))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.argv.append(os.curdir)
    process_file(sys.argv[1])
