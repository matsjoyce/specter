import tkinter
from tkinter import (filedialog as fdialog, scrolledtext as stext,
                     simpledialog, font as tkfont)
import math
import functools
import runner
import dbgcodeeditor


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

            mn = tkinter.Entry(self, width=2, bg="white", borderwidth=0)
            mn.grid(row=row, column=col * 2, sticky=STICKY_NESW)
            mn.insert(0, str(i).zfill(2))
            self.memory_nums.append(mn)
            mn["state"] = "readonly"

            var = tkinter.StringVar(value="000")
            vcmd = (self.register(functools.partial(self.changed, i)), "%P",
                    "%V")
            m = tkinter.Entry(self, width=3, bg="white", borderwidth=0,
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

    def update_memory(self, runner):
        for i, m in enumerate(runner.memory):
            self.mem_vars[i].set(str(m.value).zfill(3))

    def set_colors(self, runner):
        for i, m in enumerate(runner.memory):
            self.memory_nums[i]["readonlybackground"] = dbgcodeeditor.COLOR_MAP[m.state]
            self.memorys[i]["bg"] = dbgcodeeditor.darken(dbgcodeeditor.COLOR_MAP[m.state])


class RunMode(tkinter.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.getting_inp = False
        self.run_to_halt = False
        self.show_debug = 0
        self.all_output = []
        self.runner = runner.Runner(self.give_output)

        # Top row of buttons

        self.button_frame = tkinter.Frame(self)
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

        switch_cmd = getattr(self.master, "codemode", lambda: None)
        self.exit_btn = tkinter.Button(self.button_frame, text="Back to code",
                                       command=switch_cmd)
        self.exit_btn.grid(row=0, column=4, sticky=tkinter.E + tkinter.W,
                           padx=2, pady=2)

        for col in range(5):
            self.button_frame.columnconfigure(col, weight=1)
        self.button_frame.rowconfigure(0, weight=1)

        # Left row of inputs

        self.control_frame = tkinter.Frame(self)
        self.control_frame.grid(row=1, column=0,
                                sticky=tkinter.NE + tkinter.SW,
                                padx=5, pady=5)

        tkinter.Label(self.control_frame,
                      text="Accumulator:").grid(row=0, column=0,
                                                sticky=tkinter.W)

        self.accumulator_var = tkinter.StringVar(value="000")
        vcmd = self.register(self.accumulator_changed), "%P", "%V"
        self.accumulator = mn = tkinter.Entry(self.control_frame, width=5,
                                              bg="white", borderwidth=0,
                                              textvar=self.accumulator_var,
                                              vcmd=vcmd, validate="all")
        self.accumulator.grid(row=0, column=1, sticky=tkinter.W,
                              padx=10, pady=5)

        tkinter.Label(self.control_frame,
                      text="Counter:").grid(row=1, column=0, sticky=tkinter.W)

        self.counter_var = tkinter.StringVar(value="000")
        vcmd = self.register(self.counter_changed), "%P", "%V"
        self.counter = tkinter.Entry(self.control_frame, width=5,
                                     bg="white", borderwidth=0,
                                     textvar=self.counter_var,
                                     vcmd=vcmd, validate="all")
        self.counter.grid(row=1, column=1, sticky=tkinter.W, padx=10, pady=5)

        tkinter.Label(self.control_frame,
                      text="Input:").grid(row=2, column=0, sticky=tkinter.W)

        self.input_frame = tkinter.Frame(self.control_frame)
        self.input_var = tkinter.StringVar()
        vcmd = self.register(self.check_input), "%P"
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
                                  foreground=dbgcodeeditor.darken(dbgcodeeditor.WRITTEN_COLOR))
        self.output.tag_configure("debug_read", font=italic_font,
                                  foreground=dbgcodeeditor.darken(dbgcodeeditor.READ_COLOR))
        self.output.tag_configure("debug_jump", font=italic_font,
                                  foreground=dbgcodeeditor.darken(dbgcodeeditor.NEXT_EXEC_COLOR))
        self.output.tag_configure("debug_other", font=italic_font,
                                  foreground=dbgcodeeditor.darken(dbgcodeeditor.EXECUTED_COLOR))

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
        vcmd = self.register(self.counter_changed), "%P", "%V"
        self.debug_btn = tkinter.Button(self.control_frame,
                                        command=self.toggle_debug, text="Off")
        self.debug_btn.grid(row=5, column=1, sticky=tkinter.W, padx=10, pady=5)

        self.control_frame.columnconfigure(1, weight=1)
        self.control_frame.rowconfigure(3, weight=1)

        # Memory display on right

        self.memory_frame = MemoryDisplay(self, self.setmem,
                                          self.update_memory)
        self.memory_frame.grid(row=1, column=1, sticky=STICKY_NESW,
                               padx=5, pady=5)

        # Make resizeable

        self.columnconfigure(1, weight=2)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.after(1, self.run_halt_check)  # Kick off

        self.menus = []
        self.run_menu = tkinter.Menu(self.master.menu, tearoff=False)
        self.run_menu.add_command(label="Run", command=self.run_to_halt)
        self.run_menu.add_command(label="Step", command=self.next_step)
        self.run_menu.add_command(label="Reset", command=self.reset)
        self.menus.append(dict(label="Run", menu=self.run_menu))

    def set_code(self, assembler, fname):
        self.runner.load_code(assembler)
        self.update_memory()

    def accumulator_changed(self, num, reason):
        if reason == "key":
            ok, num = check_num(num)
            if not hasattr(self, "runner") or not ok:
                return False
            self.runner.accumulator.write(num)
            self.set_colors()
        elif reason == "focusout":
            self.after(0, self.update_memory)
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
            self.after(0, self.update_memory)
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
        self.give_debug()
        self.update_memory()
        self.update_output()
        if ret is runner.HaltReason.hlt:
            self.run_to_halt = False
        elif ret == runner.HaltReason.input:
            self.get_input()
        return ret

    def run_halt_check(self):
        if self.run_to_halt:
            self.next_step()
        i = int(self.speed_scale.get() * 1000)
        self.after(i, self.run_halt_check)

    def run_to_hlt(self):
        self.run_to_halt = True

    def pause(self):
        self.run_to_halt = False

    def set_colors(self):
        self.accumulator.config(bg=dbgcodeeditor.COLOR_MAP[self.runner.accumulator.state])
        self.memory_frame.set_colors(self.runner)

    def update_memory(self):
        self.memory_frame.update_memory(self.runner)
        self.accumulator_var.set(str(self.runner.accumulator.value).zfill(3))
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

    def give_debug(self):
        if any(m.state == runner.ValueState.written for m in self.runner.memory):
            t = "_write"
        elif any(m.state == runner.ValueState.read for m in self.runner.memory):
            t = "_read"
        elif self.runner.instruction_addr != self.runner.counter - 1:
            t = "_jump"
        else:
            t = "_other"
        self.all_output.append((self.runner.hint, "debug" + t))

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
        self.runner.memory[addr].write(value)
        self.set_colors()
        return True

    def reset(self):
        self.run_to_halt = False
        self.getting_inp = False
        self.all_output = []
        self.runner.reset()
        self.update_memory()
        self.update_output()

    def do_bindings(self):
        pass

    def do_unbindings(self):
        pass

if __name__ == "__main__":
    root = tkinter.Tk(className='ToolTip-demo')
    t = RunMode(root)
    t.grid(row=0, column=0, sticky=tkinter.NE + tkinter.SW)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root["menu"] = t.menu
    t.focus_set()
    t.do_bindings()
    root.mainloop()
