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
from tkinter import filedialog as fdialog
from tkinter import scrolledtext as stext
import yaplmc
import math

CHANGED = "#E00"
CHANGEDN = "#C00"
READ = "#EE0"
READN = "#CC0"
INTR = "#0A0"
INTRN = "#080"
DEFAULT = "white"
DEFAULTN = "#DDD"


class MemoryDisplay(tkinter.Frame):
    def __init__(self, root, rows=5):
        super().__init__(root)
        tkinter.Label(self, text="Memory").grid(row=0, column=1,
                                                columnspan=rows * 2)
        self.rows = rows
        self.per_thing = 100 // rows
        self.memory_nums = []
        self.memorys = []
        for i in range(rows):
            mn = tkinter.Listbox(self, setgrid=True,
                                 height=self.per_thing, width=2)
            mn.grid(row=1, column=i * 2)
            for j in range(self.per_thing * i, self.per_thing * (i + 1)):
                mn.insert(tkinter.END, j)
            self.memory_nums.append(mn)

            m = tkinter.Listbox(self, setgrid=True,
                                height=self.per_thing, width=3,
                                bg=DEFAULT)
            m.grid(row=1, column=i * 2 + 1)
            self.memorys.append(m)

    def update_memory(self, mem):
        for m in self.memorys:
            m.delete(0, tkinter.END)
        for i in range(self.rows):
            for j in mem[self.per_thing * i:self.per_thing * (i + 1)]:
                self.memorys[i].insert(tkinter.END, str(j).zfill(3))

    def set_colors(self, mem_changed, mem_read, instr):
        for row in range(self.rows):
            for i in range(self.per_thing):
                self.memory_nums[row].itemconfig(i, bg=DEFAULTN)
                self.memorys[row].itemconfig(i, bg=DEFAULT)
        for i in mem_read:
            row = math.floor(i / self.per_thing)
            item = i % self.per_thing
            self.memory_nums[row].itemconfig(item, bg=READN)
            self.memorys[row].itemconfig(item, bg=READ)
        for i in mem_changed:
            row = math.floor(i / self.per_thing)
            item = i % self.per_thing
            self.memory_nums[row].itemconfig(item, bg=CHANGEDN)
            self.memorys[row].itemconfig(item, bg=CHANGED)
        row = math.floor(instr / self.per_thing)
        item = instr % self.per_thing
        self.memory_nums[row].itemconfig(item, bg=INTRN)
        self.memorys[row].itemconfig(item, bg=INTR)


class AssembleGUI:
    def __init__(self):
        self.root = tkinter.Tk()
        self.l = tkinter.Label(self.root, text="Waiting for file...",
                               padx=10, pady=10)
        self.l.grid(row=0, column=0)
        self.root.wm_title("yaplmc")
        f = fdialog.askopenfile()

        self.l.destroy()
        if f is None:
            self.exit()
        self.fname = f.name
        self.root.wm_title("yaplmc - " + self.fname)
        code = f.read().split("\n")
        try:
            self.code, code_length = yaplmc.assemble(code)
        except SyntaxError as e:
            tkinter.Label(self.root, text="Assembly failed!\nError:").pack()
            t = tkinter.Text(self.root)
            t.insert(tkinter.END, e.args[0])
            t.pack()
            tkinter.Button(self.root, text="Exit", command=self.exit).pack()
        else:
            self.l = tkinter.Label(self.root,
                                   text="Assembly succeeded!\nCode:")
            self.l.grid(row=0, column=0)
            self.t = tkinter.Text(self.root)
            code = " ".join(str(i).zfill(3) for i in self.code[:code_length])
            self.t.insert(tkinter.END, code)
            self.t.grid(row=1, column=0)
            self.b = tkinter.Button(self.root, text="Run", command=self.run)
            self.b.grid(row=2, column=0)

    def exit(self):
        self.root.destroy()
        exit(1)

    def run(self):
        self.l.destroy()
        self.t.destroy()
        self.b.destroy()
        RunGUI(self.root, self.code)


class RunGUI:
    def __init__(self, root, code):
        self.root = root
        self.root.wm_minsize(68, 24)
        # self.root.wm_maxsize(68, 24)

        self.getting_inp = False
        self.run_to_halt = False
        self.runner = yaplmc.Runner(code, give_output=self.give_output,
                                    halt_for_inp=True)

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
        self.control_frame.grid(row=1, column=0)

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
        self.input = tkinter.Entry(self.control_frame, width=5,
                                   textvariable=self.input_var,
                                   state="disabled")
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
        self.outputs = []

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

        self.memory_frame = MemoryDisplay(self.root)
        self.memory_frame.grid(row=1, column=1)

        self.update_memory()

        self.root.after(1, self.run_halt_check)  # Kick off

    def run_wrapper(self, func):
        if self.getting_inp:
            self.get_input()
            return
        try:
            ret = func()
        except RuntimeError as e:
            self.give_output("Error:\n{}".format(e.args[0]))
            return
        if ret == yaplmc.HALT_REASON_INP:
            self.get_input()
        return ret

    def next_step(self):
        self.run_wrapper(self.runner.next_step)
        self.update_memory()

    def run_halt_check(self):
        if self.run_to_halt and not self.getting_inp:
            ret = self.runner.next_step()
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
        self.output["state"] = "normal"
        self.output.delete(1.0, tkinter.END)
        self.output.insert(tkinter.END, "\n".join(self.outputs))
        self.output.see(tkinter.END)
        self.output["state"] = "disabled"

    def give_output(self, i):
        if isinstance(i, int):
            if i >= 500:
                i = i - 1000
        i = str(i)
        self.outputs.append(i)

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

    def reset(self):
        self.run_to_halt = False
        self.getting_inp = False
        self.outputs = []
        self.runner.reset()
        self.update_memory()

    def exit(self):
        self.root.destroy()
        exit(0)

if __name__ == "__main__":
    AssembleGUI()
    tkinter.mainloop()
