import enum


class BreakpointState(enum.Enum):
    off = "off"
    on_execute = "execute"
    on_read = "read"
    on_write = "write"


class ValueState(enum.Enum):
    normal = "nothing"
    read = "read"
    written = "written"
    executed = "executed"
    next_exec = "executed next"


class HaltReason(enum.Enum):
    hlt = "hlt"
    input = "input"
    step = "step"
    breakpoint = "breakpoint"


def int_to_complement(i):
    return (1000 + i) % 1000


def int_from_complement(i):
    return i - 1000 if i >= 500 else i


class MemoryValue:
    def __init__(self, address, token=None):
        self.address = address
        self.token = token
        self.state = ValueState.normal
        self.breakpoint = BreakpointState.off
        self.value = token.machine_instruction() if token else 0

    def reset(self):
        self.value = self.token.machine_instruction() if self.token else 0
        self.state = ValueState.normal

    def reset_state(self):
        self.state = ValueState.normal

    def write(self, value):
        self.state = ValueState.written
        self.value = int_to_complement(value)

    def read(self):
        self.state = ValueState.read
        return self.value

    def execute(self):
        self.state = ValueState.executed
        return self.value

    def next_exec(self):
        self.state = ValueState.next_exec

    def hit_breakpoint(self):
        if self.breakpoint == BreakpointState.off:
            return False
        elif self.breakpoint == BreakpointState.on_execute:
            return self.state == ValueState.executed
        elif self.breakpoint == BreakpointState.on_read:
            return self.state == ValueState.read
        elif self.breakpoint == BreakpointState.on_write:
            return self.state == ValueState.written

    def set_interactive(self, tooltip):
        if self.token:
            tooltip.type("mnemonic")
            tooltip.value(self.token.text)
            tooltip.newline()

        tooltip.text("Memory value:")
        tooltip.number("{:03}".format(self.value))
        tooltip.newline()

        tooltip.text("Last action:")
        tooltip.action(self.state)
        tooltip.newline()

        if self.breakpoint != BreakpointState.off:
            tooltip.text("Break on:")
            tooltip.action(self.breakpoint.value)


