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

__author__ = "Matthew Joyce"
__copyright__ = "Copyright 2013"
__credits__ = ["Matthew Joyce"]
__license__ = "GPL3"
__version__ = "1.0.0"
__maintainer__ = "Matthew Joyce"
__email__ = "matsjoyce@gmail.com"
__status__ = "Development"

instructions = {"ADD": "1xx",
                "SUB": "2xx",
                "STA": "3xx",
                "LDA": "5xx",
                "BRA": "6xx",
                "BRZ": "7xx",
                "BRP": "8xx",
                "INP": "901",
                "OUT": "902",
                "HLT": "000",
                "DAT": None
                }


def add_arg(memo, arg, lineno, line):
    instr = instructions[memo]
    if arg:
        if len(arg) > 2 or not arg.isdigit():
            raise SyntaxError("Bad argument on line {}: '{}'"
                              .format(lineno + 1, arg))
    if arg:
        arg = arg.zfill(2)
    if "xx" in instr:
        if not arg:
            raise SyntaxError("Instruction on line {} "
                              "takes an argument: '{}'".format(lineno + 1,
                                                               memo))
        return instr.replace("xx", arg)
    if arg:
        raise SyntaxError("Instruction on line {} "
                          "has no argument: '{}'".format(lineno + 1, memo))
    return instr


def assemble(lines):
    labels = {}
    instrs = []
    # Turn list of lines into list of (instruction, argument)
    i = 0
    for lineno, origline in enumerate(lines):
        line = origline
        if "#" in line:
            line = line[:line.find("#")]
        line = line.strip()
        if not line:
            continue
        line = line.split()
        if len(line) == 3:
            label, instr, arg = line
        elif len(line) == 2:
            if line[0] in instructions:
                instr, arg = line
                label = None
            else:
                label, instr = line
                arg = None
        elif len(line) == 1:
            instr = line[0]
            label = arg = None
        else:
            raise SyntaxError("Invalid line {}: '{}'".format(lineno + 1,
                                                             origline))
        instr = instr.upper()
        if instr not in instructions:
            raise SyntaxError("Invalid mnemonic at line {}:"
                              " '{}'".format(lineno + 1, instr))
        if label:
            if label in labels:
                orig_line = instrs[labels[label]][3] + 1
                raise SyntaxError("Duplicate label '{}' "
                                  "on lines {} and {}".format(label,
                                                              lineno + 1,
                                                              orig_line))
            labels[label] = i
        instrs.append((instr, arg, origline, lineno))
        i += 1
    # resolve arguments and assemble
    assembled = []
    for instr, arg, line, lineno in instrs:
        if instr == "DAT":
            if arg:
                if set(arg) - set("1234567890-") \
                   or int(arg) not in range(-500, 500):
                    raise SyntaxError("Bad argument on line {}: '{}'"
                                      .format(lineno + 1, arg))
                i = int(arg)
                arg = 1000 + i if i < 0 else i
            else:
                arg = 0
            assembled.append(arg)
        else:
            if arg in labels:
                arg = str(labels[arg])
            assembled.append(int(add_arg(instr, arg, lineno, line)))
    l = len(assembled)
    while len(assembled) != 100:
        assembled.append(0)
    return assembled, l

DEBUG_LEVEL_NONE = 0
DEBUG_LEVEL_LOW = 1
DEBUG_LEVEL_MEDIUM = 2
DEBUG_LEVEL_HIGH = 3

HALT_REASON_HLT = 0
HALT_REASON_INP = 1
HALT_REASON_STEP = 2


