import tkinter
from tkinter import scrolledtext as stext, font as tkfont, filedialog, ttk, messagebox, simpledialog
import functools
import collections
import assembler
import runner
import itertools
import re
import os
import enum
import random
import traceback
import logging


# Colors from Kate theme
LABEL_COLOR = "#006E28"
COMMENT_COLOR = "#898887"
NUMBER_COLOR = "#B08000"
HIGHLIGHT_COLOR = "#FBFA96"
ERROR_COLOR = "#BF0303"
WARNING_COLOR = "#CA9219"

HOVER_TIME = 500

BREAKPOINT_BG_COLOR = "#FDD"

BREAKPOINT_SHORTENED = {
    runner.BreakpointState.off: "",
    runner.BreakpointState.on_execute: "E",
    runner.BreakpointState.on_read: "R",
    runner.BreakpointState.on_write: "W",
    runner.BreakpointState.on_rw: "RW",
    runner.BreakpointState.on_next_execute: "NE"
}

logger = logging.getLogger(__name__)


class LineBarMode(enum.Enum):
    none = "none"
    address = "address"
    lineno = "line number"


# itertools recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def mouse_inside(widget):
    return (0 <= (widget.winfo_pointerx() - widget.winfo_rootx()) < widget.winfo_width()
            and 0 <= (widget.winfo_pointery() - widget.winfo_rooty()) < widget.winfo_height())


class ProblemsDialog(simpledialog.Dialog):
    def __init__(self, master, assembler):
        self.assembler = assembler
        super().__init__(master)

    def body(self, master):
        master.pack = lambda *a, p=master.pack, **k: p(*a, fill="both",
                                                       expand=1, **k)
        self.title("Problems")
        self.assembler.assemble()
        columns = ["Type", "Problem", "Line", "Text"]

        self.treeframe = tkinter.Frame(master)

        self.tree = ttk.Treeview(self.treeframe, columns=columns, show="headings")

        normal_font = tkfont.Font(self.tree, "TkFixedFont")

        bold_font = tkfont.Font(self.tree, normal_font)
        bold_font["weight"] = "bold"

        self.tree.tag_configure("error", foreground=ERROR_COLOR,
                                font=bold_font)
        self.tree.tag_configure("warning", foreground=WARNING_COLOR,
                                font=normal_font)

        widths = {col: [] for col in columns}
        self.item_to_token = {}

        for col in columns:
            self.tree.heading(col, text=col)
            widths[col].append(tkfont.Font().measure(col))
        for token in self.assembler.tokens:
            for problem in token.problems:
                item = self.tree.insert("", tkinter.END)
                values = (problem.name, problem.msg, problem.position.lineno,
                          problem.position.get_line(self.assembler.code))
                self.item_to_token[item] = token
                self.tree.item(item, values=values, tags=problem.cat)
                for col, v in zip(columns, values):
                    widths[col].append(bold_font.measure(v) + 15)

        for col, width in widths.items():
            self.tree.column(col, minwidth=max(width))

        self.tree.bind("<Double-Button-1>", self.double_click)
        self.tree.grid(row=0, column=0, sticky=tkinter.NE + tkinter.SW)

        self.xtreescroll = tkinter.Scrollbar(self.treeframe, orient=tkinter.HORIZONTAL, command=self.tree.xview)
        self.tree["xscrollcommand"] = self.xtreescroll.set
        self.xtreescroll.grid(row=1, column=0, sticky=tkinter.E + tkinter.W)
        self.ytreescroll = tkinter.Scrollbar(self.treeframe, command=self.tree.yview)
        self.tree["yscrollcommand"] = self.ytreescroll.set
        self.ytreescroll.grid(row=0, column=1, sticky=tkinter.N + tkinter.S)

        self.treeframe.pack(fill="both", expand=1)
        self.treeframe.rowconfigure(0, weight=1)
        self.treeframe.columnconfigure(0, weight=1)

    def buttonbox(self):
        button_frame = tkinter.Frame(self)
        b = tkinter.Button(button_frame, text="Back to code", command=self.cancel)
        b.pack()
        button_frame.pack()

        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)
        return button_frame

    def double_click(self, *discard):
        token = self.item_to_token[self.tree.focus()]
        self.master.goto_token(token)
        self.cancel()