class Runner:
    def __init__(self, give_output):
        self.give_output = give_output

    def load_code(self, assembler):
        self.assembler = assembler
        self.memory = []
        self.assembler.assemble()
        for i, v in enumerate(self.assembler.instructions):
            self.memory.append(MemoryValue(i, v))
        while len(self.memory) < 100:
            self.memory.append(MemoryValue(len(self.memory)))
        self.accumulator = MemoryValue("accumulator")
        self.breakables = self.memory + [self.accumulator]
        self.reset()

    def load_breakpoints(self, brps):
        brps = sorted(brps.items())
        for instr in self.assembler.instructions:
            value = self.memory[instr.address]
            while brps and brps[0][0] <= instr.position.lineno:
                value.breakpoint = brps.pop(0)[1]
        print("BREAKPOINTS")
        for i, value in enumerate(self.memory):
            print(str(i).zfill(3), value.breakpoint)

    def give_input(self, i):
        if self.halt_reason == HaltReason.input:
            self.accumulator.write(i)
            self.halt_reason = HaltReason.breakpoint if self.hit_breakpoints() else HaltReason.step

    def hit_breakpoints(self):
        return [m for m in self.breakables if m.hit_breakpoint()]

    def next_step(self):
        for m in self.memory:
            m.reset_state()
        instruction = self.memory[self.counter].execute()
        self.instruction_addr = self.counter
        self.counter += 1
        self.memory[self.counter].next_exec()
        addr = instruction % 100
        self.halt_reason = HaltReason.step

        if instruction == 0:  # HLT
            self.hint = "HLT"
            self.give_output("Done! Coffee break!")
            self.halt_reason = HaltReason.hlt

        elif instruction < 100:
            raise RuntimeError("Invalid instruction {:03}".format(instruction))

        elif instruction < 200:  # ADD
            memval = self.memory[addr].read()
            value = int_to_complement(self.accumulator.read() + memval)
            self.hint = ("ADD {0:03}: accumulator = {1:03} (accumulator) + "
                         "{2:03} (#{0:03}) = {3:03}".format(addr,
                                                            self.accumulator.value,
                                                            memval, value))
            self.accumulator.write(value)

        elif instruction < 300:  # SUB
            memval = self.memory[addr].read()
            value = int_to_complement(self.accumulator.read() - memval)
            self.hint = ("SUB {0:03}: accumulator = {1:03} (accumulator) - "
                         "{2:03} (#{0:03}) = {3:03}".format(addr,
                                                            self.accumulator.value,
                                                            memval, value))
            self.accumulator.write(value)

        elif instruction < 400:  # STA
            self.hint = ("STA {0:03}: store {1:03} (accumulator) to #{0:03}"
                         .format(addr, self.accumulator.value))
            self.memory[addr].write(self.accumulator.read())

        elif instruction < 600:  # LDA
            memval = self.memory[addr].read()
            self.hint = ("LDA {0:03}: load {1:03} (#{0:03}) to accumulator"
                         .format(addr, memval))
            self.accumulator.write(memval)

        elif instruction < 700:  # BRA
            self.hint = "BRA {0:03}: branch to #{0:03}".format(addr)
            self.counter = addr

        elif instruction < 800:  # BRZ
            words = ("==", "") if self.accumulator.read() == 0 else ("!=", " don't")
            self.hint = ("BRZ {0:03}: {1:03} (accumulator) {2} 000, so{3} branch"
                         " to #{0:03}".format(addr, self.accumulator.value, *words))
            if self.accumulator.read() == 0:
                self.counter = addr

        elif instruction < 900:  # BRP
            words = ("<", "") if self.accumulator.read() < 500 else (">=", " don't")
            self.hint = ("BRP {0:03}: {1:03} (accumulator) {2} 500, so{3} branch to #{0:03}"
                         .format(addr, self.accumulator.value, *words))
            if self.accumulator.read() < 500:
                self.counter = addr

        elif instruction == 901:  # INP
            self.hint = "INP"
            self.halt_reason = HaltReason.input

        elif instruction == 902:  # OUT
            self.hint = "OUT"
            self.give_output(int_from_complement(self.accumulator.read()))

        else:
            raise RuntimeError("Invalid instruction {:03}".format(instruction))

        if self.halt_reason == HaltReason.step and self.hit_breakpoints():
            self.halt_reason = HaltReason.breakpoint

        return self.halt_reason

    def run_to_hlt(self):
        r = HaltReason.step
        while r in (HaltReason.step, HaltReason.breakpoint):
            r = self.next_step()
        return r

    def reset(self):
        self.counter = self.instruction_addr = 0
        self.halt_reason = HaltReason.step
        self.accumulator.reset()
        for m in self.memory:
            m.reset()
        self.memory[self.counter].next_exec()

if __name__ == "__main__":
    import sys, assembler
    assem = assembler.Assembler()
    assem.update_code(open(sys.argv[1]).read())
    print(assem.assemble())
    runner = Runner(lambda x: print(">>>", x))
    runner.load_code(assem)
    runner.accumulator.breakpoint = BreakpointState.on_write
    runner.memory[44].breakpoint = BreakpointState.on_read
    for m in runner.memory:
        print(m.breakpoint)
    while runner.halt_reason != HaltReason.hlt:
        runner.next_step()
        if runner.halt_reason == HaltReason.input:
            runner.give_input(int(input("<<< ")))
        print(runner.hint)
        if runner.halt_reason == HaltReason.breakpoint:
            print("=== Breakpoint ===")
            for val in runner.hit_breakpoints():
                print("{:<12}".format(str(val.address).zfill(3) + ":"), val.breakpoint)
            input("Press enter to continue...")
