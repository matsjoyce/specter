#!/usr/bin/env python3
"""
Yet Another Python Little Man Computer written in Python 3
Copyright (C) 2013  Matthew Joyce matsjoyce@gmail.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import assembler
import runner

__author__ = "Matthew Joyce"
__copyright__ = "Copyright 2013"
__credits__ = ["Matthew Joyce"]
__license__ = "GPL3"
__version__ = "1.1.0"
__maintainer__ = "Matthew Joyce"
__email__ = "matsjoyce@gmail.com"
__status__ = "Development"

if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                         epilog="""
yaplmc Copyright (C) 2014  Matthew Joyce
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions. Type `yaplmc --licence` for details.
                                         """.strip())
    arg_parser.add_argument("-d", "--debug", help="debug level"
                            " (repeat for more info, 2 is the max)",
                            action="count", default=0)
    arg_parser.add_argument("-f", "--file", help="lmc file",
                            default=None)
    arg_parser.add_argument("-l", "--licence", help="display licence",
                            action="store_true")
    arg_parser.add_argument("-V", "--version", help="display version",
                            action="store_true")

    args_from_parser = arg_parser.parse_args()

    if args_from_parser.licence:
        print(__doc__.strip())
        exit()
    elif args_from_parser.version:
        print("yaplmc", __version__)
        exit()

    if args_from_parser.file:
        code = open(args_from_parser.file).read()
    else:
        code = open(input("Filename: ")).read()
    print("Assembling...")
    assem = assembler.Assembler()
    assem.update_code(code)
    assem.assemble()
    if assem.problems():
        print("\n".join(i.show(code.splitlines()) for i in assem.problems()))
    if assem.in_error:
        print("Assembly failed")
        exit(1)
    print("Assembly succeeded")
    machine_code, code_length = (assem.machine_code,
                                 assem.machine_code_length)
    if args_from_parser.debug:
        print("Code:")
        print(" ".join(map(str, machine_code[:code_length])))
    print("Loading code...")
    run = runner.Runner(lambda x: print(">>>", x))
    run.load_code(assem)
    print("Running...")
    while run.halt_reason != runner.HaltReason.hlt:
        if args_from_parser.debug >= 2:
            print("Memory:")
            print(*[i.value for i in run.memory])
            print("Executing instruction {:03} at {:03}".format(run.memory[run.counter].value, run.counter))
        try:
            run.next_step()
        except RuntimeError as e:
            print("Error", e.args[0])
        if run.halt_reason == runner.HaltReason.input:
            run.give_input(int(input("<<< ")))
        if args_from_parser.debug >= 1:
            print(run.hint)
