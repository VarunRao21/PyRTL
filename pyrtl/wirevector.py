"""
wirevector has all of the basic extended types useful for creating logic.

Types defined in this file include:
WireVector: the base class for ordered collections of wires
Input: a wire vector that recieves an input for a block
Output: a wire vector that defines an output for a block
Const: a wire vector fed by an unsigned constant
Register: a wire vector that is latched each cycle
MemBlock: a block of memory that can be read (async) and written (sync)

In addition, two helper functions are defined, as_wires (which does nothing
but return original wire vector if passed one, but converts integers into
Const wire vectors), and concat (which takes an arbitrary set of wire vector
parameters and concats them into one new wire vector which it returns.
"""

import collections
import string
from block import *


#------------------------------------------------------------------------
#          __   __               __      __        __   __
#    |  | /  \ |__) |__/ | |\ | / _`    |__) |    /  \ /  ` |__/
#    |/\| \__/ |  \ |  \ | | \| \__>    |__) |___ \__/ \__, |  \
#


# Right now we use singlton_block to store the one global
# block, but in the future we should support multiple Blocks.
# The argument "singlton_block" should never be passed.
_singleton_block = Block()


def working_block():
    return _singleton_block


def reset_working_block():
    global _singleton_block
    _singleton_block = Block()


#-----------------------------------------------------------------
#        ___  __  ___  __   __
#  \  / |__  /  `  |  /  \ |__)
#   \/  |___ \__,  |  \__/ |  \
#

class WireVector(object):
    def __init__(self, bitwidth=None, name=None, block=None):

        # figure out what block this wirevector should be part of
        if isinstance(block, Block):
            self.block = block
        elif block is None:
            self.block = working_block()
        else:
            raise PyrtlError('Attempt to link WireVector to block '
                             'not derived of type Block')

        # figure out a name
        if name is None:
            name = Block.next_tempvar_name()
        if name.lower() in ['clk', 'clock']:
            raise PyrtlError(
                'Clock signals should never be explicitly instantiated')
        self.name = name

        # now handle the bitwidth
        if bitwidth is not None:
            if not isinstance(bitwidth, int):
                raise PyrtlError(
                    'error attempting to create wirevector with bitwidth of type "%s" '
                    'instead of integer' % type(bitwidth))
            if bitwidth <= 0:
                raise PyrtlError(
                    'error attempting to create wirevector with bitwidth of length "%d", '
                    'all bitwidths must be > 0' % bitwidth)
        self.bitwidth = bitwidth

        # finally, add the wirevector back in the mother block
        self.block.add_wirevector(self)

    def __repr__(self):
        return ''.join([
            type(self).__name__,
            ':',
            self.name,
            '/',
            str(self.bitwidth)
            ])

    def __ilshift__(self, other):
        if not isinstance(other, WireVector):
            other = Const(other)
        if self.bitwidth is None:
            raise PyrtlError

        if self.bitwidth < other.bitwidth:
            # truncate the upper bits
            other = other[:self.bitwidth]
        if self.bitwidth > other.bitwidth:
            # extend appropriately
            other = other.extended(self.bitwidth)

        net = LogicNet(
            op=None,
            op_param=None,
            args=(other,),
            dests=(self,))
        self.block.add_net(net)
        return self

    def logicop(self, other, op):
        a, b = self, other
        # convert constants if necessary
        if not isinstance(b, WireVector):
            b = Const(b)
        # check size of operands
        if len(a) < len(b):
            a = a.extended(len(b))
        elif len(b) < len(a):
            b = b.extended(len(a))
        resultlen = len(a)  # both are the same length now
        if op == '+' or op == '-':
            resultlen += 1  # extra bit required for carry
        if op == '*':
            resultlen = resultlen * 2  # more bits needed for mult
        s = WireVector(bitwidth=resultlen)
        net = LogicNet(
            op=op,
            op_param=None,
            args=(a, b),
            dests=(s,))
        self.block.add_net(net)
        return s

    def __and__(self, other):
        return self.logicop(other, '&')

    def __rand__(self, other):
        return self.logicop(other, '&')

    def __or__(self, other):
        return self.logicop(other, '|')

    def __ror__(self, other):
        return self.logicop(other, '|')

    def __xor__(self, other):
        return self.logicop(other, '^')

    def __rxor__(self, other):
        return self.logicop(other, '^')

    def __add__(self, other):
        return self.logicop(other, '+')

    def __radd__(self, other):
        return self.logicop(other, '+')

    def __sub__(self, other):
        return self.logicop(other, '-')

    def __rsub__(self, other):
        return self.logicop(other, '-')

    def __mul__(self, other):
        return self.logicop(other, '*')

    def __rmul__(self, other):
        return self.logicop(other, '*')

    def __invert__(self):
        outwire = WireVector(bitwidth=len(self))
        net = LogicNet(
            op='~',
            op_param=None,
            args=(self,),
            dests=(outwire,))
        self.block.add_net(net)
        return outwire

    def __getitem__(self, item):
        assert self.bitwidth is not None  # should never be user visible
        allindex = [i for i in range(self.bitwidth)]
        if isinstance(item, int):
            selectednums = [allindex[item]]
        else:
            selectednums = allindex[item]  # slice
        outwire = WireVector(bitwidth=len(selectednums))
        net = LogicNet(
            op='s',
            op_param=tuple(selectednums),
            args=(self,),
            dests=(outwire,))
        self.block.add_net(net)
        return outwire

    def __len__(self):
        return self.bitwidth

    def sign_extended(self, bitwidth):
        """ return a sign extended wirevector derived from self """
        return self._extend_with_bit(bitwidth, self[-1])

    def zero_extended(self, bitwidth):
        """ return a zero extended wirevector derived from self """
        return self._extend_with_bit(bitwidth, Const(0, bitwidth=1))

    def extended(self, bitwidth):
        """ return an extended wirevector derived from self """
        return self.zero_extended(bitwidth)

    def _extend_with_bit(self, bitwidth, extbit):
        numext = bitwidth - self.bitwidth
        if numext == 0:
            return self
        elif numext < 0:
            raise PyrtlError(
                'error, zero_extended cannot reduce the number of bits')
        else:
            extvector = WireVector(bitwidth=numext)
            net = LogicNet(
                op='s',
                op_param=(0,)*numext,
                args=(extbit,),
                dests=(extvector,))
            self.block.add_net(net)
            return concat(extvector, self)


