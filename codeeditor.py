import tkinter
from tkinter import scrolledtext as stext, font as tkfont
import functools
import collections
import assembler
import re


# Colors from Kate theme
LABEL_COLOR = "#006E28"
COMMENT_COLOR = "#898887"
NUMBER_COLOR = "#B08000"
HIGHLIGHT_COLOR = "#FBFA96"

HOVER_TIME = 500 * 2


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
    def __init__(self, master, interactives, position):
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

            normal_font = text_widget.cget("font")

            bold_font = tkfont.Font(text_widget, normal_font)
            bold_font["weight"] = "bold"

            underline_font = tkfont.Font(text_widget, normal_font)
            underline_font["underline"] = "1"

            text_widget.tag_configure("type", foreground=LABEL_COLOR)
            text_widget.tag_configure("value", font=bold_font)
            text_widget.tag_configure("number", foreground=NUMBER_COLOR)
            text_widget.tag_configure("link", font=underline_font, foreground="blue")
            text_widget.tag_configure("error_h", font=bold_font, foreground="red")
            text_widget.tag_configure("error_d", foreground="red")
            text_widget.tag_configure("warning_h", font=bold_font, foreground="orange")
            text_widget.tag_configure("warning_d", foreground="orange")
            self.orig_cursor = text_widget["cursor"]
            text_widget.tag_bind("link", "<Enter>", functools.partial(self.link_enter, text_widget))
            text_widget.tag_bind("link", "<Leave>", functools.partial(self.link_leave, text_widget))

            interactive.set_interactive(TooltipContentInterface(self, text_widget))
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
        if not self.entered:
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
        self.highlighted_token = self.highlight_reg = None

        self.hovered_token_mode = "cursor"

        self.text = CustomText(self, bg="white", wrap=tkinter.NONE)
        self.text.grid(column=0, row=0, sticky=tkinter.NE + tkinter.SW)

        self.vbar = tkinter.Scrollbar(self, command=self.text.yview)
        self.vbar.grid(column=1, row=0, sticky=tkinter.N + tkinter.S)
        self.hbar = tkinter.Scrollbar(self, orient=tkinter.HORIZONTAL,
                                      command=self.text.xview)
        self.hbar.grid(column=0, row=1, sticky=tkinter.E + tkinter.W)
        self.text["xscrollcommand"] = lambda *a: (self.nuke_tooltip(),
                                                  self.hbar.set(*a))
        self.text["yscrollcommand"] = lambda *a: (self.nuke_tooltip(),
                                                  self.vbar.set(*a))

        self.columnconfigure(0, weight=1)
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

        self.text.tag_configure("comment", foreground=COMMENT_COLOR)
        self.text.tag_configure("text")
        self.text.tag_configure("mnemonic", font=bold_font, background="white")
        self.text.tag_configure("label", font=bold_font,
                                foreground=LABEL_COLOR, background="white")
        self.text.tag_configure("labelref", foreground=LABEL_COLOR,
                                background="white")
        self.text.tag_configure("number", foreground=NUMBER_COLOR,
                                background="white")

        self.text.bind("<Motion>", self.motion)
        self.text.bind("<Leave>", self.leave)
        self.text.bind("<Enter>", self.enter)
        self.text._root().bind("<FocusOut>", self.leave)
        self.text._root().bind("<FocusIn>", self.enter)
        self.text.set_insert_moved_callback(self.insert_moved)

        self.tags = collections.defaultdict(list)
        self.token_to_tag = {}
        self.token_to_problem_tag = {}

    def update_code(self, code):
        self.assembler.update_code(code)
        self.assembler.assemble()
        self.tags.clear()
        self.token_to_tag.clear()
        self.text.delete("1.0", tkinter.END)
        self.text.insert(tkinter.END, self.assembler.raw_code)
        self.update_syntax()

    def create_tag(self, token):
        if isinstance(token, assembler.Label):
            name = "label_at_" + str(token.position)
        if isinstance(token, assembler.LabelRef):
            if token.label is not None:
                name = "label_at_" + str(token.label.position)
            else:
                name = "labelref_at_" + str(token.position)
        elif isinstance(token, assembler.Mnemonic):
            name = "mnem_at_" + str(token.position)
        elif isinstance(token, assembler.Number):
            name = "num_at_" + str(token.position)
        if name not in self.tags:
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
            self.token_to_problem_tag[pname] = token
            self.text.tag_configure(pname, font=self.underline_font,
                                    foreground="red" if token.in_error else "orange")
            self.text.tag_raise(pname)
            return pname

    def update_syntax(self):
        for line in self.assembler.parsed_code:
            for token in line:
                start = "{}.{}".format(token.position.lineno + 1,
                                       token.position.start_index)
                end = "{}.{}".format(token.position.lineno + 1,
                                     token.position.end_index)
                self.text.tag_add(token.style, start, end)
                if isinstance(token, assembler.InteractiveToken):
                    self.text.tag_add(self.create_tag(token), start, end)
                p = self.create_problem_tag(token)
                if p:
                    self.text.tag_add(p, start, end)

    def get_hovered_token(self):
        if self.hovered_token_mode == "cursor":
            if not (0 <= (self.text.winfo_pointerx() - self.text.winfo_rootx()) < self.text.winfo_width()
                    and 0 <= (self.text.winfo_pointery() - self.text.winfo_rooty()) < self.text.winfo_height()):
                print("ght: pointer outside widget")
                return
            print("ght: pointer !outside widget")
            row, col = map(int, self.text.index("current").split("."))
            return self.assembler.get_token_at(row - 1, col)
        else:
            row, col = map(int, self.text.index("insert").split("."))
            return self.assembler.get_token_at(row - 1, col)

    # Highlighting functions

    def highlight(self, force=False):
        """
        Moves highlighting to the next tag. When no tag is being hovered over
        no dehighlighting will take place unless force is True.
        """
        print("Updating h")
        force = force or self.highlight_force
        token = self.get_hovered_token()
        if isinstance(token, assembler.InteractiveToken):
            if self.highlighted_token:
                self.dehighlight()
            print("Highlighting", token)
            self.text.tag_raise(self.token_to_tag[token])
            self.highlighted_token = token
        else:
            if self.highlighted_token and force:
                self.dehighlight()
            print("Nothing to highlight", token)

    def dehighlight(self):
        if self.highlighted_token is not None:
            print("Dehighlighting", self.highlighted_token)
            self.text.tag_lower(self.token_to_tag[self.highlighted_token])
            self.highlighted_token = None

    def start_highlight_timer(self, force=False):
        if self.highlight_reg is not None:
            self.stop_highlight_timer()
        print("Starting h timer")
        self.highlight_force = force
        self.highlight_reg = self.after(HOVER_TIME, self.highlight)

    def stop_highlight_timer(self):
        print("Stopped h timer")
        self.after_cancel(self.highlight_reg)
        self.highlight_reg = None

    # Tooltip functions

    def make_tooltip(self, token):
        if self.tooltip:
            self.nuke_tooltip()
        if token and token.problems or isinstance(token, assembler.InteractiveToken):
            print("Making tooltip")
            m = re.match("(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", self._root().geometry())
            x, y = self.text.winfo_pointerx() - self.text.winfo_rootx(), self.text.winfo_pointery() - self.text.winfo_rooty()
            pos = x + int(m.group(3)) + 30, y + int(m.group(4))
            interactives = sorted(token.problems, key=lambda prob: prob.cat)
            if isinstance(token, assembler.InteractiveToken):
                interactives.append(token)
            self.tooltip = Tooltip(self, interactives, pos)
        else:
            print("Did not make tooltip as nothing to show")

    def nuke_tooltip(self, *discard_args):
        print("Nukeing tooltip")
        if self.tooltip:
            self.tooltip.destroy_when_ready()
            self.tooltip = None
            self.tooltip_token = None
        self.stop_tooltip_timer()

    def update_tooltip(self):
        print("Updating tooltip")
        token = self.get_hovered_token()
        print(token, self.tooltip_token)
        if token != self.tooltip_token:
            self.make_tooltip(token)
            self.tooltip_token = token

    def start_tooltip_timer(self):
        if self.tooltip_reg is not None:
            self.stop_tooltip_timer()
        print("Started tooltip timer")
        self.tooltip_reg = self.after(HOVER_TIME, self.update_tooltip)

    def stop_tooltip_timer(self):
        if self.tooltip_reg:
            print("Stopped tooltip timer")
            self.after_cancel(self.tooltip_reg)
            self.tooltip_reg = None

    # Event callbacks

    def motion(self, event):
        print("Motion", event.x, event.y)
        self.hovered_token_mode = "cursor"
        self.start_highlight_timer()
        self.start_tooltip_timer()

    def insert_moved(self, *stuff):
        print("Insert Moved", stuff)
        self.hovered_token_mode = "insert"
        self.highlight(force=True)
        self.nuke_tooltip()
        self.start_highlight_timer(force=True)

    def leave(self, event):
        print("Leave", event.x, event.y, self)
        self.hovered_token_mode = "cursor"
        self.nuke_tooltip()

    def enter(self, event):
        print("Enter", event.x, event.y, self)
        self.hovered_token_mode = "cursor"
        self.start_tooltip_timer()
        self.start_highlight_timer()

    def goto_token(self, token):
        row = token.position.lineno + 1
        col = token.position.start_index
        rc = "{}.{}".format(row, col)
        self.text.see(rc)
        self.text.mark_set("insert", rc)
        if token in self.token_to_tag:
            self.highlight_tag(self.token_to_tag[token])


if __name__ == "__main__":
    import sys
    root = tkinter.Tk(className='ToolTip-demo')
    ce = CodeEditor(root)
    ce.update_code(open(sys.argv[1]).read())
    ce.grid(sticky=tkinter.NE + tkinter.SW)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.mainloop()
