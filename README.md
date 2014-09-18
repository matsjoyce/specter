pyLMC
=====

A Little Man Computer simulator written in Python 3

Usage
=====

Command Line
------------

 - `./LMC.py`
 - Type in filename (or use `-f` command line flag)
 - Have fun!

GUI
---

 - `./LMC_gui.py`
 - Select file
 - Press `Run`
 - Press `Run to Halt`
 - Have fun!
 - When the `input` field is "selected", type in a integer value between `-500` and `499` and press `Submit`.

Examples
========

Included examples (in the `examples` folder), sorted by subjective, relative measure:

 - Easy
   - `add.lmc` - Add two numbers
   - `echo.lmc` - Echos user input until the input == 0
   - `infinite.lmc` - Prints 1 for ever
   - `sub.lmc` - Subtract two numbers
 - Medium
   - `counter.lmc` - Counts down from the users input
   - `divide.lmc` - Divide two numbers
   - `multiply.lmc` - Multiply two numbers
   - `square.lmc` - Squares input until input == 0
 - Hard
   - `fib.lmc` - Little man's fibonacci, a traditional challenge
   - `test.lmc` - A self-test

Advanced Usage
==============

General
-------

 - Memory is stored in a decimalised twos-complement (`999` == `-1`, `998` == `-2`, ..., `500` == `-500`, `499` == `499`, ..., `0` == `0`)

Command Line Specific
---------------------

 - Usage string: `LMC.py [-h] [-d DEBUG] [-f FILE]`
 - `-d` flag - Specifies debug level
   - `0` - no debug output (default)
   - `1` - low debug output
   - `2` - medium debug output
   - `3` or higher - high debug output
 
GUI Specific
------------

 - `Run one step` -  Execute next instruction, then halt. Can be presses multiple times for "step though" effect.
 - `Reset` - Reset registers and memory. Equivalent to restarting the program.
 - `Exit` - Does what is says on the packet.