#------------------------------------------------------------------------
#  ___     ___  ___       __   ___  __           ___  __  ___  __   __   __
# |__  \_/  |  |__  |\ | |  \ |__  |  \    \  / |__  /  `  |  /  \ |__) /__`
# |___ / \  |  |___ | \| |__/ |___ |__/     \/  |___ \__,  |  \__/ |  \ .__/
#

class Input(WireVector):
    """ A WireVector type denoting inputs to a block (no writers) """

    def __init__(self, bitwidth=None, name=None):
        super(Input, self).__init__(bitwidth, name)

    def __ilshift__(self, _):
        raise PyrtlError(
            'Input, such as "%s", cannot have values generated internally'
            % str(self.name))


class Output(WireVector):
    """ A WireVector type denoting outputs of a block (no readers) """

    def __init__(self, bitwidth=None, name=None):
        super(Output, self).__init__(bitwidth, name)
    # todo: check that we can't read from this vector


class Const(WireVector):
    """ A WireVector representation of an unsigned integer constant """

    def __init__(self, val, bitwidth=None):
        """ Construct a constant implementation at initialization """
        name = Block.next_constvar_name(val)

        if isinstance(val, int):
            num = val
            # infer bitwidth if it is not specified explicitly
            if bitwidth is None:
                bitwidth = len(bin(num))-2  # the -2 for the "0b" at the start of the string
        if isinstance(val, basestring):
            if bitwidth is not None:
                raise PyrtlError('error, bitwidth parameter of const should be unspecified when'
                                 ' the const is created from a string (instead use verilog style'
                                 ' specification)')
            split_string = string.split(val, "'")
            if len(split_string) != 2:
                raise PyrtlError('error, string for Const not in verilog "32\'b01001" style format')
            try:
                bitwidth = int(split_string[0])
                num = int(''.join(['0', split_string[1]]), 0)
            except ValueError:
                raise PyrtlError('error, string for Const not in verilog "32\'b01001" style format')

        if not isinstance(bitwidth, int):
            raise PyrtlError(
                'error, bitwidth must be from type int, instead Const was passed "%s" of type %s'
                % (str(bitwidth), type(bitwidth)))
        if num < 0:
            raise PyrtlError(
                'error, Const is only for unsigned numbers and must be positive')
        if bitwidth < 0:
            raise PyrtlError(
                'error, you are trying a negative bitwidth? awesome but wrong')
        if (num >> bitwidth) != 0:
            raise PyrtlError(
                'error constant "%s" cannot fit in the specified %d bits'
                % (str(num), bitwidth))

        # initialize the WireVector
        super(Const, self).__init__(bitwidth=bitwidth, name=name)
        # add the member "val" to track the value of the constant
        self.val = num

    def __ilshift__(self, other):
        raise PyrtlError(
            'ConstWires, such as "%s", should never be assigned to with <<='
            % str(self.name))


class Register(WireVector):
    """ A WireVector with a latch in the middle (read current value, set .next value) """

    def __init__(self, bitwidth, name=None):
        super(Register, self).__init__(bitwidth=bitwidth, name=name)
        self.reg_in = None

    def _makereg(self):
        if self.reg_in is None:
            n = WireVector(bitwidth=self.bitwidth, name=self.name+"'")
            net = LogicNet(
                op='r',
                op_param=None,
                args=(n,),
                dests=(self,))
            self.block.add_net(net)
            self.reg_in = n
        return self.reg_in

    def __ilshift__(self, other):
        raise PyrtlError(
            'Registers, such as "%s", should never be assigned to with <<='
            % str(self.name))

    @property
    def next(self):
        return self._makereg()

    @next.setter
    def next(self, value):
        # The .next feild can be set with either "<<=" or "=", and
        # they do the same thing.
        if self.reg_in == value:
            return
        if self.reg_in is not None:
            raise PyrtlError
        n = self._makereg()
        n <<= value


