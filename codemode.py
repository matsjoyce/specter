import tkinter
from tkinter import ttk, filedialog, simpledialog, font as tkfont, scrolledtext

import codeeditor
import assembler


class AssembleDialog(simpledialog.Dialog):
    def __init__(self, master, assembler_: assembler.Assembler):
        self.assembler = assembler_
        self.result = False
        super().__init__(master)

    def body(self, root):
        self.title("Assembling")
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

        t = scrolledtext.ScrolledText(self, bg="white")
        bold_font = tkfont.Font(t, t.cget("font"))
        bold_font["weight"] = "bold"
        t.tag_config("error", font=bold_font, foreground=codeeditor.ERROR_COLOR)
        t.tag_config("warning", font=bold_font, foreground=codeeditor.WARNING_COLOR)

        for prob in self.assembler.problems():
            t.insert(tkinter.END, prob.show(self.assembler.code) + "\n\n", prob.cat)

        t.pack()
        t["state"] = "disabled"

    def cancel_(self, *args):
        self.result = False
        super().cancel(*args)

    def ok(self, *args):
        self.result = True
        super().ok(*args)

    def buttonbox(self):
        box = tkinter.Frame(self)

        if not self.assembler.in_error:
            b = tkinter.Button(box, text="Run", command=self.ok)
            b.pack(side=tkinter.LEFT)
        b = tkinter.Button(box, text="Back to code", command=self.cancel_)
        b.pack(side=tkinter.LEFT)

        self.bind("<Return>", self.ok if not self.assembler.in_error else self.cancel_)
        self.bind("<Escape>", self.cancel_)
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

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def do_bindings(self):
        self.bind_all("<Control-s>", self.save_current)
        self.bind_all("<Control-S>", self.saveas_current)

    def do_unbindings(self):
        self.unbind_all("<Control-s>")
        self.unbind_all("<Control-S>")

    def current_codeeditor(self):
        if self.tabber.tabs():
            return self.tabber.nametowidget(self.tabber.select())

    def open(self, fnames=None):
        print("CM open")
        if not fnames:
            fnames = filedialog.askopenfilenames(parent=self,
                                                 defaultextension=".lmc",
                                                 filetypes=[("LMC files", ".lmc"),
                                                            ("All files", "*")])
        if not fnames:
            return
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
                self.tabber.select(ce)

    def new(self, *e):
        print("CM new")
        ce = codeeditor.CodeEditor(self.tabber)
        self.codeeditors.append(ce)
        self.tabber.add(ce)
        ce.focus_set()
        ce.set_name()

    def close_current(self):
        print("CM close")
        if self.codeeditors:
            current_ce = self.current_codeeditor()
            if current_ce.close():
                self.codeeditors.remove(current_ce)
                self.tabber.forget(current_ce)
                current_ce.destroy()

    def save_current(self, *e):
        print("CM save")
        if self.codeeditors:
            return self.current_codeeditor().save()

    def saveas_current(self, *e):
        print("CM saveas")
        if self.codeeditors:
            return self.current_codeeditor().saveas()

    def reload_current(self, *e):
        print("CM save")
        if self.codeeditors:
            return self.current_codeeditor().reload()

    def assemble(self, *e):
        print("CM assemble")
        if self.codeeditors and AssembleDialog(self, self.current_codeeditor().assembler).result:
            print("Switch")
            getattr(self.master, "runmode", lambda: None)()

    def commant_current(self, *e):
        print("CM comment")
        if self.codeeditors:
            return self.current_codeeditor().comment_line()

    def commant_decurrent(self, *e):
        print("CM decomment")
        if self.codeeditors:
            return self.current_codeeditor().decomment_line()

if __name__ == "__main__":
    root = tkinter.Tk(className='ToolTip-demo')
    t = CodeMode(root)
    t.grid(row=0, column=0, sticky=tkinter.NE + tkinter.SW)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root["menu"] = t.menu
    t.open()
    t.focus_set()
    t.do_bindings()
    root.mainloop()
