from amaranth import *
from amaranth.sim import *

# this decoder can handle byte sequences delimited by '\r\n' = '\xd\xa'.
# bytes are written to 'char' and shifted in with a pulse on 'write'.
# a pulse on 'clear' resets the buffer.
# the input byte sequence is interpreted as a 'command' and an optional 'arg'
# separated by a space character.
# Example: "READ 50\r\n" will result in command = "READ" and arg = 50
# only commands listed in the command lookup table are recognized and mapped
# to numerical values.

# Commands
# -: 0 # invalid
# R: 1 # read
# W: 2 # write
# I: 3 # increment

# Special chars
#  : 0x0A = 10 line feed
#  : 0x0D = 13 carriage return
#  : 0x32 = 20 space character

class SerialDecoder(Elaboratable):

    def __init__(self, bufsize=16):
        self.bufsize = bufsize
        self.buffer = Array([Signal(unsigned(8)) for _ in range(self.bufsize)])
        self.pos = Signal(unsigned(8))
        self.command = Signal(unsigned(4))
        self.command_complete = Signal()
        self.arg = Signal(unsigned(8))
        self.arg_off = Signal(unsigned(8))
        self.arg_len = Signal(unsigned(8))
        self.arg_convert_busy = Signal()
        self.char = Signal(8)
        self.write = Signal()
        self.clear = Signal()
        self.seen_crlf = Signal()
        self.decoded_command = Signal(unsigned(4))
        self.decoded_arg = Signal(unsigned(8))
        self.ready = Signal()
        self.write_prev = Signal()
        self.write_rose = Signal()

        self.commands = {
                "READ": {"char": 'R', "value": 1},
                "WRITE": {"char": 'W', "value": 2},
                "INSERT": {"char": 'I', "value": 3}
                }
        self.separator = ' '

        self.ports = (
                self.char,
                self.write,
                self.clear,
                self.command,
                self.arg,
                self.ready
                )

    def elaborate(self, platform):
        m = Module()

        m.d.sync += [
                self.write_prev.eq(self.write),
                ]

        m.d.comb += self.write_rose.eq((self.write == 1) & (self.write_prev == 0))

        with m.FSM(reset="WAIT_COMMAND"):
            with m.State("RESET"):
                m.d.sync += [
                        self.seen_crlf.eq(0),
                        self.command_complete.eq(0),
                        self.arg_off.eq(0),
                        self.pos.eq(0),
                        self.arg_len.eq(0),
                        self.decoded_arg.eq(0),
                        self.decoded_command.eq(0)
                        ]
                m.next = "WAIT_COMMAND"
            with m.State("WAIT_COMMAND"):
                with m.If(self.write_rose == 1):
                    m.d.sync += [
                            self.buffer[self.pos].eq(self.char),
                            self.pos.eq(self.pos + 1),
                            self.ready.eq(0),
                            ]
                with m.If((self.char == ord(self.separator))
                          | (self.char == 0x0d)):
                    m.d.sync += [
                            self.command_complete.eq(1),
                            self.arg_off.eq(self.pos + 1)
                            ]
                    m.next = "WAIT_ARG"
                with m.Else():
                    m.next = "WAIT_COMMAND"
            with m.State("WAIT_ARG"):
                with m.If(self.write_rose == 1):
                    m.d.sync += [
                            self.buffer[self.pos].eq(self.char),
                            self.pos.eq(self.pos + 1),
                            self.command_complete.eq(0)
                            ]
                with m.If(self.pos > 1):
                    with m.If(self.buffer[self.pos - 2] == 0x0d):
                        with m.If(self.buffer[self.pos - 1] == 0x0a):
                            m.d.sync += [
                                    self.seen_crlf.eq(1),
                                    self.arg_len.eq(self.pos - self.arg_off - 2)
                                    ]
                            m.next = "WAIT_ARG_CONVERT"
                with m.Else():
                            m.next = "WAIT_ARG"
            with m.State("WAIT_ARG_CONVERT"):
                m.d.sync += self.seen_crlf.eq(0)
                m.next = "WAIT_ARG_CONVERT2"
            with m.State("WAIT_ARG_CONVERT2"):
                with m.If(self.arg_convert_busy == 1):
                    m.next = "WAIT_ARG_CONVERT2"
                with m.Else():
                    m.d.sync += [
                        self.command.eq(self.decoded_command),
                        self.arg.eq(self.decoded_arg)
                        ]
                    m.next = "READY"
            with m.State("READY"):
                m.d.sync += self.ready.eq(1)
                m.next = "RESET"

        with m.FSM(reset="WAIT_INPUT"):
            with m.State("WAIT_INPUT"):
                with m.If(self.seen_crlf == 1):
                    m.d.sync += self.arg_convert_busy.eq(1)
                    m.next = "DECODE_ARG"
                with m.Else():
                    m.next = "WAIT_INPUT"
            with m.State("DECODE_ARG"):
                with m.If(self.arg_len == 1):
                    m.d.sync += self.decoded_arg.eq(
                                self.buffer[self.arg_off] - ord('0'))
                with m.Elif(self.arg_len == 2):
                    m.d.sync += self.decoded_arg.eq(
                                10 * (self.buffer[self.arg_off] - ord('0'))
                                + (self.buffer[self.arg_off + 1] - ord('0')))
                m.next = "DECODE_ARG_DONE"
            with m.State("DECODE_ARG_DONE"):
                m.d.sync += self.arg_convert_busy.eq(0)
                m.next = "WAIT_INPUT"

        with m.FSM(reset="WAIT_INPUT"):
            with m.State("WAIT_INPUT"):
                with m.If(self.command_complete == 1):
                    m.next = "DECODE_COMMAND"
                with m.Else():
                    m.next = "WAIT_INPUT"
            with m.State("DECODE_COMMAND"):
                with m.Switch(self.buffer[0]):
                    for k,v in self.commands.items():
                        with m.Case(ord(v["char"])):
                            print("{}:{}".format(k, v))
                            m.d.sync += self.decoded_command.eq(v["value"])
                    with m.Default():
                        m.d.sync += self.decoded_command.eq(0)
                m.next = "WAIT_INPUT"


        with m.If(self.clear == 1):
            m.d.sync += [
                    self.pos.eq(0),
                    self.command.eq(0),
                    self.arg.eq(0)
                    ]


        return m


