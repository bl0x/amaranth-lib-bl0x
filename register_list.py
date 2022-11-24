import os
import json
import textwrap
from amaranth import Signal


class RegisterFile():
    def __init__(self, name):
        self.name = name
        self.tables = []

    def add_table(self, table):
        self.tables.append(table)

    def to_json(self, filename):
        registers = {}
        for t in self.tables:
            if t.shortname is not None:
                name = t.shortname
            else:
                name = t.name
            registers[name] = t.dict

        with open(filename, "w") as f:
            json.dump(registers, f)

    def to_text(self, filename):
        text = ""
        for t in self.tables:
            text += t.to_text()
            text += "\n\n"
        with open(filename, "w") as f:
            f.write(text)


class RegConf(dict):
    def __init__(self, addr, bits, signame, reset=0, description=None):
        self.addr = addr
        self.reset = reset
        self.bits = bits
        self.name = signame
        self.signal = Signal(bits, name=signame, reset=self.reset)
        dict.__init__(self, addr=addr, reset=reset, bits=bits, name=signame,
                      description=description)


class RegisterTable():
    def __init__(self, name, shortname=None):
        self.name = name
        self.shortname = shortname
        self.dict = {}
        self.description = {}

    def add_list(self, name, offset, description=None, names=None):
        if name in self.dict:
            if type(self.dict[name]) is not list:
                print(("{} already exists in register table {} and it "
                       "is not a list, but a {}.").format(
                           name, self.name, type(self.dict[name])))
                os.abort()
            self.dict[name].append(register_list(
                name+str(len(self.dict[name])), offset, names))
            if description is not None:
                print("Description not used.")
                print("Add description to new_list_array call.")
        else:
            self.dict[name] = register_list(name, offset, names)
            self.description[name] = description

    def new_list_array(self, name, description=None):
        self.dict[name] = []
        self.description[name] = description

    def reg_to_text(self, r):
        maximum = (1 << r.bits)
        return "0x{:04x}: {:3d} {:10d} {:10d} {}\n".format(
                r.addr, r.bits, r.reset, maximum, r.name)

    def to_text(self):
        reg = self.dict
        desc = self.description
        text = "Register table '{}'\n".format(self.name)
        text += "----------------------------------------------------------\n"
        text += "  addr bits    default    maximum name\n"
        text += "----------------------------------------------------------\n"
        for r1 in reg:
            it = reg[r1]
            text += "\n"
            if desc[r1] is not None:
                wrapped = textwrap.indent(textwrap.fill(desc[r1]), "  #### ")
                text += "{}\n\n".format(wrapped)
            if type(it) is list:
                for i, item in enumerate(reg[r1]):
                    for r0 in reg[r1][i]:
                        text += self.reg_to_text(reg[r1][i][r0])
            else:
                for r0 in reg[r1]:
                    text += self.reg_to_text(reg[r1][r0])
        return text


def register_list(listname, offset, names):
    regs = {}
    for i, conf in enumerate(names):
        if len(conf) == 2:
            name, bits = conf
            reset = 0
            description = None
        elif len(conf) == 3:
            name, bits, reset = conf
            description = None
        elif len(conf) == 4:
            name, bits, reset, description = conf
        else:
            print("ERROR: register item must be a 2, 3 or 4 tuple.")
            os.abort()
        signame = listname + "_" + name
        regs[name] = RegConf(offset + i, bits, signame, reset, description)
    return regs
