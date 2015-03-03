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

import tkinter
from tkinter import (filedialog as fdialog, scrolledtext as stext,
                     simpledialog, font as tkfont)
import yaplmc
import math
from functools import partial

__author__ = "Matthew Joyce"
__copyright__ = "Copyright 2013"
__credits__ = ["Matthew Joyce"]
__license__ = "GPL3"
__version__ = "1.1.0"
__maintainer__ = "Matthew Joyce"
__email__ = "matsjoyce@gmail.com"
__status__ = "Development"

CHANGEDN = "#C00"
CHANGED = "#E00"

READN = "#CC0"
READ = "#EE0"

INTRN = "#080"
INTR = "#0A0"

NINTRN = "#AAA"
NINTR = "#CCC"

DEFAULTN = "#DDD"
DEFAULT = "#FFF"

STICKY_NESW = tkinter.NE + tkinter.SW


def check_num(num):
    if num in ("", "-"):
        num = "0"
    try:
        if not int(num) in range(-500, 500):
            return False, 0
    except ValueError:
        return False, 0
    return True, int(num)


class MemoryDisplay(tkinter.Frame):
    def __init__(self, root, setmem, updater, rows=5):
        super().__init__(root)
        tkinter.Label(self, text="Memory").grid(row=0, column=1,
                                                columnspan=rows * 2)
        self.setmem = setmem
        self.rows = rows
        self.per_thing = 100 // rows
        self.memory_nums = []
        self.memorys = []
        self.mem_vars = []
        self.updater = updater
        for i in range(100):
            col = int(math.floor(i / self.per_thing))
            row = i % self.per_thing + 1

            mn = tkinter.Entry(self, width=2, bg=DEFAULT, borderwidth=0)
            mn.grid(row=row, column=col * 2, sticky=STICKY_NESW)
            mn.insert(0, str(i).zfill(2))
            self.memory_nums.append(mn)
            mn["state"] = "readonly"

            var = tkinter.StringVar(value="000")
            vcmd = self.register(partial(self.changed, i)), "%P", "%V"
            m = tkinter.Entry(self, width=3, bg=DEFAULT, borderwidth=0,
                              textvariable=var, vcmd=vcmd, validate="all")
            m.grid(row=row, column=col * 2 + 1, sticky=STICKY_NESW)
            self.memorys.append(m)
            self.mem_vars.append(var)

        for x in range(self.rows * 2):
            self.columnconfigure(x, weight=1)
        for y in range(self.per_thing + 1):
            self.rowconfigure(y, weight=1)

    def changed(self, addr, num, reason):
        if reason == "key":
            ok, num = check_num(num)
            if not ok:
                return False
            return self.setmem(addr, num)
        elif reason == "focusout":
            self.after(0, self.updater)
        return True

    def update_memory(self, mem):
        for i, m in enumerate(mem):
            self.mem_vars[i].set(str(m).zfill(3))

    def set_colors(self, mem_changed, mem_read, instr, ninstr):
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
        self.memory_nums[ninstr]["readonlybackground"] = NINTRN
        self.memorys[ninstr]["bg"] = NINTR


class AssembleGUI(simpledialog.Dialog):
    def __init__(self, f=None, parent=None):
        self.f = f
        self.code = self.fname = None
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

            t = tkinter.Text(self.root, bg="white")
            t.insert(tkinter.END, e.args[0])

            bold_font = tkfont.Font(t, t.cget("font"))
            bold_font["weight"] = "bold"
            t.config(font=bold_font, foreground="red")
            t.pack()
            t["state"] = "disabled"
        else:
            tkinter.Label(self.root, text="Assembly succeeded!\nCode:").pack()

            t = tkinter.Text(self.root, bg="white")
            code = " ".join(str(i).zfill(3) for i in self.code[:code_length])
            t.insert(tkinter.END, code)
            t.pack()
            t["state"] = "disabled"

    def cancel_(self, *args):
        self.code = self.fname = None
        super().cancel(*args)

    def buttonbox(self):
        box = tkinter.Frame(self)

        if self.code:
            b = tkinter.Button(box, text="Run", command=self.ok)
            b.pack(side=tkinter.LEFT)
        b = tkinter.Button(box, text="Exit", command=self.cancel_)
        b.pack(side=tkinter.LEFT)

        self.bind("<Return>", self.ok if self.code else self.cancel_)
        self.bind("<Escape>", self.cancel_)
        box.pack()


