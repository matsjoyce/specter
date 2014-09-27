import os

instructions = {"ADD", "SUB", "STA", "LDA", "BRA", "BRZ", "BRP", "INP", "OUT", "HLT", "DAT"}

eightspaces = " " * 8


def check(lines):
    errors = []
    if not lines[-1].endswith("\n"):
        errors.append((len(lines) - 1, "file does not end with newline"))
        lines[-1] += "\n"
    for lineno, line in enumerate(lines):
        if line.startswith("#"):
            if not line.startswith("# "):
                errors.append((lineno, "comment does not begin with '# '"))
                continue
            continue
        if line == "\n":
            continue
        if line.strip() == "\n":
            print(repr(line))
            errors.append((lineno, "blank line has whitespace"))
            continue
        sline = line.split()
        if sline[0] in instructions:
            if not line.startswith(eightspaces):
                errors.append((lineno, "line with no label not indented by 8 spaces"))
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
        if not len(sline) or sline[0] not in instructions:
            errors.append((lineno, "mnemonic missing"))
            continue
        if len(sline) > 1:
            if not nline.startswith(sline[0]):
                print(repr(sline[0]), repr(nline))
                errors.append((lineno, "mnemonic not padded to 4 spaces"))
                continue
        else:
            if not line.endswith(sline[0] + "\n"):
                print(repr(sline[0]), repr(line))
                errors.append((lineno, "line ends with space(s)"))
                continue
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
                    errors.append((lineno, "label not padded enough"))
                    continue
            else:
                if not nline.endswith(sline[0] + "\n"):
                    errors.append((lineno, "line has trailing whitespace"))
                    continue
                continue  # Done line containing arg or comment
        sline = sline[1:]
        nline = nline[8:]
        if nline[0].isspace():
            errors.append((lineno, "label padded too much"))
            continue
        if not nline.startswith("#"):
            errors.append((lineno, "too many args"))
            continue
        if not nline.startswith("# "):
            errors.append((lineno, "comment does not begin with '# '"))
            continue
        if not nline.endswith(sline[-1] + "\n"):
            errors.append((lineno, "line has trailing whitespace"))
            continue
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
    process_file(sys.argv[1])

