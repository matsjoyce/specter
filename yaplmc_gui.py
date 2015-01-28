#!/usr/bin/env python3
"""
Graphical user interface written with tkinter for yaplmc
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

import tkinter
from tkinter import filedialog as fdialog, scrolledtext as stext, simpledialog
import yaplmc
import math
from functools import partial

CHANGED = "#E00"
CHANGEDN = "#C00"
READ = "#EE0"
READN = "#CC0"
INTR = "#0A0"
INTRN = "#080"
DEFAULT = "white"
DEFAULTN = "#DDD"


class MemoryDisplay(tkinter.Frame):
    def __init__(self, root, setmem, rows=5):
        super().__init__(root)
        tkinter.Label(self, text="Memory").grid(row=0, column=1,
                                                columnspan=rows * 2)
        self.setmem = setmem
        self.rows = rows
        self.per_thing = 100 // rows
        self.memory_nums = []
        self.memorys = []
        self.mem_vars = []
        self.updatingmem = True
        for i in range(100):
            col = int(math.floor(i / self.per_thing))
            row = i % self.per_thing + 1

            mn = tkinter.Entry(self, width=2, bg=DEFAULT, borderwidth=0)
            mn.grid(row=row, column=col * 2)
            mn.insert(0, str(i).zfill(2))
            self.memory_nums.append(mn)
            mn["state"] = "readonly"

            var = tkinter.StringVar(value="000")
            vcmd = self.register(partial(self.changed, i)), "%P"
            m = tkinter.Entry(self, width=3, bg=DEFAULT, borderwidth=0,
                              textvariable=var, vcmd=vcmd, validate="key")
            m.grid(row=row, column=col * 2 + 1)
            self.memorys.append(m)
            self.mem_vars.append(var)
        self.updatingmem = False

    def changed(self, addr, num):
        if self.updatingmem:
            return True
        print("changed", addr, num, self)
        if not num.isdigit() or int(num) not in range(1000):
            return False
        return self.setmem(addr, int(num))

    def update_memory(self, mem):
        self.updatingmem = True
        for i, m in enumerate(mem):
            self.mem_vars[i].set(str(m).zfill(3))
        self.updatingmem = False

    def set_colors(self, mem_changed, mem_read, instr):
        for i in range(100):
            self.memory_nums[i]["readonlybackground"] = DEFAULTN
            self.memorys[i]["bg"] = DEFAULT
        for i in mem_read:
            self.memory_nums[i]["readonlybackground"] = READN
            self.memorys[i]["bg"] = READ
        for i in mem_changed:
            self.memory_nums[i]["readonlybackground"] = CHANGEDN
            self.memorys[i]["bg"] = CHANGED
        self.memory_nums[instr]["readonlybackground"] = INTRN
        self.memorys[instr]["bg"] = INTR


class AssembleGUI(simpledialog.Dialog):
    def __init__(self, f=None, parent=None):
        self.f = f
        super().__init__(parent)

    def get_file(self):
        l = tkinter.Label(self.root, text="Waiting for file...",
                          padx=10, pady=10)
        l.pack()
        f = fdialog.askopenfile()

        l.destroy()
        return f

    def body(self, root):
        self.root = root
        self.title("yaplmc")

        if self.f is None:
            f = self.get_file()
        else:
            f = open(self.f)
        if f is None:
            exit(0)

        self.fname = f.name
        self.title("yaplmc - " + self.fname)

        code = f.read().split("\n")

        try:
            self.code, code_length = yaplmc.assemble(code)
        except SyntaxError as e:
            self.code = None
            tkinter.Label(self.root, text="Assembly failed!\nError:").pack()

            t = tkinter.Text(self.root)
            t.insert(tkinter.END, e.args[0])
            t.pack()
        else:
            tkinter.Label(self.root, text="Assembly succeeded!\nCode:").pack()

            t = tkinter.Text(self.root)
            code = " ".join(str(i).zfill(3) for i in self.code[:code_length])
            t.insert(tkinter.END, code)
            t.pack()

    def buttonbox(self):
        box = tkinter.Frame(self)

        if self.code:
            b = tkinter.Button(box, text="Run", command=self.cancel)
            b.pack(side=tkinter.LEFT)
        b = tkinter.Button(box, text="Exit", command=self.cancel)
        b.pack(side=tkinter.LEFT)

        self.bind("<Return>", self.ok if self.code else self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()


def get_assembled_code(f, r):
    a = AssembleGUI(f, r)
    return (a.code, a.fname) if hasattr(a, "code") else (None, None)


class RunGUI:
    def __init__(self):
        self.root = tkinter.Tk()
        self.root.title("yaplmc")

        self.getting_inp = False
        self.run_to_halt = False

        # Top row of buttons

        self.button_frame = tkinter.Frame(self.root)
        self.button_frame.grid(row=0, column=0, columnspan=2)

        self.run_to_hlt_btn = tkinter.Button(self.button_frame,
                                             text="Run to halt",
                                             command=self.run_to_hlt, width=10)
        self.run_to_hlt_btn.grid(row=0, column=0)

        self.run_step_btn = tkinter.Button(self.button_frame,
                                           text="Run one step",
                                           command=self.next_step, width=10)
        self.run_step_btn.grid(row=0, column=1)

        self.reset_btn = tkinter.Button(self.button_frame, text="Pause",
                                        command=self.pause, width=10)
        self.reset_btn.grid(row=0, column=2)

        self.reset_btn = tkinter.Button(self.button_frame, text="Reset",
                                        command=self.reset, width=10)
        self.reset_btn.grid(row=0, column=3)

        self.exit_btn = tkinter.Button(self.button_frame, text="Exit",
                                       command=self.exit, width=10)
        self.exit_btn.grid(row=0, column=4)

        # Left row of inputs

        self.control_frame = tkinter.Frame(self.root)
        self.control_frame.grid(row=1, column=0, sticky="n")

        tkinter.Label(self.control_frame, text="Accumulator:").grid(row=0,
                                                                    column=0,
                                                                    sticky="w")

        self.accumulator = tkinter.Listbox(self.control_frame, setgrid=True,
                                           height=1, width=5)
        self.accumulator.grid(row=0, column=1)
        self.accumulator.insert(tkinter.END, 0)

        tkinter.Label(self.control_frame, text="Counter:").grid(row=1,
                                                                column=0,
                                                                sticky="w")

        self.counter = tkinter.Listbox(self.control_frame, setgrid=True,
                                       height=1, width=5)
        self.counter.grid(row=1, column=1)
        self.counter.insert(tkinter.END, 0)

        tkinter.Label(self.control_frame, text="Input:").grid(row=2,
                                                              column=0,
                                                              sticky="w")

        self.input_var = tkinter.StringVar()
        vcmd = self.root.register(self.check_input), "%P"
        self.input = tkinter.Entry(self.control_frame, width=5,
                                   textvariable=self.input_var,
                                   state="disabled",
                                   validate="key", vcmd=vcmd)
        self.input.grid(row=2, column=1)
        self.input_btn = tkinter.Button(self.control_frame, text="Submit",
                                        command=self.got_input,
                                        state="disabled")
        self.input_btn.grid(row=2, column=2)

        tkinter.Label(self.control_frame, text="Output:").grid(row=3,
                                                               column=0,
                                                               sticky="w")

        self.output = stext.ScrolledText(self.control_frame, height=10,
                                         width=20, state="disabled",
                                         bg="white")
        self.output.grid(row=3, column=1, columnspan=2)

        tkinter.Label(self.control_frame, text="Speed:").grid(row=4,
                                                              column=0,
                                                              sticky="w")

        self.speed_scale = tkinter.Scale(self.control_frame,
                                         orient="horizontal",
                                         length=150,
                                         to=2.5, resolution=0.01)
        self.speed_scale["from"] = 0.0
        self.speed_scale.set(0.01)
        self.speed_scale.grid(row=4, column=1, columnspan=2)

        # Memory display on right

        self.memory_frame = MemoryDisplay(self.root, self.setmem)
        self.memory_frame.grid(row=1, column=1)

        self.root.after(1, self.run_halt_check)  # Kick off

    def set_code(self, code, fname):
        self.runner = yaplmc.Runner(code, give_output=self.give_output,
                                    halt_for_inp=True)
        self.root.title("yaplmc - " + fname)
        self.update_memory()

    def run_wrapper(self, func):
        if self.getting_inp:
            self.get_input()
            return
        try:
            ret = func()
        except RuntimeError as e:
            self.give_output("Error:\n{}".format(e.args[0]))
            self.run_to_halt = False
            return
        if ret == yaplmc.HALT_REASON_INP:
            self.get_input()
        return ret

    def next_step(self):
        if self.getting_inp:
            self.get_input()
            return
        try:
            ret = self.runner.next_step()
            self.update_memory()
        except RuntimeError as e:
            self.give_output("Error:\n{}".format(e.args[0]))
            self.run_to_halt = False
            return
        if ret == yaplmc.HALT_REASON_INP:
            self.get_input()
        return ret

    def run_halt_check(self):
        if self.getting_inp:
            self.get_input()
        elif self.run_to_halt:
            try:
                ret = self.runner.next_step()
            except RuntimeError as e:
                self.give_output("Error:\n{}".format(e.args[0]))
                self.run_to_halt = False
            else:
                self.update_memory()
                if ret == yaplmc.HALT_REASON_HLT:
                    self.run_to_halt = False
                elif ret == yaplmc.HALT_REASON_INP:
                    self.get_input()
        i = int(self.speed_scale.get() * 1000)
        if i == 0 and not (self.run_to_halt and not self.getting_inp):
            i = 1
        self.root.after(i, self.run_halt_check)

    def run_to_hlt(self):
        self.run_to_halt = True

    def pause(self):
        self.run_to_halt = False

    def set_colors(self):
        if self.runner.accumulator_changed:
            self.accumulator.config(bg=CHANGED)
        elif self.runner.accumulator_read:
            self.accumulator.config(bg=READ)
        else:
            self.accumulator.config(bg=DEFAULT)
        self.memory_frame.set_colors(self.runner.memory_changed,
                                     self.runner.memory_read,
                                     self.runner.instruction_addr)

    def update_memory(self):
        self.memory_frame.update_memory(self.runner.memory)
        self.accumulator.delete(tkinter.END)
        self.accumulator.insert(tkinter.END, self.runner.accumulator)
        self.counter.delete(tkinter.END)
        self.counter.insert(tkinter.END, self.runner.counter)
        self.set_colors()

    def give_output(self, i, err=False):
        if isinstance(i, int):
            if i >= 500:
                i = i - 1000
        i = str(i)
        self.output["state"] = "normal"
        if self.output.get(1.0, tkinter.END) == "\n":
            self.output.delete(1.0, tkinter.END)
        else:
            self.output.insert(tkinter.END, "\n")
        self.output.insert(tkinter.END, i)
        self.output.see(tkinter.END)
        self.output["state"] = "disabled"

    def check_input(self, num):
        if num in ("", "-"):
            return True
        try:
            return int(num) in range(-500, 500)
        except ValueError:
            return False

    def get_input(self):
        self.getting_inp = True
        self.input.focus()
        self.input["state"] = "normal"
        self.input_btn["state"] = "normal"

    def got_input(self):
        i = self.input_var.get()
        self.input_var.set("")
        self.input["state"] = "disabled"
        self.input_btn["state"] = "disabled"
        if self.getting_inp:
            self.runner.give_input(int(i))
            self.getting_inp = False
            self.update_memory()

    def setmem(self, addr, value):
        if self.run_to_halt or self.getting_inp:
            return False
        self.runner.setmem(addr, value)
        self.set_colors()
        return True

    def reset(self):
        self.run_to_halt = False
        self.getting_inp = False
        self.output["state"] = "normal"
        self.output.delete(1.0, tkinter.END)
        self.output["state"] = "disabled"
        self.runner.reset()
        self.update_memory()

    def exit(self):
        self.root.destroy()

if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                         epilog="""
yaplmc Copyright (C) 2014  Matthew Joyce
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions. Type `yaplmc --licence` for details.
                                         """.strip())
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
    r = RunGUI()
    code, fname = get_assembled_code(args_from_parser.file, r.root)
    if code:
        r.set_code(code, fname)
        tkinter.mainloop()
