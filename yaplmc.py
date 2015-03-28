#!/usr/bin/env python3
"""
Yet Another Python Little Man Computer written in Python 3
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
import logging
import sys

import assembler
import runner
import codemode
import runmode
import colored_logger

__author__ = "Matthew Joyce"
__copyright__ = "Copyright 2013"
__credits__ = ["Matthew Joyce"]
__license__ = "GPL3"
__version__ = "1.1.0"
__maintainer__ = "Matthew Joyce"
__email__ = "matsjoyce@gmail.com"
__status__ = "Development"

logger = logging.getLogger()
logger.name = __name__


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

    def set_title(self, txt):
        self.title("yaplmc - " + txt)


def main_gui(args_from_parser):
    t = GUIManager()
    t.mainloop()
    return 0


def main_cli(args_from_parser):
    try:
        with open(args_from_parser.file or input("Filename: ")) as f:
            code = f.read()
    except IOError as e:
        print("Could not open file:", e)
        return 1
    print("Assembling...")
    assem = assembler.Assembler()
    assem.update_code(code)
    assem.assemble()
    if assem.problems():
        print("\n".join(i.show(code.splitlines()) for i in assem.problems()))
    if assem.in_error:
        print("Assembly failed")
        return 1
    print("Assembly succeeded")
    machine_code, code_length = (assem.machine_code,
                                 assem.machine_code_length)
    if args_from_parser.debug:
        print("Code:")
        print(" ".join(map(str, machine_code[:code_length])))
    print("Loading code...")
    run = runner.Runner(lambda x: print(">>>", x))
    run.load_code(assem)
    print("Running...")
    while run.halt_reason != runner.HaltReason.hlt:
        if args_from_parser.debug >= 2:
            print("Memory:")
            print(*[i.value for i in run.memory])
            print("Executing instruction {:03} at {:03}".format(run.memory[run.counter].value, run.counter))
        try:
            run.next_step()
        except RuntimeError as e:
            print("Error", e.args[0])
        if run.halt_reason == runner.HaltReason.input:
            #try:
                run.give_input(int(input("<<< ")))
            #except (KeyboardInterrupt, EOFError):
                #break
        if args_from_parser.debug >= 1:
            print(run.hint)
    return 0


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
    arg_parser.add_argument("-V", "--version", version="yaplmc " + __version__,
                            action="version")
    arg_parser.add_argument("-b", "--buginfo", help="generate information"
                            " about any crashed", action="store_true")

    cli_group = arg_parser.add_argument_group("CLI options (all options only"
                                              " active when -c or --cli used)")
    cli_group.add_argument("-c", "--cli", help="use CLI mode",
                           action="store_true")
    cli_group.add_argument("-d", "--debug", help="debug level"
                           " (repeat for more info, 3 is the max)",
                           action="count", default=0)

    args_from_parser = arg_parser.parse_args()

    if args_from_parser.licence:
        print(__doc__.strip())

    logger.setLevel(logging.DEBUG)

    log_formatter = colored_logger.ColoredFormatter()

    stream_hndlr = logging.StreamHandler(sys.stdout)
    stream_hndlr.setFormatter(log_formatter)
    stream_hndlr.setLevel(logging.CRITICAL if args_from_parser.cli else logging.INFO)
    logger.addHandler(stream_hndlr)

    if args_from_parser.buginfo:
        import inquisitor
        exc_catcher = inquisitor.Inquisitor()
        log_col = inquisitor.collectors.LoggingCollector()
        log_col.setFormatter(log_formatter)
        exc_catcher.collectors.append(log_col)
        logger.addHandler(log_col)
        rh = inquisitor.utils.ReportManager("bug_info", "bug_info_{no}.xml",
                                            max_files_size=inquisitor.utils.MiB)
        xml_h = inquisitor.handlers.XMLFileDumpHandler(reportmanager=rh)
        log_h = inquisitor.handlers.LogTracebackHandler()
        exc_catcher.handlers = [xml_h, log_h]
        exc_catcher.watch_sys_excepthook()
        exc_catcher.watch_tkinter_report_callback_exception()
        if args_from_parser.cli:
            tk_h = inquisitor.handlers.StreamMessageHandler()
            exc_catcher.handlers.append(tk_h)
        else:
            tk_h = inquisitor.handlers.TkinterMessageHandler()
            exc_catcher.handlers.append(tk_h)

    if args_from_parser.cli:
        exit(main_cli(args_from_parser))
    else:
        exit(main_gui(args_from_parser))
