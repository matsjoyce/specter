import tkinter
from tkinter import (filedialog as fdialog, scrolledtext as stext,
                     simpledialog, font as tkfont, ttk)
import math
import functools
import logging
import runner
import codeeditor
import dbgcodeeditor


STICKY_NESW = tkinter.NE + tkinter.SW

logger = logging.getLogger(__name__)


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
        self.setmem = setmem
        self.rows = rows
        self.per_thing = 100 // rows
        self.memory_nums = []
        self.memorys = []
        self.mem_vars = []
        self.updater = updater
        for i in range(100):
            col = int(math.floor(i / self.per_thing))
            row = i % self.per_thing

            mn = tkinter.Entry(self, width=2, bg="white", borderwidth=0,
                               selectbackground="white", selectforeground="black")
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

    def set_colors(self, runner_):
        for i, m in enumerate(runner_.memory):
            self.memory_nums[i]["readonlybackground"] = dbgcodeeditor.darken(dbgcodeeditor.COLOR_MAP[m.state])
            self.memorys[i]["bg"] = dbgcodeeditor.COLOR_MAP[m.state]
            if (runner_.breakpoints_active
               and m.state == runner.ValueState.normal
               and m.breakpoint != runner.BreakpointState.off):
                self.memory_nums[i]["readonlybackground"] = dbgcodeeditor.darken(codeeditor.BREAKPOINT_BG_COLOR)
                self.memorys[i]["bg"] = codeeditor.BREAKPOINT_BG_COLOR


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
                                             text="Run",
                                             command=self.run_to_hlt)
        self.run_to_hlt_btn.grid(row=0, column=0, sticky=tkinter.E + tkinter.W,
                                 padx=2, pady=2)

        self.run_step_btn = tkinter.Button(self.button_frame,
                                           text="Step",
                                           command=self.next_step)
        self.run_step_btn.grid(row=0, column=1, sticky=tkinter.E + tkinter.W,
                               padx=2, pady=2)

        self.reset_btn = tkinter.Button(self.button_frame, text="Reset",
                                        command=self.reset)
        self.reset_btn.grid(row=0, column=2, sticky=tkinter.E + tkinter.W,
                            padx=2, pady=2)

        self.debug_var = tkinter.BooleanVar(value=False)
        self.debug_btn = tkinter.Button(self.button_frame,
                                        command=self.toggle_debug, text="Debug")
        self.debug_btn.grid(row=0, column=3, sticky=tkinter.E + tkinter.W,
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
        self.output.tag_configure("debug_breakpoint", font=bold_font,
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

        self.control_frame.columnconfigure(1, weight=1)
        self.control_frame.rowconfigure(3, weight=1)

        # Tabber for switching between memory and code

        self.tabber = ttk.Notebook(self)
        self.tabber.grid(row=1, column=1, sticky=STICKY_NESW, padx=5, pady=5)
        self.tabber.bind("<<NotebookTabChanged>>", self.unfocus_tabber_widget)

        # Memory display in the tabber

        self.memory_frame = MemoryDisplay(self.tabber, self.setmem,
                                          self.update_memory)
        self.tabber.add(self.memory_frame, text="Memory", sticky=STICKY_NESW)

        # Code display in the tabber

        self.code_editor = dbgcodeeditor.DebugCodeEditor(self.tabber)
        self.tabber.add(self.code_editor, text="Code", sticky=STICKY_NESW)

        # Make resizeable

        self.columnconfigure(1, weight=3)
        self.columnconfigure(0, weight=2)
        self.rowconfigure(1, weight=1)

        self.after(1, self.run_halt_check)  # Kick off

        self.menus = []
        self.run_menu = tkinter.Menu(self.master.menu, tearoff=False)
        self.run_menu.add_command(label="Run", command=self.run_to_halt)
        self.run_menu.add_command(label="Step", command=self.next_step)
        self.run_menu.add_command(label="Reset", command=self.reset)
        self.menus.append(dict(label="Run", menu=self.run_menu))

        self.debug_trace_var = tkinter.BooleanVar()
        self.breakpoints_active_var = tkinter.BooleanVar()

        self.debug_menu = tkinter.Menu(self.master.menu, tearoff=False)
        self.debug_menu.add_checkbutton(label="Debug trace", variable=self.debug_trace_var,
                                        command=self.update_debug_from_vars)
        self.debug_menu.add_checkbutton(label="Breapoints", variable=self.breakpoints_active_var,
                                        command=self.update_debug_from_vars)
        self.menus.append(dict(label="Debug", menu=self.debug_menu))

        self.breakpoints_active = False

    def unfocus_tabber_widget(self, *e):
        self.memory_frame.memory_nums[0].selection_clear()

    def set_code(self, assembler, fname):
        self.runner.load_code(assembler)
        self.code_editor.update_runner(self.runner)
        self.update_memory()
        self.code_editor.update_syntax()

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
        elif ret is runner.HaltReason.breakpoint:
            self.run_to_halt = False
            self.give_output("Hit breakpoint at {:03}".format(self.runner.instruction_addr), type="debug_breakpoint")
        elif ret == runner.HaltReason.input:
            self.get_input()
        return ret

    def run_halt_check(self):
        if self.run_to_halt:
            self.next_step()
        i = int(self.speed_scale.get() * 1000)
        self.after(i, self.run_halt_check)

    @property
    def run_to_halt(self):
        return self._run_to_halt

    @run_to_halt.setter
    def run_to_halt(self, value):
        self._run_to_halt = value
        if not hasattr(self, "run_to_hlt_btn"):
            return
        if value:
            self.run_to_hlt_btn.config(text="Stop", command=self.pause)
        else:
            self.run_to_hlt_btn.config(text="Run ", command=self.run_to_hlt)

    def run_to_hlt(self):
        self.run_to_halt = True

    def pause(self):
        self.run_to_halt = False

    def set_colors(self):
        self.accumulator.config(bg=dbgcodeeditor.COLOR_MAP[self.runner.accumulator.state])
        self.memory_frame.set_colors(self.runner)
        self.code_editor.update_syntax()

    def update_memory(self):
        self.memory_frame.update_memory(self.runner)
        self.accumulator_var.set(str(self.runner.accumulator.value).zfill(3))
        self.counter_var.set(str(self.runner.counter).zfill(3))
        self.set_colors()

    def toggle_debug(self):
        if self.show_debug or self.breakpoints_active:
            self.show_debug = self.breakpoints_active = False
        else:
            self.show_debug = self.breakpoints_active = True
        self.update_output()
        self.update_debug_button()
        self.debug_trace_var.set(self.show_debug)

    def update_debug_button(self):
        if self.show_debug or self.breakpoints_active:
            self.debug_btn.config(relief="sunken")
        else:
            self.debug_btn.config(relief="raised")

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

            def out(x):
                self.output.insert(tkinter.END, x + "\n", tag)

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
        self.set_colors()
        self.update_output()

    def set_breakpoints(self, brps):
        self.code_editor.breakpoints = brps
        self.code_editor.breakpoints_changed()

    def breakpoints_changed(self, brps):
        self.runner.load_breakpoints(brps)
        self.after(1, self.set_colors)

    @property
    def breakpoints_active(self):
        return self._breakpoints_active

    @breakpoints_active.setter
    def breakpoints_active(self, value):
        logger.info("Breakpoints active: {}", value)
        self._breakpoints_active = value
        self.breakpoints_active_var.set(value)
        self.runner.breakpoints_active = value
        self.code_editor.show_breakpoints(value)
        self.update_memory()

    def update_debug_from_vars(self):
        self.breakpoints_active = self.breakpoints_active_var.get()
        self.show_debug = self.debug_trace_var.get()
        self.update_output()
        self.update_debug_button()

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
