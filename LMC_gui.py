#!/usr/bin/env python3
#
# Graphical user interface written with tkinter for pyLMC
# Copyright (C) 2013  Matthew Joyce matsjoyce@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import tkinter
from tkinter import filedialog as fdialog
from tkinter import scrolledtext as stext
from LMC import Runner, assemble


class MemoryDisplay(tkinter.Frame):
    def __init__(self, root, rows=5):
        super().__init__(root)
        tkinter.Label(self, text="Memory").grid(row=0, column=1, columnspan=rows * 2)
        self.rows = rows
        self.per_thing = 100 // rows
        self.memory_nums = []
        self.memorys = []
        for i in range(rows):
            mn = tkinter.Listbox(self, setgrid=True, height=self.per_thing, width=2)
            mn.grid(row=1, column=i * 2)
            for j in range(self.per_thing * i, self.per_thing * (i + 1)):
                mn.insert(tkinter.END, j)
            self.memory_nums.append(mn)

            m = tkinter.Listbox(self, setgrid=True, height=self.per_thing, width=3)
            m.grid(row=1, column=i * 2 + 1, padx=5)
            self.memorys.append(m)

    def update_memory(self, mem):
        for m in self.memorys:
            m.delete(0, tkinter.END)
        for i in range(self.rows):
            for j in mem[self.per_thing * i:self.per_thing * (i + 1)]:
                self.memorys[i].insert(tkinter.END, str(j).zfill(3))

class AssembleGUI:
    def __init__(self):
        self.root = tkinter.Tk()
        code = fdialog.askopenfile().read().split("\n")
        try:
            self.code, self.code_length = assemble(code)
            error = None
        except SyntaxError as e:
            self.code = None
            error = e.args[0]
        if error:
            tkinter.Label(self.root, text="Assembly failed!\nError:").pack()
            t = tkinter.Text(self.root)
            t.insert(tkinter.END, error)
            t.pack()
            tkinter.Button(self.root, text="Exit", command=self.exit).pack()
        else:
            tkinter.Label(self.root, text="Assembly succeeded!\nCode:").pack()
            t = tkinter.Text(self.root)
            t.insert(tkinter.END, " ".join(str(i).zfill(3) for i in self.code[:self.code_length]))
            t.pack()
            tkinter.Button(self.root, text="Run", command=self.run).pack()

    def exit(self):
        self.root.destroy()
        exit(1)

    def run(self):
        self.root.destroy()
        r = RunGUI()
        r.setup_runner(self.code)
        r.mainloop()

class RunGUI:
    def __init__(self):
        self.root = tkinter.Tk()

    def setup_runner(self, code):
        self.getting_inp = False
        self.runner = Runner(code, get_input=self.get_input, give_output=self.give_output, use_input_callback=True)

        self.button_frame = tkinter.Frame(self.root)
        self.button_frame.grid(row=0, column=0, columnspan=2)

        self.run_to_hlt_btn = tkinter.Button(self.button_frame, text="Run to halt", command=self.run_to_hlt, width=10)
        self.run_to_hlt_btn.grid(row=0, column=0)

        self.run_step_btn = tkinter.Button(self.button_frame, text="Run one step", command=self.next_step, width=10)
        self.run_step_btn.grid(row=0, column=1)
    
        self.reset_btn = tkinter.Button(self.button_frame, text="Reset", command=self.reset, width=10)
        self.reset_btn.grid(row=0, column=2)

        self.exit_btn = tkinter.Button(self.button_frame, text="Exit", command=self.exit, width=10)
        self.exit_btn.grid(row=0, column=3)

        self.control_frame = tkinter.Frame(self.root)
        self.control_frame.grid(row=1, column=0)

        tkinter.Label(self.control_frame, text="Accumulator").grid(row=0, column=0, sticky="w")

        self.accumulator = tkinter.Listbox(self.control_frame, setgrid=True, height=1, width=5)
        self.accumulator.grid(row=0, column=1)
        self.accumulator.insert(tkinter.END, 0)

        tkinter.Label(self.control_frame, text="Counter").grid(row=1, column=0, sticky="w")

        self.counter = tkinter.Listbox(self.control_frame, setgrid=True, height=1, width=5)
        self.counter.grid(row=1, column=1)
        self.counter.insert(tkinter.END, 0)

        tkinter.Label(self.control_frame, text="Input").grid(row=2, column=0, sticky="w")

        self.input_var = tkinter.StringVar()
        self.input = tkinter.Entry(self.control_frame, width=5, textvariable=self.input_var)
        self.input.grid(row=2, column=1)
        self.input_btn = tkinter.Button(self.control_frame, text="Submit", command=self.got_input)
        self.input_btn.grid(row=2, column=2)

        tkinter.Label(self.control_frame, text="Output").grid(row=3, column=0, sticky="w")

        self.output = stext.ScrolledText(self.control_frame, height=10, width=20)
        self.output.grid(row=3, column=1, columnspan=2)

        self.memory_frame = MemoryDisplay(self.root)
        self.memory_frame.grid(row=1, column=1)

        self.update_memory()

    def run_wrapper(self, func):
        if self.getting_inp:
            self.get_input()
            return
        try:
            cb = func()
        except RuntimeError as e:
            self.give_output("Error:\n{}".format(e.args[0]))
            return
        if isinstance(cb, bool):
            self.update_memory()
            return
        else:
            self.inp_callback = cb
            self.get_input()

    def next_step(self):
        self.run_wrapper(self.runner.next_step)

    def run_to_hlt(self):
        self.run_wrapper(self.runner.run_to_hlt)

    def update_memory(self):
        self.memory_frame.update_memory(self.runner.memory)
        self.accumulator.delete(tkinter.END)
        self.accumulator.insert(tkinter.END, self.runner.accumulator)
        self.counter.delete(tkinter.END)
        self.counter.insert(tkinter.END, self.runner.counter)

    def mainloop(self):
        self.root.mainloop()

    def give_output(self, i):
        if isinstance(i, int):
            if i >= 500:
                i = i - 1000
        self.output.insert(tkinter.END, str(i) + "\n")

    def get_input(self):
        self.update_memory()
        self.getting_inp = True
        self.input.focus()

    def got_input(self):
        i = self.input_var.get()
        self.input_var.set("")
        self.run_to_hlt_btn.focus()
        self.getting_inp = False
        rth = self.inp_callback(int(i))
        self.update_memory()
        if rth:
            self.run_to_hlt()

    def reset(self):
        self.output.delete(1.0, tkinter.END)
        self.runner.reset()
        self.update_memory()

    def exit(self):
        self.root.destroy()
        exit(0)

if __name__ == "__main__":
    a = AssembleGUI()
    a.root.mainloop()