class TooltipContentInterface:
    def __init__(self, tooltip, text_widget):
        self.tooltip = tooltip
        self.text_widget = text_widget

    @property
    def width(self):
        return int(self.tooltip["width"])

    @property
    def height(self):
        return int(self.tooltip["height"])

    def put(self, str, *tags, space=True):
        self.text_widget.insert(tkinter.END, str, tags)
        if space:
            self.text_widget.insert(tkinter.END, " ")

    def space(self):
        self.text_widget.insert(tkinter.END, " ")

    def type(self, str, space=True):
        self.put(str, "type", space=space)

    def value(self, str, space=True):
        self.put(str, "value", space=space)

    def text(self, str, space=True):
        self.put(str, space=space)

    def number(self, str, space=True):
        self.put(str, "number", space=space)

    def newline(self):
        self.text_widget.insert(tkinter.END, "\n")

    def error_header(self, str, space=True):
        self.put(str, "error_h", space=space)

    def error_detail(self, str, space=True):
        self.put(str, "error_d", space=space)

    def warning_header(self, str, space=True):
        self.put(str, "warning_h", space=space)

    def warning_detail(self, str, space=True):
        self.put(str, "warning_d", space=space)

    def goto_token(self, token):
        tag_name = "link_to_" + str(token.position)
        self.text_widget.tag_bind(tag_name, "<ButtonPress-1>", lambda e: self.tooltip.goto_token(token))
        self.text_widget.insert(tkinter.END, "line {}".format(token.position.lineno + 1), ("link", tag_name))


class Tooltip(tkinter.Toplevel):
    def __init__(self, master, interactives, position, content_interface=TooltipContentInterface):
        super().__init__(master, padx=1, pady=1, bg="black")
        self.overrideredirect(1)
        self.transient(master)
        self.frames = []
        self.text_widgets = []
        widths = []
        for interactive in interactives:
            frame = tkinter.Frame(self, padx=3, pady=3, bg="white")
            frame.pack(padx=1, pady=1)
            text_widget = tkinter.Text(frame, bg="white", width=50, height=4, border=0)

            self.setup_text(text_widget)

            interactive.set_interactive(content_interface(self, text_widget))
            lines = text_widget.get("1.0", tkinter.END).rstrip("\n").split("\n")
            text_widget["height"] = len(lines)
            widths.append(max(map(len, lines)))
            text_widget["state"] = "disabled"
            text_widget.pack()
            self.frames.append(frame)
            self.text_widgets.append(text_widget)

        width = max(widths)
        for tw in self.text_widgets:
            tw["width"] = width

        self.geometry("+{}+{}".format(*position))

        self.bind("<Enter>", self.enter)
        self.bind("<Leave>", self.leave)
        self.entered = False
        self.dying = False

    def setup_text(self, text_widget):
        normal_font = text_widget.cget("font")

        bold_font = tkfont.Font(text_widget, normal_font)
        bold_font["weight"] = "bold"

        underline_font = tkfont.Font(text_widget, normal_font)
        underline_font["underline"] = "1"

        text_widget.tag_configure("type", foreground=LABEL_COLOR)
        text_widget.tag_configure("value", font=bold_font)
        text_widget.tag_configure("number", foreground=NUMBER_COLOR)
        text_widget.tag_configure("link", font=underline_font, foreground="blue")
        text_widget.tag_configure("error_h", font=bold_font, foreground=ERROR_COLOR)
        text_widget.tag_configure("error_d", foreground=ERROR_COLOR)
        text_widget.tag_configure("warning_h", font=bold_font, foreground=WARNING_COLOR)
        text_widget.tag_configure("warning_d", foreground=WARNING_COLOR)
        self.orig_cursor = text_widget["cursor"]
        text_widget.tag_bind("link", "<Enter>", functools.partial(self.link_enter, text_widget))
        text_widget.tag_bind("link", "<Leave>", functools.partial(self.link_leave, text_widget))

    def link_enter(self, text_widget, event):
        text_widget["cursor"] = ""

    def link_leave(self, text_widget, event):
        text_widget["cursor"] = self.orig_cursor

    def enter(self, event):
        self.entered = True

    def leave(self, event):
        self.entered = False
        if self.dying:
            self.withdraw()
            self.destroy()

    def destroy_when_ready(self):
        inside_self = mouse_inside(self)
        if not self.entered and not inside_self:
            self.withdraw()
            self.destroy()
        else:
            self.dying = True

    def goto_token(self, token):
        self.master.goto_token(token)
        self.withdraw()
        self.destroy()


