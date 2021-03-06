import tkinter
from tkinter import ttk, filedialog, simpledialog, font as tkfont, scrolledtext
import logging

import codeeditor
import assembler

logger = logging.getLogger(__name__)


class AssembleDialog(codeeditor.ProblemsDialog):
    def __init__(self, master, assembler):
        self.result = False
        super().__init__(master, assembler)

    def body(self, master):
        self.assembler.assemble()

        if not self.assembler.in_error:
            tkinter.Label(self, text="Assembly succeeded!\nMachine code:").pack()

            t = tkinter.Text(self, bg="white", height=4)
            code = " ".join(str(i).zfill(3) for i in self.assembler.machine_code)
            t.insert(tkinter.END, code)
            t.pack()
            t["state"] = "disabled"
        else:
            tkinter.Label(self, text="Assembly failed!").pack()

        tkinter.Label(self, text="Problems:").pack()

        super().body(master)
        self.title("Assembling")

    def ok(self, *args):
        self.result = True
        super().ok(*args)

    def buttonbox(self):
        box = tkinter.Frame(self)

        if not self.assembler.in_error:
            b = tkinter.Button(box, text="Run", command=self.ok)
            b.pack(side=tkinter.LEFT)
        b = tkinter.Button(box, text="Back to code", command=self.cancel)
        b.pack(side=tkinter.LEFT)

        self.bind("<Return>", self.ok if not self.assembler.in_error else self.cancel)
        self.bind("<Escape>", self.cancel)
        box.pack()


class CodeMode(tkinter.Frame):
    def __init__(self, master):
        super().__init__(master, bg="blue")
        self.codeeditors = []

        self.menus = []
        self.file_menu = tkinter.Menu(self.master.menu, tearoff=False)
        self.file_menu.add_command(label="New", command=self.new)
        self.file_menu.add_command(label="Open", command=self.open)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save", command=self.save_current)
        self.file_menu.add_command(label="Save As", command=self.saveas_current)
        self.file_menu.add_command(label="Reload", command=self.reload_current)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Close", command=self.close_current)
        self.menus.append(dict(label="File", menu=self.file_menu))

        self.code_menu = tkinter.Menu(self.master.menu, tearoff=False)
        self.code_menu.add_command(label="Assemble", command=self.assemble)
        self.code_menu.add_command(label="Problems", command=self.problems)
        self.code_menu.add_separator()
        self.code_menu.add_command(label="Comment", command=self.commant_current)
        self.code_menu.add_command(label="Decomment", command=self.commant_decurrent)
        self.menus.append(dict(label="Code", menu=self.code_menu))

        self.button_box = tkinter.Frame(self, bg="red")
        tkinter.Button(self.button_box, text="New", command=self.new).grid(row=0, column=0,
                                                                           sticky=tkinter.E + tkinter.W)
        tkinter.Button(self.button_box, text="Open", command=self.open).grid(row=0, column=1,
                                                                             sticky=tkinter.E + tkinter.W)
        tkinter.Button(self.button_box, text="Save", command=self.save_current).grid(row=0, column=2,
                                                                                     sticky=tkinter.E + tkinter.W)
        tkinter.Button(self.button_box, text="Close", command=self.close_current).grid(row=0, column=3,
                                                                                       sticky=tkinter.E + tkinter.W)
        tkinter.Button(self.button_box, text="Assemble", command=self.assemble).grid(row=0, column=4,
                                                                                     sticky=tkinter.E + tkinter.W)
        self.button_box.grid(row=0, column=0, sticky=tkinter.NE + tkinter.W)
        self.button_box.rowconfigure(0, weight=1)
        for i in range(5):
            self.button_box.columnconfigure(i, weight=1)

        self.tabber = ttk.Notebook(self, width=600, height=400)
        self.tabber.grid(row=1, column=0, sticky=tkinter.NE + tkinter.SW)
        self.tabber.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def do_bindings(self):
        self.bind_all("<Control-s>", self.save_current)
        self.bind_all("<Control-S>", self.saveas_current)
        self.bind_all("<Control-w>", self.close_current)
        self.bind_all("<F5>", self.assemble)

    def do_unbindings(self):
        self.unbind_all("<Control-s>")
        self.unbind_all("<Control-S>")
        self.unbind_all("<Control-w>")
        self.unbind_all("<F5>")

    def current_codeeditor(self):
        if self.tabber.tabs():
            return self.tabber.nametowidget(self.tabber.select())

    def open(self, fnames=None):
        logger.info("Open")
        if not fnames:
            fnames = filedialog.askopenfilenames(parent=self,
                                                 defaultextension=".lmc",
                                                 filetypes=[("LMC files", ".lmc"),
                                                            ("All files", "*")])
        if not fnames:
            return
        logger.info("Opening {}", fnames)
        for fname in fnames:
            current = [i for i in self.codeeditors if i.fname == fname]
            if current:
                self.tabber.select(current[0])
            else:
                ce = codeeditor.CodeEditor(self.tabber)
                self.codeeditors.append(ce)
                self.tabber.add(ce, sticky=tkinter.NE + tkinter.SW)
                ce.open(fname)
                ce.focus_set()
                ce.set_name()
                self.tabber.select(ce)

    def new(self, *e):
        logger.info("New")
        ce = codeeditor.CodeEditor(self.tabber)
        self.codeeditors.append(ce)
        self.tabber.add(ce)
        ce.focus_set()
        ce.set_name()

    def close_current(self, *e):
        logger.info("Close")
        if self.codeeditors:
            current_ce = self.current_codeeditor()
            if current_ce.close():
                self.codeeditors.remove(current_ce)
                self.tabber.forget(current_ce)
                current_ce.destroy()

    def save_current(self, *e):
        logger.info("Save")
        if self.codeeditors:
            return self.current_codeeditor().save()
        self.on_tab_change()

    def saveas_current(self, *e):
        logger.info("Save As")
        if self.codeeditors:
            return self.current_codeeditor().saveas()
        self.on_tab_change()

    def reload_current(self, *e):
        logger.info("Reload")
        if self.codeeditors:
            return self.current_codeeditor().reload()

    def assemble(self, *e):
        logger.info("Assemble")
        if self.codeeditors:
            ce = self.current_codeeditor()
            if AssembleDialog(ce, ce.assembler).result:
                logger.info("Switch")
                getattr(self.master, "runmode", lambda: None)()
            else:
                logger.info("No switch")

    def commant_current(self, *e):
        logger.info("Comment")
        if self.codeeditors:
            return self.current_codeeditor().comment_line()

    def commant_decurrent(self, *e):
        logger.info("Decomment")
        if self.codeeditors:
            return self.current_codeeditor().decomment_line()

    def problems(self, *e):
        logger.info("Problems")
        if self.codeeditors:
            return self.current_codeeditor().show_problems()

    def on_tab_change(self, *e):
        if self.codeeditors:
            self.master.set_title(self.current_codeeditor().display_name)

if __name__ == "__main__":
    root = tkinter.Tk(className='ToolTip-demo')
    root.menu = tkinter.Menu(root)
    root.set_title = lambda *a: None
    t = CodeMode(root)
    t.grid(row=0, column=0, sticky=tkinter.NE + tkinter.SW)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root["menu"] = root.menu
    for opts in t.menus:
        root.menu.add_cascade(**opts)
    t.open()
    t.focus_set()
    t.do_bindings()
    root.mainloop()
