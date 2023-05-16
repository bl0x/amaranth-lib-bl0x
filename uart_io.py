from amaranth import (Signal, Elaboratable, unsigned, Module, Const)
from amaranth.sim import Simulator
from external.uart import UART
from serial_decoder import SerialDecoder
from serial_encoder import SerialEncoder
from edge_detect import EdgeDetector


class UartIO(Elaboratable):
    def __init__(self, data_bits=8, addr_bits=4, clock_frequency=0):

        # Parameters
        self.data_bits = data_bits
        self.addr_bits = addr_bits
        self.arg_bits = data_bits
        self.clock_frequency = clock_frequency
        self.divisor = Signal(16)

        # Hardware IO
        self.rx_pin = Signal()
        self.tx_pin = Signal()

        # Module IO
        self.we = Signal()
        self.w_data = Signal(self.data_bits)
        self.w_addr = Signal(self.addr_bits)
        self.re = Signal()
        self.r_data = Signal(self.data_bits)
        self.r_addr = Signal(self.addr_bits)

        self.encoder = SerialEncoder()
        self.decoder = SerialDecoder(bufsize=10, arg_bits=self.data_bits)

    def connect(self, rx_pin, tx_pin, we, w_addr, w_data, re, r_addr, r_data,
                divisor):
        return [self.rx_pin.eq(rx_pin), tx_pin.eq(self.tx_pin),
                we.eq(self.we), w_addr.eq(self.w_addr), w_data.eq(self.w_data),
                re.eq(self.re), r_addr.eq(self.r_addr), self.r_data.eq(r_data),
                self.divisor.eq(divisor)]

    def elaborate(self, platform):

        m = Module()

        m.submodules.uart = uart = UART()
        m.submodules.decoder = decoder = self.decoder
        m.submodules.encoder = encoder = self.encoder
        m.submodules.uart_fsm = uart_fsm = UartFsm(decoder, encoder,
                                                   data_bits=self.data_bits,
                                                   addr_bits=self.addr_bits)
        self.encoder = encoder
        self.decoder = decoder

        # connect uart to pins and data
        m.d.comb += [
                uart.rx_pin.eq(self.rx_pin),
                self.tx_pin.eq(uart.tx_pin),
                decoder.char.eq(uart.rx_data),
                decoder.write.eq(uart.rx_rdy),
                uart.divisor.eq(self.divisor),
                uart.tx_data.eq(encoder.tx),
                uart.tx_trg.eq(encoder.tx_trg),
                encoder.tx_rdy.eq(uart.tx_rdy),
        ]

        # connect fsm
        m.d.comb += uart_fsm.connect(we=self.we, write_addr=self.w_addr,
                                     write_data=self.w_data,
                                     read_data=self.r_data,
                                     read_addr=self.r_addr,
                                     re=self.re)

        return m


class UartFsm(Elaboratable):
    def __init__(self, decoder, encoder, data_bits=8, addr_bits=4):

        # Parameters
        self.n_args = 2
        self.data_bits = data_bits
        self.addr_bits = addr_bits

        # Submodules
        self.encoder = encoder
        self.decoder = decoder

        # Inputs
        # Data from register
        self.read_data = Signal(unsigned(self.data_bits))

        # Reading
        # Select address to read from
        self.re = Signal()
        self.read_addr = Signal(self.addr_bits)
        # Data to send out over TX
        self.uart_tx_data = Signal(unsigned(self.data_bits))

        # Writing
        self.we = Signal()
        # Select address to write to
        self.write_addr = Signal(self.addr_bits)
        # Data to write at address
        self.write_data = Signal(self.data_bits)

    def connect(self, we, write_addr, write_data, read_data, read_addr, re):
        return [we.eq(self.we), write_addr.eq(self.write_addr),
                write_data.eq(self.write_data),
                self.read_data.eq(read_data),
                read_addr.eq(self.read_addr),
                re.eq(self.re)]

    def elaborate(self, platform):

        m = Module()

        # receiver side
        decode_ready = Signal()
        start = Signal()

        m.submodules.decode_edge = decode_edge = EdgeDetector()
        m.d.comb += decode_edge.connect(i=decode_ready, o=start)

        read_val = Signal(16)
        read_addr = self.read_addr
        re = self.re
        uart_tx_data = self.uart_tx_data
        read_data = self.read_data
        write_addr = self.write_addr
        write_data = self.write_data
        we = self.we
        encoder = self.encoder
        decoder = self.decoder

        command = Signal(unsigned(4))
        arg = [Signal(unsigned(self.data_bits)) for _ in range(self.n_args)]

        m.d.comb += [
            decode_ready.eq(decoder.ready),
            command.eq(decoder.command),
            *[arg[i].eq(decoder.arg[i]) for i in range(self.n_args)]
        ]

        with m.FSM(reset="WAIT_START") as fsm:
            _ = fsm
            with m.State("WAIT_START"):
                with m.If((start == 1) & (command == 1)):
                    m.d.sync += read_val.eq(0)
                    m.next = "READ"
                with m.Elif((start == 1) & (command == 2)):
                    m.next = "WRITE"
                with m.Else():
                    m.next = "WAIT_START"

            with m.State("READ"):
                m.d.sync += [
                    read_addr.eq(arg[0][0:16]), # Limit address space to 0xffff
                    read_val.eq(arg[1][0:16]),  # Limit multi-read to 65k
                ]
                m.next = "READ_ON"
            with m.State("READ_ON"):
                m.d.sync += re.eq(1)
                m.next = "READ_OFF"
            with m.State("READ_OFF"):
                m.d.sync += re.eq(0)
                m.next = "GET_DATA"
            with m.State("GET_DATA"):
                m.d.sync += uart_tx_data.eq(read_data)
                m.next = "SEND_DATA"
            with m.State("SEND_DATA"):
                m.next = "SEND_DELAY"
            with m.State("SEND_DELAY"):
                m.d.sync += [
                    encoder.data.eq(uart_tx_data),
                    encoder.write.eq(1),
                ]
                m.next = "SEND_DATA2"
            with m.State("SEND_DATA2"):
                m.d.sync += encoder.write.eq(0),
                m.next = "START_ENCODE"
            with m.State("START_ENCODE"):
                m.d.sync += encoder.trg.eq(1)
                m.next = "SENDER_PAUSE"
            with m.State("SENDER_PAUSE"):
                m.d.sync += encoder.trg.eq(0),
                m.next = "WAIT_SENDER_READY"
            with m.State("WAIT_SENDER_READY"):
                with m.If(encoder.rdy == 1):
                    with m.If(read_val > 1):
                        m.d.sync += [
                            read_val.eq(read_val - 1),
                            read_addr.eq(read_addr + 1)
                        ]
                        m.next = "READ_ON"
                    with m.Else():
                        m.next = "WAIT_START"

            with m.State("WRITE"):
                m.d.sync += [
                    we.eq(1),
                    write_addr.eq(arg[0]),
                    write_data.eq(arg[1])
                ]
                m.next = "WRITE_END"
            with m.State("WRITE_END"):
                m.d.sync += [
                    we.eq(0),
                    write_addr.eq(0),
                    write_data.eq(0)
                ]
                m.next = "WAIT_START"

        return m