class Runner:
    def __init__(self, program, get_input=None, halt_for_inp=False,
                 give_output=None, debug_output=None, debug_level=0):
        self.counter = self.instruction_addr = 0
        self.accumulator = 0
        self.code = program
        self.memory = self.code.copy()
        self.get_input = get_input if get_input else self._get_input
        self.give_output = give_output if give_output else self._give_output
        self.halt_for_inp = halt_for_inp
        self.debug_level = debug_level
        self.unfiltered_debug_output = debug_output or self._debug_output
        self.accumulator_read = False
        self.accumulator_changed = False
        self.memory_changed = set()
        self.memory_read = set()

    def debug_output(self, msg, level):
        if level <= self.debug_level:
            self.unfiltered_debug_output(msg)

    def cap(self, i):
        return (i + 1000) % 1000

    def int_to_complement(self, i):
        return 1000 + i if i < 0 else i

    def int_from_complement(self, i):
        return i - 1000 if i >= 500 else i

    def _get_input(self):
        return int(input("<<< "))

    def _give_output(self, i):
        print(">>>", i)

    def _debug_output(self, i):
        print(i)

    def give_input(self, i):
        self.setaccum(self.cap(i))

    # Below functions are to be used inside next_step, to keep track
    # of what has been read and written

    def readaccum(self):
        self.accumulator_read = True
        return self.accumulator

    def setaccum(self, value):
        self.accumulator = value
        self.accumulator_changed = True

    def readmem(self, addr):
        self.memory_read.add(addr)
        return self.memory[addr]

    def setmem(self, addr, value):
        self.memory[addr] = value
        self.memory_changed.add(addr)

    def next_step(self):
        self.accumulator_read = False
        self.accumulator_changed = False
        self.memory_changed = set()
        self.memory_read = set()
        self.debug_output("Executing next instruction"
                          " at {:03}".format(self.counter), DEBUG_LEVEL_HIGH)
        instruction = self.memory[self.counter]
        self.debug_output("Next instruction is {:03}".format(instruction),
                          DEBUG_LEVEL_MEDIUM)
        memory_str = ", ".join("{}: {:03}".format(i, self.memory[i])
                               for i in range(100))
        self.debug_output("Memory: {}".format(memory_str), DEBUG_LEVEL_MEDIUM)
        self.debug_output("Accumulator: {}".format(self.accumulator),
                          DEBUG_LEVEL_MEDIUM)
        self.debug_output("Counter: {}".format(self.counter),
                          DEBUG_LEVEL_MEDIUM)
        self.instruction_addr = self.counter
        self.counter += 1
        self.debug_output("Incrementing counter to {}".format(self.counter),
                          DEBUG_LEVEL_HIGH)
        addr = instruction % 100
        if addr > 99:
            raise RuntimeError("Invalid memory address")
        if instruction == 0:  # HLT
            self.debug_output("HLT", DEBUG_LEVEL_LOW)
            self.give_output("Done! Coffee break!")
            return HALT_REASON_HLT
        elif instruction < 100:
            raise RuntimeError("Invalid instruction {:03}".format(instruction))
        elif instruction < 200:  # ADD
            memval = self.readmem(addr)
            value = self.cap(self.readaccum() + memval)
            self.debug_output("ADD {:03}: accumulator = {} + {} = {}"
                              .format(addr, self.readaccum(),
                                      memval, value),
                              DEBUG_LEVEL_LOW)
            self.setaccum(value)
        elif instruction < 300:  # SUB
            memval = self.readmem(addr)
            value = self.cap(self.readaccum() - memval)
            self.debug_output("SUB {:03}: accumulator = {} - {} = {}"
                              .format(addr, self.readaccum(),
                                      memval, value),
                              DEBUG_LEVEL_LOW)
            self.setaccum(value)
        elif instruction < 400:  # STA
            self.debug_output("STA {:03}: accumulator = {}"
                              .format(addr, self.readaccum()), DEBUG_LEVEL_LOW)
            self.setmem(addr, self.readaccum())
        elif instruction < 600:  # LDA
            memval = self.readmem(addr)
            self.debug_output("LDA {:03}: value = {}"
                              .format(addr, memval),
                              DEBUG_LEVEL_LOW)
            self.setaccum(memval)
        elif instruction < 700:  # BRA
            self.debug_output("BRA {:03}".format(addr), DEBUG_LEVEL_LOW)
            self.counter = addr
        elif instruction < 800:  # BRZ
            word = "" if self.readaccum() == 0 else " no"
            self.debug_output("BRZ {:03}: accumulator = {}, so{} branch"
                              .format(addr, self.readaccum(), word),
                              DEBUG_LEVEL_LOW)
            if self.readaccum() == 0:
                self.counter = addr
        elif instruction < 900:  # BRP
            word = "" if self.readaccum() < 500 else " no"
            self.debug_output("BRP {:03}: accumulator = {}, so{} branch"
                              .format(addr, self.readaccum(), word),
                              DEBUG_LEVEL_LOW)
            if self.readaccum() < 500:
                self.counter = addr
        elif instruction == 901:  # INP
            self.debug_output("INP", DEBUG_LEVEL_LOW)
            if self.halt_for_inp:
                return HALT_REASON_INP
            else:
                i = self.int_to_complement(self.get_input())
                self.setaccum(self.cap(i))
        elif instruction == 902:  # OUT
            self.debug_output("OUT", DEBUG_LEVEL_LOW)
            self.give_output(self.int_from_complement(self.readaccum()))
        else:
            raise RuntimeError("Invalid instruction {:03}".format(instruction))
        return HALT_REASON_STEP

    def run_to_hlt(self):
        r = HALT_REASON_STEP
        while r == HALT_REASON_STEP:
            r = self.next_step()
        return r

    def reset(self):
        self.counter = 0
        self.accumulator = 0
        self.memory = self.code.copy()
        self.accumulator_read = False
        self.accumulator_changed = False
        self.memory_changed = set()
        self.memory_read = set()

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
                            " (repeat for more info, 3 is the max)",
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
        code = open(args_from_parser.file).read().split("\n")
    else:
        code = open(input("Filename: ")).read().split("\n")
    print("Assembling...")
    try:
        machine_code, code_length = assemble(code)
    except SyntaxError as e:
        print("Assembly failed")
        print("Error:", e.args[0])
        exit(1)
    print("Assembly successful")
    if args_from_parser.debug:
        print("Code:")
        print(" ".join(map(str, machine_code[:code_length])))
    print("Running...")
    runner = Runner(machine_code, debug_level=args_from_parser.debug)
    try:
        runner.run_to_hlt()
    except RuntimeError as e:
        print("Error:", e.args[0])