if __name__ == '__main__':
    dut = SerialDecoder(bufsize=16)

    sim = Simulator(dut)

    def write_char(char, speed_divider=1):
        # Write
        yield dut.char.eq(ord(char))
        yield dut.write.eq(1)
        for i in range(speed_divider):
            yield Tick()
            yield Settle()
        # Reset write
        yield dut.write.eq(0)
        for i in range(speed_divider):
            yield Tick()
            yield Settle()

    def pause():
        yield Tick()
        yield Settle()
        yield Tick()
        yield Settle()
        yield Tick()
        yield Settle()
        yield Tick()
        yield Settle()
        yield Tick()
        yield Settle()
        yield Tick()
        yield Settle()

    def clear():
        yield dut.clear.eq(1)
        yield Tick()
        yield Settle()
        yield dut.clear.eq(0)
        yield Tick()
        yield Settle()

    def write(text, speed_divider=1):
        print("write = {}".format(text.strip()))
        for i in range(len(text)):
            yield from write_char(text[i], speed_divider)
        while True:
            ready = yield dut.ready
            yield Tick()
            yield Settle()
            if ready == 1:
                break

    def test_command(cmd, arg=None, speed_divider=1):
        argstr = ""
        if arg is not None:
            argstr = " " + str(arg)
        yield from write("{}{}\r\n".format(cmd["char"], argstr), speed_divider)

        print("dut.command = {}".format((yield dut.command)))
        assert (yield dut.command) == cmd["value"], "Didn't get {} = R!".format(cmd["value"], cmd["char"])
        if arg is not None:
            print("dut.arg = {}".format((yield dut.arg)))
            assert (yield dut.arg) == arg, "Didn't get argument {}!".format(arg)


    def proc():
        for speed_divider in [1, 2, 20]:
            print("Speed divider = {}".format(speed_divider))
            for cmd in dut.commands:
                print("cmd = {}".format(cmd))
                yield from test_command(dut.commands[cmd], None, speed_divider)
                yield from test_command(dut.commands[cmd], 7, speed_divider)
                yield from test_command(dut.commands[cmd], 42, speed_divider)


        yield from clear()
        assert (yield dut.command) == 0, "Didn't get 0!"
        assert (yield dut.arg) == 0, "Didn't get argument 0!"


    sim.add_clock(1e-6)
    sim.add_sync_process(proc)
    with sim.write_vcd('serial_dec.vcd', 'serial_dec.gtkw', traces=dut.ports):
        sim.run()
