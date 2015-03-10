import tkinter
from tkinter import font as tkfont

import codeeditor
import assembler
import runner


READ_COLOR = "#EE0"
WRITTEN_COLOR = "#E00"
EXECUTED_COLOR = "#0A0"
NEXT_EXEC_COLOR = "#CCC"


COLOR_MAP = dict(zip(runner.ValueState, ["#FFF", READ_COLOR, WRITTEN_COLOR,
                                         EXECUTED_COLOR, NEXT_EXEC_COLOR]))


def darken(s):
    return s.translate(str.maketrans("23456789ABCDEF", "0123456789ABCE"))


class DbgTooltipContentInterface(codeeditor.TooltipContentInterface):
    def action(self, state):
        self.put(state.value.title(), "state_" + state.value)


class DbgTooltip(codeeditor.Tooltip):
    def __init__(self, master, memval, position, content_interface=DbgTooltipContentInterface):
        super().__init__(master, [memval], position, content_interface=content_interface)

    def setup_text(self, text_widget):
        super().setup_text(text_widget)

        normal_font = text_widget.cget("font")

        bold_font = tkfont.Font(text_widget, normal_font)
        bold_font["weight"] = "bold"

        for state, color in zip(runner.ValueState, ["#000", READ_COLOR, WRITTEN_COLOR,
                                EXECUTED_COLOR, NEXT_EXEC_COLOR]):
            text_widget.tag_configure("state_" + state.value, font=bold_font, foreground=darken(color))


class DebugCodeEditor(codeeditor.CodeEditor):
    def __init__(self, master):
        super().__init__(master)
        for state, color in COLOR_MAP.items():
            self.text.tag_configure("state_" + state.value, background=color)
        self.text.tag_raise("sel")
        self.text["state"] = "disabled"

    def update_runner(self, runner):
        self.runner = runner
        self.assembler = self.runner.assembler
        self.text["state"] = "normal"
        self.text.delete("1.0", tkinter.END)
        self.text.insert(tkinter.END, self.assembler.raw_code[:-1])
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.text["state"] = "disabled"
        self.set_name()
        self.update_syntax()

    def update_syntax(self):
        self.text["state"] = "normal"
        super().update_syntax()
        for state in runner.ValueState:
            self.text.tag_remove("state_" + state.value, "1.0", tkinter.END)
        for val in self.runner.memory:
            if val.token is None:
                continue
            print(val.token.position.lineno, val.state)
            lineno = val.token.position.lineno + 1
            self.text.tag_add("state_" + val.state.value,
                              str(lineno) + ".0",
                              str(lineno + 1) + ".0")
        self.text["state"] = "disabled"

    def make_tooltip(self, token):
        if self.tooltip:
            self.nuke_tooltip()
        if token and isinstance(token, assembler.Mnemonic):
            print("Making tooltip")
            x, y = self.text.winfo_pointerx(), self.text.winfo_pointery()
            pos = x + 20, y - 35
            self.tooltip = DbgTooltip(self, self.runner.memory[token.address], pos)
        else:
            print("Did not make tooltip as nothing to show")

    def create_problem_tag(self, token):
        # Disable problem underlining
        pass

    def set_name(self):
        pass


if __name__ == "__main__":
    import sys, tkinter.ttk as ttk
    assem = assembler.Assembler()
    assem.update_code(open(sys.argv[1]).read())
    print(assem.assemble())
    runner_ = runner.Runner(lambda x: print(">>>", x))
    runner_.load_code(assem)
    root = tkinter.Tk(className='ToolTip-demo')
    t = ttk.Notebook(root)
    t.grid(sticky=tkinter.NE + tkinter.SW)
    ce = DebugCodeEditor(t)
    t.add(ce, text="Hi")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    ce.update_runner(runner_)
    def c():
        runner_.next_step()
        ce.update_syntax()
    b=tkinter.Button(root, text="Step", command=c)
    b.grid()
    root.mainloop()