class RunGUI:
    def __init__(self):
        self.root = tkinter.Tk()
        self.root.title("yaplmc")

        self.getting_inp = False
        self.run_to_halt = False
        self.show_debug = 0
        self.all_output = []

        # Top row of buttons

        self.button_frame = tkinter.Frame(self.root)
        self.button_frame.grid(row=0, column=0, columnspan=2,
                               sticky=tkinter.E + tkinter.W + tkinter.N)

        self.run_to_hlt_btn = tkinter.Button(self.button_frame,
                                             text="Run to halt",
                                             command=self.run_to_hlt)
        self.run_to_hlt_btn.grid(row=0, column=0, sticky=tkinter.E + tkinter.W,
                                 padx=2, pady=2)

        self.run_step_btn = tkinter.Button(self.button_frame,
                                           text="Run one step",
                                           command=self.next_step)
        self.run_step_btn.grid(row=0, column=1, sticky=tkinter.E + tkinter.W,
                               padx=2, pady=2)

        self.pause_btn = tkinter.Button(self.button_frame, text="Pause",
                                        command=self.pause)
        self.pause_btn.grid(row=0, column=2, sticky=tkinter.E + tkinter.W,
                            padx=2, pady=2)

        self.reset_btn = tkinter.Button(self.button_frame, text="Reset",
                                        command=self.reset)
        self.reset_btn.grid(row=0, column=3, sticky=tkinter.E + tkinter.W,
                            padx=2, pady=2)

        self.exit_btn = tkinter.Button(self.button_frame, text="Exit",
                                       command=self.exit)
        self.exit_btn.grid(row=0, column=4, sticky=tkinter.E + tkinter.W,
                           padx=2, pady=2)

        for col in range(5):
            self.button_frame.columnconfigure(col, weight=1)
        self.button_frame.rowconfigure(0, weight=1)

        # Left row of inputs

        self.control_frame = tkinter.Frame(self.root)
        self.control_frame.grid(row=1, column=0,
                                sticky=tkinter.NE + tkinter.SW,
                                padx=5, pady=5)

        tkinter.Label(self.control_frame,
                      text="Accumulator:").grid(row=0, column=0,
                                                sticky=tkinter.W)

        self.accumulator_var = tkinter.StringVar(value="000")
        vcmd = self.root.register(self.accumulator_changed), "%P", "%V"
        self.accumulator = mn = tkinter.Entry(self.control_frame, width=5,
                                              bg=DEFAULT, borderwidth=0,
                                              textvar=self.accumulator_var,
                                              vcmd=vcmd, validate="all")
        self.accumulator.grid(row=0, column=1, sticky=tkinter.W,
                              padx=10, pady=5)

        tkinter.Label(self.control_frame,
                      text="Counter:").grid(row=1, column=0, sticky=tkinter.W)

        self.counter_var = tkinter.StringVar(value="000")
        vcmd = self.root.register(self.counter_changed), "%P", "%V"
        self.counter = tkinter.Entry(self.control_frame, width=5,
                                     bg=DEFAULT, borderwidth=0,
                                     textvar=self.counter_var,
                                     vcmd=vcmd, validate="all")
        self.counter.grid(row=1, column=1, sticky=tkinter.W, padx=10, pady=5)

        tkinter.Label(self.control_frame,
                      text="Input:").grid(row=2, column=0, sticky=tkinter.W)

        self.input_frame = tkinter.Frame(self.control_frame)
        self.input_var = tkinter.StringVar()
        vcmd = self.root.register(self.check_input), "%P"
        self.input = tkinter.Entry(self.input_frame, width=5,
                                   textvariable=self.input_var,
                                   state="disabled",
                                   validate="key", vcmd=vcmd)
        self.input.grid(row=0, column=0, padx=10, pady=5)
        self.input.bind("<Return>", self.got_input)

        self.input_btn = tkinter.Button(self.input_frame, text="Submit",
                                        command=self.got_input,
                                        state="disabled")
        self.input_btn.grid(row=0, column=1, padx=10, pady=5)
        self.input_frame.grid(row=2, column=1, sticky=tkinter.W)

        tkinter.Label(self.control_frame,
                      text="Output:").grid(row=3, column=0, sticky=tkinter.W)

        self.output = stext.ScrolledText(self.control_frame, height=10,
                                         width=20, state="disabled",
                                         bg="white")
        self.output.grid(row=3, column=1, sticky=tkinter.NW + tkinter.SE,
                         padx=10, pady=5)

        # Output formatting
        normal_font = self.output.cget("font")

        bold_font = tkfont.Font(self.output, normal_font)
        bold_font["weight"] = "bold"

        italic_font = tkfont.Font(self.output, normal_font)
        italic_font["slant"] = "italic"

        self.output.tag_configure("output", font=normal_font)
        self.output.tag_configure("input", font=normal_font)
        self.output.tag_configure("error", font=bold_font, foreground="red")
        self.output.tag_configure("done", font=normal_font)

        self.output.tag_configure("debug_write", font=italic_font,
                                  foreground=CHANGEDN)
        self.output.tag_configure("debug_read", font=italic_font,
                                  foreground=READN)
        self.output.tag_configure("debug_jump", font=italic_font,
                                  foreground=NINTRN)
        self.output.tag_configure("debug_other", font=italic_font,
                                  foreground=INTRN)

        self.output.tag_configure("debug_output", font=bold_font)
        self.output.tag_configure("debug_input", font=bold_font)
        self.output.tag_configure("debug_error", font=bold_font,
                                  foreground="red")
        self.output.tag_configure("debug_done", font=bold_font)

        tkinter.Label(self.control_frame, text="Speed:").grid(row=4,
                                                              column=0,
                                                              sticky=tkinter.W)

        self.speed_scale = tkinter.Scale(self.control_frame,
                                         orient="horizontal",
                                         length=150,
                                         to=2.5, resolution=0.01)
        self.speed_scale["from"] = 0.01
        self.speed_scale.set(0.01)
        self.speed_scale.grid(row=4, column=1,
                              sticky=tkinter.E + tkinter.W, padx=10)

        tkinter.Label(self.control_frame, text="Debug:").grid(row=5,
                                                              column=0,
                                                              sticky=tkinter.W)

        self.debug_var = tkinter.BooleanVar(value=False)
        vcmd = self.root.register(self.counter_changed), "%P", "%V"
        self.debug_btn = tkinter.Button(self.control_frame,
                                        command=self.toggle_debug, text="Off")
        self.debug_btn.grid(row=5, column=1, sticky=tkinter.W, padx=10, pady=5)

        self.control_frame.columnconfigure(1, weight=1)
        self.control_frame.rowconfigure(3, weight=1)

        # Memory display on right

        self.memory_frame = MemoryDisplay(self.root, self.setmem,
                                          self.update_memory)
        self.memory_frame.grid(row=1, column=1, sticky=STICKY_NESW,
                               padx=5, pady=5)

        # Make resizeable

        self.root.columnconfigure(1, weight=2)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.root.after(1, self.run_halt_check)  # Kick off

    def set_code(self, code, fname):
        self.runner = yaplmc.Runner(code, give_output=self.give_output,
                                    halt_for_inp=True,
                                    unfiltered_debug_output=self.give_debug)
        self.root.title("yaplmc - " + fname)
        self.update_memory()

    def accumulator_changed(self, num, reason):
        if reason == "key":
            ok, num = check_num(num)
            if not hasattr(self, "runner") or not ok:
                return False
            self.runner.setaccum(num)
            self.set_colors()
        elif reason == "focusout":
            self.root.after(0, self.update_memory)
        return True

    def counter_changed(self, num, reason):
        if reason == "key":
            if not hasattr(self, "runner") or len(num) > 3:
                return False
            if num == "":
                num = "0"
            try:
                if not int(num) in range(1000):
                    return False
            except ValueError:
                return False
            self.runner.counter = int(num)
            self.set_colors()
        elif reason == "focusout":
            self.root.after(0, self.update_memory)
        return True

    def next_step(self):
        if self.getting_inp:
            self.get_input()
            return
        try:
            ret = self.runner.next_step()
        except RuntimeError as e:
            self.give_output(e.args[0], type="error")
            self.run_to_halt = False
            ret = None
        self.type_debug()
        self.update_memory()
        self.update_output()
        if ret == yaplmc.HALT_REASON_HLT:
            self.run_to_halt = False
        elif ret == yaplmc.HALT_REASON_INP:
            self.get_input()
        return ret

    def run_halt_check(self):
        if self.run_to_halt:
            self.next_step()
        i = int(self.speed_scale.get() * 1000)
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
                                     self.runner.instruction_addr,
                                     self.runner.counter)

    def update_memory(self):
        self.memory_frame.update_memory(self.runner.memory)
        self.accumulator_var.set(str(self.runner.accumulator).zfill(3))
        self.counter_var.set(str(self.runner.counter).zfill(3))
        self.set_colors()

    def toggle_debug(self):
        self.show_debug = not self.show_debug
        if self.show_debug:
            self.debug_btn.config(relief="sunken", text="On")
        else:
            self.debug_btn.config(relief="raised", text="Off")
        self.update_output()

    def give_output(self, i, type="output"):
        if isinstance(i, int):
            if i >= 500:
                i = i - 1000
        i = str(i)
        if i == "Done! Coffee break!":
            self.all_output.append((i, "done"))
        else:
            self.all_output.append((i, type))
        self.update_output()

    def give_debug(self, t, level):
        if level == 1:
            self.give_output(t, type="waiting_typing")

    def type_debug(self):
        if self.runner.memory_changed:
            t = "_write"
        elif self.runner.memory_read:
            t = "_read"
        elif self.runner.instruction_addr != self.runner.counter - 1:
            t = "_jump"
        else:
            t = "_other"
        for i, (text, type) in enumerate(self.all_output):
            if type == "waiting_typing":
                self.all_output[i] = (text, "debug" + t)

    def update_output(self):
        self.output["state"] = "normal"
        self.output.delete("1.0", tkinter.END)
        for text, type in self.all_output:
            tag = type
            out = lambda x: self.output.insert(tkinter.END, x + "\n", tag)
            if self.show_debug:
                if not type.startswith("debug_"):
                    tag = "debug_" + type
                if type == "output":
                    out(">>> " + text)
                elif type.startswith("debug"):
                    out(text)
                elif type == "input":
                    out("<<< " + text)
                elif type == "error":
                    out("Error: " + text)
                elif type == "done":
                    out(text)
            else:
                if type == "output":
                    out(text)
                elif type == "error":
                    out("Error: " + text)
                elif type == "done":
                    out(text)

        self.output.see(tkinter.END)
        self.output["state"] = "disabled"

    def check_input(self, num):
        if num in ("", "-"):
            return True
        if len(num) > 4 or len(num) > 3 and not num.startswith("-"):
            return False
        try:
            return int(num) in range(-500, 500)
        except ValueError:
            return False

    def get_input(self):
        self.getting_inp = True
        self.input.focus()
        self.input["state"] = "normal"
        self.input_btn["state"] = "normal"

    def got_input(self, *args):
        i = self.input_var.get()
        self.input_var.set("")
        self.input["state"] = "disabled"
        self.input_btn["state"] = "disabled"
        if self.getting_inp:
            self.runner.give_input(int(i))
            self.give_output(int(i), type="input")
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
        self.all_output = []
        self.runner.reset()
        self.update_memory()
        self.update_output()

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
    a = AssembleGUI(args_from_parser.file, r.root)
    if a.code:
        r.set_code(a.code, a.fname)
        tkinter.mainloop()
