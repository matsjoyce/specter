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
import codemode
import runmode

__author__ = "Matthew Joyce"
__copyright__ = "Copyright 2013"
__credits__ = ["Matthew Joyce"]
__license__ = "GPL3"
__version__ = "1.1.0"
__maintainer__ = "Matthew Joyce"
__email__ = "matsjoyce@gmail.com"
__status__ = "Development"


class GUIManager(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.title("yaplmc")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.menu = tkinter.Menu(self)
        self["menu"] = self.menu

        self.code_mode = codemode.CodeMode(self)
        self.run_mode = runmode.RunMode(self)

        self.code_mode.grid(row=0, column=0, sticky=tkinter.NE + tkinter.SW)
        self.code_mode.do_bindings()
        self.code_mode.focus_set()
        self.update_menu(self.code_mode.menus)

    def update_menu(self, menus):
        end = self.menu.index(tkinter.END)
        for opts in menus:
            self.menu.add_cascade(**opts)
        self.menu.delete(0, end)

    def runmode(self, *discard):
        self.code_mode.grid_forget()
        self.code_mode.do_unbindings()

        self.run_mode.grid(row=0, column=0, sticky=tkinter.NE + tkinter.SW)
        self.run_mode.do_bindings()
        self.run_mode.focus_set()
        self.update_menu(self.run_mode.menus)

        ce = self.code_mode.current_codeeditor()
        self.run_mode.set_code(ce.assembler, ce.fname)
        self.run_mode.set_breakpoints(self.code_mode.current_codeeditor().breakpoints)
        self.run_mode.reset()

    def codemode(self, *discard):
        self.run_mode.grid_forget()
        self.run_mode.do_unbindings()

        self.code_mode.grid(row=0, column=0, sticky=tkinter.NE + tkinter.SW)
        self.code_mode.do_bindings()
        self.code_mode.focus_set()
        ce = self.code_mode.current_codeeditor()
        ce.breakpoints = self.run_mode.code_editor.breakpoints
        ce.update_sidebars()
        self.update_menu(self.code_mode.menus)


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
    t = GUIManager()
    t.mainloop()