# From http://stackoverflow.com/a/13840728/3946766
class CustomText(tkinter.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Danger Will Robinson!
        # Heavy voodoo here. All widget changes happen via
        # an internal Tcl command with the same name as the
        # widget:  all inserts, deletes, cursor changes, etc
        #
        # The beauty of Tcl is that we can replace that command
        # with our own command. The following code does just
        # that: replace the code with a proxy that calls the
        # original command and then calls a callback. We
        # can then do whatever we want in the callback.
        private_callback = self.register(self._callback)
        self.tk.eval("""
            proc widget_proxy {actual_widget callback args} {

                # this prevents recursion if the widget is called
                # during the callback
                set flag ::dont_recurse(actual_widget)

                # call the real tk widget with the real args
                set result [uplevel [linsert $args 0 $actual_widget]]

                # call the callback and ignore errors, but only
                # do so on inserts, deletes, and changes in the
                # mark. Otherwise we'll call the callback way too
                # often.
                if {! [info exists $flag]} {
                    if {([lindex $args 0] in {insert replace delete}) ||
                        ([lrange $args 0 2] == {mark set insert})} {
                        # the flag makes sure that whatever happens in the
                        # callback doesn't cause the callbacks to be called again.
                        set $flag 1
                        catch {$callback $result {*}$args } callback_result
                        unset -nocomplain $flag
                    }
                }

                # return the result from the real widget command
                return $result
            }
            """)
        self.tk.eval("""
            rename {widget} _{widget}
            interp alias {{}} ::{widget} {{}} widget_proxy _{widget} {callback}
        """.format(widget=str(self), callback=private_callback))

    def _callback(self, result, *args):
        self.insert_moved_callback(result, *args)

    def set_insert_moved_callback(self, callable):
        self.insert_moved_callback = callable


class CodeEditor(tkinter.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.tooltip_token = self.tooltip = self.tooltip_reg = self.tooltip_xy = None
        self.highlighted_tokens = []
        self.highlight_reg = self.syntax_update_reg = None
        self.highlight_force = False

        self.hovered_token_mode = "cursor"

        # dict of address to breakpoint type
        self.breakpoints = collections.defaultdict(lambda: runner.BreakpointState.off)
        self.linebar_type = LineBarMode.address
        self.sidebar_markers = set()

        self.fname = None

        self.text = CustomText(self, bg="white", wrap=tkinter.NONE, undo=True)
        self.text.grid(column=1, row=0, sticky=tkinter.NE + tkinter.SW)

        self.sideframe = tkinter.Frame(self)
        self.sideframe.grid(column=0, row=0, sticky=tkinter.N + tkinter.S)
        self.sideframe.rowconfigure(0, weight=1)
        self.sideframe.columnconfigure(1, weight=1)

        self.linebar = tkinter.Text(self.sideframe, bg="white", width=2, wrap=tkinter.NONE)
        self.linebar.grid(column=0, row=0, sticky=tkinter.N + tkinter.S)
        self.linebar["yscrollcommand"] = functools.partial(self.yscroll, self.linebar, yxmode=True)

        self.breakbar = tkinter.Text(self.sideframe, bg="white", fg="red", width=2, wrap=tkinter.NONE)
        self.breakbar.grid(column=1, row=0, sticky=tkinter.N + tkinter.S)
        self.breakbar["yscrollcommand"] = functools.partial(self.yscroll, self.breakbar, yxmode=True)

        self.breakbar["state"] = "disabled"
        self.linebar["state"] = "disabled"

        self.vbar = tkinter.Scrollbar(self)
        self.vbar["command"] = functools.partial(self.yscroll, self.vbar)
        self.vbar.grid(column=2, row=0, sticky=tkinter.N + tkinter.S)

        self.hbar = tkinter.Scrollbar(self, orient=tkinter.HORIZONTAL,
                                      command=lambda *a: (self.nuke_tooltip(), self.text.xview(*a)))
        self.hbar.grid(column=0, row=1, columnspan=2, sticky=tkinter.E + tkinter.W)

        self.text["xscrollcommand"] = lambda y, x: (self.nuke_tooltip(),
                                                    self.hbar.set(y, x))
        self.text["yscrollcommand"] = functools.partial(self.yscroll, self.text, yxmode=True)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.assembler = assembler.Assembler()

        # Highlighting
        normal_font = self.text.cget("font")

        bold_font = tkfont.Font(self.text, normal_font)
        bold_font["weight"] = "bold"

        self.underline_font = tkfont.Font(self.text, normal_font)
        self.underline_font["underline"] = "1"

        self.underline_bold_font = tkfont.Font(self.text, bold_font)
        self.underline_bold_font["underline"] = "1"

        self.text.tag_configure("comment", foreground=COMMENT_COLOR, background="white")
        self.text.tag_configure("text", background="white")
        self.text.tag_configure("mnemonic", font=bold_font, background="white")
        self.text.tag_configure("label", font=bold_font,
                                foreground=LABEL_COLOR, background="white")
        self.text.tag_configure("labelref", foreground=LABEL_COLOR,
                                background="white")
        self.text.tag_configure("number", foreground=NUMBER_COLOR,
                                background="white")
        self.text.tag_configure("breakpoint", background=BREAKPOINT_BG_COLOR)

        self.breakbar.tag_configure("breakpoint", foreground="red", font=bold_font)

        self.text.tag_raise("sel")  # Otherwise selecting a label, mnemonic, etc. will results in a white background

        self.text.bind("<Motion>", self.motion)
        self.text.bind("<Leave>", self.leave)
        self.text.bind("<Enter>", self.enter)
        self.text.bind("<FocusOut>", self.leave)
        self.text.bind("<FocusIn>", self.enter)
        self.text.bind("<Control-d>", self.comment_line)
        self.text.bind("<Control-D>", self.decomment_line)
        self.text.bind("<Tab>", self.indent)
        self.text.bind("<Shift-Tab>", self.deindent)
        self.text.bind("<ISO_Left_Tab>", self.deindent)
        self.text.set_insert_moved_callback(self.insert_moved)

        self.tags = collections.defaultdict(list)
        self.token_to_tag = {}
        self.token_to_problem_tag = {}

        self.change_breakpoint_var = tkinter.StringVar()

        self.text_menu = tkinter.Menu(self.text, tearoff=0, takefocus=True)

        self.change_breakpoint_menu = tkinter.Menu(self.text_menu, tearoff=0)
        for option in runner.BreakpointState:
            self.change_breakpoint_menu.add_radiobutton(label=option.value.title(),
                                                        variable=self.change_breakpoint_var,
                                                        value=option.value,
                                                        command=self.do_change_breakpoint)

        self.breakbar.bind("<Button-3>", self.change_breakpoint)

        self.text_menu.add_cascade(label="Breakpoint", menu=self.change_breakpoint_menu)
        self.text_menu.add_separator()
        self.text_menu.add_command(label="Comment line", command=self.comment_line)
        self.text_menu.add_command(label="Decomment line", command=self.decomment_line)
        self.text_menu.add_separator()
        self.text_menu.add_command(label="Indent line", command=self.indent)
        self.text_menu.add_command(label="Deindent line", command=self.deindent)

        self.text.bind("<Button-3>", self.launch_text_menu)

    # File-based stuff

    def open(self, fname=None):
        logger.info("Open file")
        if not fname:
            fname = filedialog.askopenfilename(parent=self, defaultextension=".lmc",
                                               filetypes=[("LMC files", ".lmc"), ("All files", "*")])
        logger.info("Opening file {!r}", fname)
        self.fname = fname
        self.text.delete("1.0", tkinter.END)
        self.text.insert(tkinter.END, open(fname).read())
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.set_name()
        self.update_syntax()
        self.update_sidebars()
        self.text.yview_moveto(0.0)
        self.text.xview_moveto(0.0)

    def save(self, *discard):
        logger.info("Saving to file {!r}", self.fname)
        if not self.fname:
            return self.saveas()
        open(self.fname, "w").write(self.text.get("1.0", "end").rstrip("\n") + "\n")
        self.text.edit_modified(False)
        self.set_name()

    def saveas(self, *discard):
        fname = filedialog.asksaveasfilename(parent=self, defaultextension=".lmc",
                                             filetypes=[("LMC files", ".lmc"), ("All files", "*")])
        if fname:
            logger.info("Saving to file {!r}", self.fname)
            self.fname = fname
            self.save()
        else:
            logger.info("Saving cancelled")

    def close(self, *discard):
        logger.info("Closing")
        if self.text.edit_modified():
            logger.info("File has been modified and not saved")
            save = messagebox.askyesnocancel(title="Close file",
                                             message="File {} has unsaved changes. Save?".format(self.fname))
            if save is None:
                return False
            elif save is True:
                self.save()
            else:
                logger.warning("Changes not saved")
        return True

    def reload(self, *discard):
        logger.info("Reload")
        if self.close():
            self.open(self.fname)

    # Scrolling

    def yscroll(self, w, *a, yxmode=False):
        self.nuke_tooltip()
        if w not in (self.hbar, self.vbar) and yxmode:
            self.hbar.set(*a)
            self.vbar.set(*a)
        if yxmode:
            if w != self.text:
                self.text.yview_moveto(a[0])
            if w != self.linebar:
                self.linebar.yview_moveto(a[0])
            if w != self.breakbar:
                self.breakbar.yview_moveto(a[0])
        else:
            if w != self.text:
                self.text.yview(*a)
            if w != self.linebar:
                self.linebar.yview(*a)
            if w != self.breakbar:
                self.breakbar.yview(*a)

    # Syntax highlighting

    def create_tag(self, token):
        name = "token_at_" + str(token.position)
        self.tags[name].clear()
        self.text.tag_configure(name, background=HIGHLIGHT_COLOR,
                                foreground="black")
        self.text.tag_lower(name)
        self.tags[name].append(token)
        self.token_to_tag[token] = name
        return name

    def create_problem_tag(self, token):
        if token.problems:
            pname = "problems_at_" + str(token.position)
            self.token_to_problem_tag[token] = pname
            self.text.tag_configure(pname, font=self.underline_font,
                                    foreground=ERROR_COLOR if token.in_error else WARNING_COLOR)
            self.text.tag_raise(pname)
            return pname

    def update_syntax(self):
        self.dehighlight()
        for tag in self.token_to_tag.values():
            self.text.tag_delete(tag)
        for tag in self.token_to_problem_tag.values():
            self.text.tag_delete(tag)
        for tag in self.text.tag_names():
            self.text.tag_remove(tag, "1.0", tkinter.END)
        code = self.text.get("1.0", "end")[:-1]
        if code:
            self.assembler.update_code(code)
            self.assembler.assemble()
            self.tags.clear()
            self.token_to_tag.clear()
            for line in self.assembler.parsed_code:
                for token in line:
                    start = "{}.{}".format(token.position.lineno + 1,
                                           token.position.start_index)
                    end = "{}.{}".format(token.position.lineno + 1,
                                         token.position.end_index)
                    self.text.tag_add(token.style, start, end)
                    self.text.tag_add(self.create_tag(token), start, end)
                    p = self.create_problem_tag(token)
                    if p:
                        self.text.tag_add(p, start, end)
        self.highlight()
        self.update_sidebars()

    def set_linebar_mode(self, mode):
        if mode is LineBarMode.none:
            self.linebar.grid_forget()
            self.sideframe.columnconfigure(0, weight=0)
        else:
            self.linebar.grid(column=0, row=0, sticky=tkinter.N + tkinter.S)
            self.sideframe.columnconfigure(0, weight=1)
        self.update_sidebars()

    def breakpoints_changed(self):
        pass

    def update_sidebars(self):
        self.breakbar["state"] = "normal"
        self.linebar["state"] = "normal"
        current_lines = int(self.text.index("end").split(".")[0]) - 1
        new_to_old = {}
        stat = {}
        new_breakpoints = collections.defaultdict(lambda: runner.BreakpointState.off)
        for m in sorted(self.sidebar_markers, key=lambda a: int(a.split("_")[1])):
            new = int(self.text.index(m).split(".")[0]) - 1
            old = int(m[m.rfind("_") + 1:])
            stat[m] = old, new
            if new not in new_to_old:
                new_to_old[new] = old
                new_breakpoints[new] = self.breakpoints[old]
        if self.breakpoints != new_breakpoints:
            logger.debug("Breakpoints changed")
            self.breakpoints = new_breakpoints
            self.breakpoints_changed()

        for m in self.sidebar_markers:
            self.text.mark_unset(m)
        self.sidebar_markers.clear()
        for line in range(current_lines):
            self.sidebar_markers.add("sidebarmark_" + str(line))
            self.text.mark_set("sidebarmark_" + str(line), str(line + 1) + ".0")

        # Preserve scrolling position
        posx, posy = self.text.xview()[0], self.text.yview()[0]

        # Linebar
        if self.linebar_type is not LineBarMode.none:
            self.linebar.delete("1.0", "end")
            if self.linebar_type is LineBarMode.lineno:
                sideinfo = list(map(str, range(current_lines)))
            elif self.linebar_type is LineBarMode.address:
                sideinfo = []
                if hasattr(self.assembler, "parsed_code"):
                    for lineno in range(current_lines):
                        if lineno in new_to_old and new_to_old[lineno] < len(self.assembler.parsed_code):
                            tokens = self.assembler.parsed_code[new_to_old[lineno]]
                        else:
                            tokens = []
                        mnems = [i for i in tokens if isinstance(i, assembler.Mnemonic)]
                        if mnems:
                            sideinfo.append(str(mnems[0].address))
                        else:
                            sideinfo.append("")
                while len(sideinfo) < current_lines:
                    sideinfo.append("")
            self.linebar.insert("end", "\n".join(sideinfo))
            self.linebar["width"] = max(map(len, sideinfo))

        # Breakpoint bar
        self.breakbar.delete("1.0", "end")
        breakinfo = []
        for lineno in range(current_lines):
            short = BREAKPOINT_SHORTENED[self.breakpoints[lineno]]
            if short:
                self.breakbar.insert("end", short, "breakpoint")
            if lineno != current_lines - 1:
                self.breakbar.insert("end", "\n")

        self.text.tag_remove("breakpoint", "1.0", "end")
        for lineno, type in self.breakpoints.items():
            if type != runner.BreakpointState.off:
                self.text.tag_add("breakpoint", "{}.0".format(lineno + 1), "{}.0".format(lineno + 2))

        self.breakbar["state"] = "disabled"
        self.linebar["state"] = "disabled"

        self.yscroll(None, posy, posx, yxmode=True)

    def change_breakpoint(self, event):
        self.breakbar.mark_set("insert", "current")
        self.change_breakpoint_menu.tk_popup(event.x_root, event.y_root)

    def launch_text_menu(self, event):
        self.text.mark_set("insert", "current")
        self.breakbar.mark_set("insert", self.text.index("current").split(".")[0] + ".0")
        self.text_menu.tk_popup(event.x_root, event.y_root)

    def do_change_breakpoint(self):
        value = self.change_breakpoint_var.get()
        lineno = int(self.breakbar.index("insert").split(".")[0]) - 1
        self.breakpoints[lineno] = runner.BreakpointState(value)
        self.breakpoints_changed()
        self.update_sidebars()

    def start_syntax_update_timer(self):
        if self.syntax_update_reg is not None:
            self.stop_syntax_update_timer()
        logger.debug("Starting syntax update timer")
        self.syntax_update_reg = self.after(HOVER_TIME, self.update_syntax)

    def stop_syntax_update_timer(self):
        logger.debug("Stopped syntax update timer")
        self.after_cancel(self.syntax_update_reg)
        self.syntax_update_reg = None

    # Highlighting and tooltip utils

    def get_tags_at_index(self, index, tags=None):
        tags = self.text.tag_names() if tags is None else tags
        ret = []
        for tag in tags:
            for start, end in grouper(self.text.tag_ranges(tag), 2):
                if self.text.compare(start, "<=", index) and self.text.compare(index, "<", end):
                    ret.append(tag)
        return ret

    def get_hovered_token(self):
        if self.hovered_token_mode == "cursor":
            if not mouse_inside(self):
                logger.debug("Pointer outside widget")
                return
            logger.debug("Pointer not outside widget")
            tag = self.get_tags_at_index("current", self.token_to_tag.values())
        else:
            tag = self.get_tags_at_index("insert", self.token_to_tag.values())
        if len(tag) > 1:
            raise RuntimeError("Hovering over more than one tag")
        if not tag:
            return
        tag = tag[0]
        pos = assembler.Position.from_string(tag.replace("token_at_", ""))
        return self.assembler.get_token_at(pos)

    # Highlighting functions

    def highlight(self, force=False):
        """
        Moves highlighting to the next tag. When no tag is being hovered over
        no dehighlighting will take place unless force is True.
        """
        logger.debug("Updating highlighting")
        force = force or self.highlight_force
        token = self.get_hovered_token()
        if isinstance(token, assembler.InteractiveToken):
            self.dehighlight()
            logger.debug("Highlighting {}", token)
            self.text.tag_raise(self.token_to_tag[token])
            self.highlighted_tokens.append(token)
            if isinstance(token, assembler.Label):
                for i in token.refs:
                    self.text.tag_raise(self.token_to_tag[i])
                    self.highlighted_tokens.append(i)
            elif isinstance(token, assembler.LabelRef) and token.label:
                self.text.tag_raise(self.token_to_tag[token.label])
                self.highlighted_tokens.append(token.label)
                for i in token.label.refs:
                    self.text.tag_raise(self.token_to_tag[i])
                    self.highlighted_tokens.append(i)
        else:
            if force:
                self.dehighlight()
            logger.debug("Nothing to highlight {}", token)

    def dehighlight(self):
        while self.highlighted_tokens:
            self.text.tag_lower(self.token_to_tag[self.highlighted_tokens.pop()])

    def start_highlight_timer(self, force=False):
        if self.highlight_reg is not None:
            self.stop_highlight_timer()
        logger.debug("Starting highlighting timer")
        self.highlight_force = force
        self.highlight_reg = self.after(HOVER_TIME, self.highlight)

    def stop_highlight_timer(self):
        logger.debug("Stopped highlighting timer")
        self.after_cancel(self.highlight_reg)
        self.highlight_reg = None

    # Tooltip functions

    def make_tooltip(self, token):
        if self.tooltip:
            self.nuke_tooltip()
        if token and token.problems or isinstance(token, assembler.InteractiveToken):
            logger.debug("Making tooltip")
            x, y = self.text.winfo_pointerx(), self.text.winfo_pointery()
            pos = x + 20, y - 35
            interactives = sorted(token.problems, key=lambda prob: prob.cat)
            if isinstance(token, assembler.InteractiveToken):
                interactives.append(token)
            self.tooltip = Tooltip(self, interactives, pos)

    def nuke_tooltip(self, *discard_args):
        logger.debug("Nukeing tooltip")
        if self.tooltip:
            self.tooltip.destroy_when_ready()
            self.tooltip = None
            self.tooltip_token = None
        self.stop_tooltip_timer()

    def update_tooltip(self):
        logger.debug("Updating tooltip")
        token = self.get_hovered_token()
        if token != self.tooltip_token:
            self.make_tooltip(token)
            self.tooltip_token = token

    def start_tooltip_timer(self):
        if self.tooltip_reg is not None:
            self.stop_tooltip_timer()
        logger.debug("Started tooltip timer")
        self.tooltip_reg = self.after(HOVER_TIME, self.update_tooltip)

    def stop_tooltip_timer(self):
        if self.tooltip_reg:
            logger.debug("Stopped tooltip timer")
            self.after_cancel(self.tooltip_reg)
            self.tooltip_reg = None

    # Event callbacks

    def motion(self, event):
        logger.debug("Motion at {}, {}", event.x, event.y)
        self.hovered_token_mode = "cursor"
        self.start_highlight_timer()
        self.start_tooltip_timer()

    def insert_moved(self, *stuff):
        logger.debug("Insert Moved {}", stuff)
        self.hovered_token_mode = "insert"
        self.highlight(force=True)
        self.nuke_tooltip()
        self.start_highlight_timer(force=True)
        if stuff[1] != "mark":
            self.start_syntax_update_timer()
            self.update_sidebars()
        self.set_name()

    def leave(self, event):
        logger.debug("Leave at {},{}", event.x, event.y)
        self.hovered_token_mode = "cursor"
        self.nuke_tooltip()

    def enter(self, event):
        logger.debug("Enter at {}, {}", event.x, event.y)
        self.hovered_token_mode = "cursor"
        self.start_tooltip_timer()
        self.start_highlight_timer()

    def goto_token(self, token):
        row = token.position.lineno + 1
        col = token.position.start_index
        rc = "{}.{}".format(row, col)
        self.text.see(rc)
        self.text.mark_set("insert", rc)
        self.highlight(token)

    @property
    def display_name(self):
        if self.fname:
            name = os.path.relpath(self.fname, os.curdir)
        else:
            name = "New file"
        if self.text.edit_modified():
            name = "*[{}]".format(name)
        return name

    def set_name(self):
        logger.debug("Setting name")
        if isinstance(self.master, ttk.Notebook):
            if str(self) in self.master.tabs():
                self.master.tab(self, text=self.display_name)
            if hasattr(self.master.master, "on_tab_change"):
                self.master.master.on_tab_change()

    def comment_line(self, *discard):
        logger.info("Commentising line")
        current_line = self.text.index("insert").split(".")[0]
        self.text.insert("{}.0".format(current_line), "# ")
        return "break"

    def decomment_line(self, *discard):
        logger.info("Decommentising line")
        current_line = self.text.index("insert").split(".")[0]
        line = self.text.get("{}.0".format(current_line), "{}.end".format(current_line))
        for i, c in enumerate(line):
            if c == "#":
                self.text.delete("{}.{}".format(current_line, i))
                if i + 1 < len(line) and line[i + 1] == " ":
                    self.text.delete("{}.{}".format(current_line, i))
                break
            elif c.isspace():
                pass
            else:
                break
        return "break"

    def indent(self, *discard):
        lineno, charno = map(int, self.text.index("insert").split("."))
        line = self.text.get("{}.0".format(lineno), "{}.end".format(lineno))
        while charno != len(line) and line[charno] == " ":
            charno += 1
        self.text.mark_set("insert", "{}.{}".format(lineno, charno))
        if charno < 8:
            spaces = 8 - charno
        elif charno < 12:
            spaces = 12 - charno
        elif charno < 20:
            spaces = 20 - charno
        else:
            spaces = 4
        logger.info("Indenting line by {} to {}", spaces, charno + spaces)
        self.text.insert("insert", " " * spaces)
        return "break"

    def deindent(self, *discard):
        lineno = int(self.text.index("insert").split(".")[0])
        line = self.text.get("{}.0".format(lineno), "{}.end".format(lineno))
        charno = 0
        while charno != len(line) and line[charno] == " ":
            charno += 1
        self.text.mark_set("insert", "{}.{}".format(lineno, charno))
        if charno > 20:
            spaces = charno % 4 or 4
        elif charno > 12:
            spaces = charno - 12
        elif charno > 8:
            spaces = charno - 8
        else:
            spaces = charno
        logger.info("Indenting line from {} by {} to {}", charno, spaces, charno - spaces)
        self.text.delete("insert-{}c".format(spaces), "insert")
        return "break"

    def show_breakpoints(self, value):
        if value:
            self.text.tag_configure("breakpoint", background=BREAKPOINT_BG_COLOR)
        else:
            self.text.tag_configure("breakpoint", background="white")

    def show_problems(self):
        ProblemsDialog(self, self.assembler)

if __name__ == "__main__":
    import sys
    import tkinter.ttk as ttk
    root = tkinter.Tk(className='ToolTip-demo')
    t = ttk.Notebook(root)
    t.grid(sticky=tkinter.NE + tkinter.SW)
    ce = CodeEditor(t)
    t.add(ce, text="Hi")

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    ce.open()
    ProblemsDialog(ce, ce.assembler)
    root.mainloop()