#-----------------------------------------------------------------
#   __     __        ___  __           ___  __  ___  __   __   __
#  /__` | / _` |\ | |__  |  \    \  / |__  /  `  |  /  \ |__) /__`
#  .__/ | \__> | \| |___ |__/     \/  |___ \__,  |  \__/ |  \ .__/
#

class SignedWireVector(WireVector):
    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


class SignedInput(Input):
    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


class SignedOutput(Output):
    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


class SignedConst(Const):
    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


class SignedRegister(Register):
    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


#------------------------------------------------------------------------
#
#         ___        __   __          __        __   __
#   |\/| |__   |\/| /  \ |__) \ /    |__) |    /  \ /  ` |__/
#   |  | |___  |  | \__/ |  \  |     |__) |___ \__/ \__, |  \
#

# MemBlock supports any number of the following operations:
# read: d = mem[address]
# write: mem[address] = d
# write with an enable: mem[address] = DataWithEnable(d,enable=we)
# Based on the number of reads and writes a memory will be inferred
# with the correct number of ports to support that

DataWithEnable = collections.namedtuple('DataWithEnable', 'data, enable')


class MemBlock(object):
    """ An object for specifying block memories """

    # data = memory[addr]  (infer read port)
    # memory[addr] = data  (infer write port)
    # Not currently implemented:  memory[addr] <<= data (infer write port)
    def __init__(self,  bitwidth, addrwidth, name=None, block=None):

        if isinstance(block, Block):
            self.block = block
        elif block is None:
            self.block = working_block()
        else:
            raise PyrtlError(
                'Attempt to link MemBlock to block not derived of type Block')

        if bitwidth <= 0:
            raise PyrtlError
        if addrwidth <= 0:
            raise PyrtlError
        if name is None:
            name = Block.next_tempvar_name()

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.stored_net = None
        self.id = Block.next_memid()
        self.read_addr = []  # arg
        self.read_data = []  # dest
        self.write_addr = []  # arg
        self.write_data = []  # arg
        self.write_enable = []  # arg

    def __getitem__(self, item):
        if not isinstance(item, WireVector):
            raise PyrtlError('error, index to a memblock must be a WireVector (or derived) type')
        if len(item) != self.addrwidth:
            raise PyrtlError('error, width of memblock index "%s" is %d, '
                             'addrwidth is %d' % (item.name, len(item), self.addrwidth))

        data = WireVector(bitwidth=self.bitwidth)
        self.read_data.append(data)
        self.read_addr.append(item)
        self._update_net()
        return data

    def _update_net(self):
        if self.stored_net:
            self.block.logic.remove(self.stored_net)
        assert len(self.write_addr) == len(self.write_data)  # not sure about this one

        # construct the arg list from reads and writes
        coupled_write_args = zip(self.write_addr, self.write_data, self.write_enable)
        flattened_write_args = [item for sublist in coupled_write_args for item in sublist]
        net = LogicNet(
            op='m',
            op_param=(self.id, len(self.read_addr), len(self.write_addr)),
            args=tuple(self.read_addr + flattened_write_args),
            dests=tuple(self.read_data))
        self.block.add_net(net)
        self.stored_net = net

    def __setitem__(self, item, val):
        # check that 'item' is a valid address vector
        if not isinstance(item, WireVector):
            raise PyrtlError
        if len(item) != self.addrwidth:
            raise PyrtlError
        addr = item

        # check that 'val' is a valid datavector
        if isinstance(val, WireVector):
            data = val
            enable = Const(1, bitwidth=1)
        elif isinstance(val, DataWithEnable):
            data = val.data
            enable = val.enable
        else:
            raise PyrtlError
        if len(data) != self.bitwidth:
            raise PyrtlError
        if len(enable) != 1:
            raise PyrtlError

        self.write_data.append(data)
        self.write_addr.append(addr)
        self.write_enable.append(enable)
        self._update_net()


#-----------------------------------------------------------------
#        ___       __   ___  __   __
#  |__| |__  |    |__) |__  |__) /__`
#  |  | |___ |___ |    |___ |  \ .__/
#

def as_wires(val):
    """ Return wires from val which may be wires or int. """
    if isinstance(val, int):
        return Const(val)
    if not isinstance(val, WireVector):
        raise PyrtlError
    return val


def concat(*args):
    """ Take any number of wire vector params and return a wire vector concatinating them."""
    if len(args) <= 0:
        raise PyrtlError
    if len(args) == 1:
        return args[0]
    else:
        final_width = sum([len(arg) for arg in args])
        outwire = WireVector(bitwidth=final_width)
        net = LogicNet(
            op='c',
            op_param=None,
            args=tuple(args),
            dests=(outwire,))
        outwire.block.add_net(net)
        return outwire