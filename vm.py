#!/usr/bin/env python3

import sys
import struct
import logging
import argparse

class InvalidReadError(Exception): pass
class InvalidValueError(Exception): pass
class InvalidArgumentsError(Exception): pass

class RegisterInstructionsMetaclass(type):
    def __init__(cls, name, bases, nmspc):
        super(RegisterInstructionsMetaclass, cls).__init__(name, bases, nmspc)

        if not hasattr(cls, 'registry'):
            cls.registry = dict()

        if cls not in bases:
            cls.registry[cls.OPCODE] = cls

    def __iter__(cls):
        return iter(cls.registry)

    def __getitem__(cls, key):
        return cls.registry[key]

    def __len__(cls):
        return 1 + cls.ARGS

class Instruction(metaclass=RegisterInstructionsMetaclass):
    ARGS = 0
    OPCODE = -1
    def __init__(self, vm, *args):
        logging.debug('%s: %s' % (self.__class__.__name__, args))
        if len(args) != self.ARGS:
            raise InvalidArgumentsError(
                'Arguments expected %d got %d' % (self.ARGS, len(args))
            )
        self._args = args
        self._vm = vm

    def __len__(self):
        return 1 + self.ARGS

    def exec(self):
        raise NotImplementedError

    def incpc(self):
        self._vm.pc += len(self)

    @classmethod
    def decode(cls, vm):
        opcode = vm.readMemory(vm.pc, 1)[0]
        instruction = cls[opcode]
        if instruction.ARGS:
            args = vm.readMemory(vm.pc+1, len(instruction)-1)
            logging.debug('ARGS %r', args)
            return instruction(vm, *args)
        else:
            return instruction(vm)

class Halt(Instruction):
    '''
    halt: 0
    stop executaion and terminate the program
    '''
    OPCODE = 0
    def exec(self):
        logging.info('HALT')
        self._vm.running = False

class Set(Instruction):
    '''
    set: 1 a b
    set register <a> to the value of <b>
    '''
    OPCODE = 1
    ARGS = 2
    def exec(self):
        a, b = self._args
        logging.info('SET: %d %d', a, b)
        self._vm.setRegister(a, self._vm.getValueOrReg(b))

class Push(Instruction):
    '''
    push: 2 a
    push <a> onto the stack
    '''
    OPCODE = 2
    ARGS = 1
    def exec(self):
        a = self._args[0]
        logging.info('PUSH: %d', a)
        self._vm.push(self._vm.getValueOrReg(a))

class Pop(Instruction):
    '''
    pop: 3 a
    remove the top element from the stack and write it into <a>; empty stack = error
    '''
    OPCODE = 3
    ARGS = 1
    def exec(self):
        a = self._args[0]
        logging.info('POP: %d', a)
        val = self._vm.pop()
        self._vm.setRegister(a, self._vm.getValueOrReg(val))

class Eq(Instruction):
    '''
    eq: 4 a b c
    set <a> to 1 if <b> is equal to <c>; set it to 0 otherwise
    '''
    OPCODE = 4
    ARGS = 3
    def exec(self):
        a, b, c = self._args
        logging.info('EQ: %d %d %d', a, b, c)
        if self._vm.getValueOrReg(b) == self._vm.getValueOrReg(c):
            self._vm.setRegister(a, 1)
        else:
            self._vm.setRegister(a, 0)

class Gt(Instruction):
    '''
    gt: 5 a b c
    set <a> to 1 if <b> is greater than <c>; set it to 0 otherwise
    '''
    OPCODE = 5
    ARGS = 3
    def exec(self):
        a, b, c = self._args
        logging.info('GT: %d %d %d', a, b, c)
        if self._vm.getValueOrReg(b) > self._vm.getValueOrReg(c):
            self._vm.setRegister(a, 1)
        else:
            self._vm.setRegister(a, 0)

class Jmp(Instruction):
    '''
    jmp: 6 a
    jump to <a>
    '''
    OPCODE = 6
    ARGS = 1
    def exec(self):
        a = self._args[0]
        logging.info('JMP: %d' % (a))

    def incpc(self):
        a = self._args[0]
        self._vm.pc = self._vm.getValueOrReg(a)

class Jt(Instruction):
    '''
    jt: 7 a b
    if <a> is nonzero, jump to <b>
    '''
    OPCODE = 7
    ARGS = 2
    def exec(self):
        a, b = self._args
        logging.info('JT: %d %d' % (a, b))

    def incpc(self):
        a, b = self._args
        if self._vm.getValueOrReg(a) != 0:
            self._vm.pc = self._vm.getValueOrReg(b)
        else:
            super().incpc()

class Jf(Instruction):
    '''
    jf: 8 a b
    if <a> is zero, jump to <b>
    '''
    OPCODE = 8
    ARGS = 2
    def exec(self):
        a, b = self._args
        logging.info('JF: %d %d' % (a, b))

    def incpc(self):
        a, b = self._args
        if self._vm.getValueOrReg(a) == 0:
            self._vm.pc = self._vm.getValueOrReg(b)
        else:
            super().incpc()

class Add(Instruction):
    '''
    add: 9 a b c
    assign into <a> the sum of <b> and <c> (modulo 32768)
    '''
    OPCODE = 9
    ARGS = 3
    def exec(self):
        a, b, c = self._args
        logging.info('ADD: %d %d %d', a, b, c)
        self._vm.setRegister(a,
            (self._vm.getValueOrReg(b) + self._vm.getValueOrReg(c)) % 2**15
        )

class Mult(Instruction):
    '''
    mult: 10 a b c
    store into <a> the product of <b> and <c> (modulo 32768)
    '''
    OPCODE = 10
    ARGS = 3
    def exec(self):
        a, b, c = self._args
        logging.info('MULT: %d %d %d', a, b, c)
        self._vm.setRegister(a,
            (self._vm.getValueOrReg(b) * self._vm.getValueOrReg(c)) % 2**15
        )

class Mod(Instruction):
    '''
    mod: 11 a b c
    store into <a> the remainder of <b> divided by <c>
    '''
    OPCODE = 11
    ARGS = 3
    def exec(self):
        a, b, c = self._args
        logging.info('MOD: %d %d %d', a, b, c)
        self._vm.setRegister(a,
            self._vm.getValueOrReg(b) % self._vm.getValueOrReg(c)
        )

class And(Instruction):
    '''
    and: 12 a b c
    stores into <a> the bitwise and of <b> and <c>
    '''
    OPCODE = 12
    ARGS = 3
    def exec(self):
        a, b, c = self._args
        logging.info('AND: %d %d %d', a, b, c)
        self._vm.setRegister(a,
            self._vm.getValueOrReg(b) & self._vm.getValueOrReg(c)
        )

class Or(Instruction):
    '''
    or: 13 a b c
    stores into <a> the bitwise or of <b> and <c>
    '''
    OPCODE = 13
    ARGS = 3
    def exec(self):
        a, b, c = self._args
        logging.info('OR: %d %d %d', a, b, c)
        self._vm.setRegister(a,
            self._vm.getValueOrReg(b) | self._vm.getValueOrReg(c)
        )

class Not(Instruction):
    '''
    not: 14 a b
    stores 15-bit bitwise inverse of <b> in <a>
    '''
    OPCODE = 14
    ARGS = 2
    def exec(self):
        a, b = self._args
        logging.info('NOT: %d %d', a, b)
        self._vm.setRegister(a,
            (~self._vm.getValueOrReg(b) & 0x7fff)
        )

class Rmem(Instruction):
    '''
    rmem: 15 a b
    read memory at address <b> and write it to <a>
    '''
    OPCODE = 15
    ARGS = 2
    def exec(self):
        a, b = self._args
        logging.info('RMEM: %d %d', a, b)
        val = self._vm.readMemory(self._vm.getValueOrReg(b), 1)[0]
        self._vm.setRegister(a, val)

class Wmem(Instruction):
    '''
    wmem: 16 a b
    write the value from <b> into memory at address <a>
    '''
    OPCODE = 16
    ARGS = 2
    def exec(self):
        a, b = self._args
        logging.info('WMEM: %d %d', a, b)
        self._vm.writeMemory(
            self._vm.getValueOrReg(a),
            self._vm.getValueOrReg(b),
        )

class Call(Instruction):
    '''
    call: 17 a
    write the address of the next instruction to the stack and jump to <a>
    '''
    OPCODE = 17
    ARGS = 1
    def exec(self):
        a = self._args[0]
        logging.info('CALL: %d', a)
        self._vm.push(self._vm.pc + len(self))

    def incpc(self):
        a = self._args[0]
        self._vm.pc = self._vm.getValueOrReg(a)

class Ret(Instruction):
    '''
    ret: 18
    remove the top element from the stack and jump to it; empty stack = halt
    '''
    OPCODE = 18
    ARGS = 0
    def exec(self):
        logging.info('RET')

    def incpc(self):
        val = self._vm.pop()
        a = self._vm.getValueOrReg(val)
        self._vm.pc = self._vm.getValueOrReg(a)

class Out(Instruction):
    '''
    out: 19 a
    write the character represented by ascii code <a> to the terminal
    '''
    OPCODE = 19
    ARGS = 1
    def exec(self):
        a = self._args[0]
        logging.info('OUT: %d', a)
        sys.stdout.write(chr(self._vm.getValueOrReg(a)))

class In(Instruction):
    '''
    in: 20 a
    read a character from the terminal and write its ascii code to <a>;
    it can be assumed that once input starts, it will continue until a
    newline is encountered; this means that you can safely read whole
    lines from the keyboard and trust that they will be fully read
    '''
    OPCODE = 20
    ARGS = 1
    def exec(self):
        a = self._args[0]
        logging.info('IN: %d', a)
        self._vm.setRegister(a, ord(self._vm.stdin))

class Noop(Instruction):
    '''
    noop: 21
    no operation
    '''
    OPCODE = 21
    def exec(self):
        logging.info('NOOP')

class VirtualMachine:
    __INSTRUCTIONS__ = [
        Halt,
        Out,
        Noop
    ]
    def __init__(self, executable):
        self._executable = executable

        self.running = True

        self._memory = executable
        self._stack = []
        self._pc = 0
        self._registers = {
            'r0': 0,
            'r1': 0,
            'r2': 0,
            'r3': 0,
            'r4': 0,
            'r5': 0,
            'r6': 0,
            'r7': 0,
        }
        self._stdin = ''

    @property
    def pc(self):
        logging.debug(' PC: %d', self._pc)
        return self._pc

    @pc.setter
    def pc(self, value):
        logging.debug(' PC = %d', value)
        self._pc = value

    @property
    def stdin(self):
        if not self._stdin:
            self._stdin = sys.stdin.readline()
        ret = self._stdin[0]
        self._stdin = self._stdin[1:]
        return ret

    def push(self, val):
        logging.debug('SPUSH: %d', val)
        self._stack.append(val)

    def pop(self):
        val = self._stack.pop()
        logging.debug('SPOP: %d', val)
        return val

    def setRegister(self, reg, value):
        if reg == 32768:
            logging.info('  R0 = %d', value)
            self._registers['r0'] = value
        elif reg == 32769:
            logging.info('  R1 = %d', value)
            self._registers['r1'] = value
        elif reg == 32770:
            logging.info('  R2 = %d', value)
            self._registers['r2'] = value
        elif reg == 32771:
            logging.info('  R3 = %d', value)
            self._registers['r3'] = value
        elif reg == 32772:
            logging.info('  R4 = %d', value)
            self._registers['r4'] = value
        elif reg == 32773:
            logging.info('  R5 = %d', value)
            self._registers['r5'] = value
        elif reg == 32774:
            logging.info('  R6 = %d', value)
            self._registers['r6'] = value
        elif reg == 32775:
            logging.info('  R7 = %d', value)
            self._registers['r7'] = value
        else:
            raise InvalidRegisterError('Invalid register: %d' % (reg))

    def getValueOrReg(self, value):
        if 0 <= value <= 32767:
            logging.info('  VAL: %d', value)
        elif value == 32768:
            value = self._registers.get('r0')
            logging.info('  R0: %d', value)
        elif value == 32769:
            value = self._registers.get('r1')
            logging.info('  R1: %d', value)
        elif value == 32770:
            value = self._registers.get('r2')
            logging.info('  R2: %d', value)
        elif value == 32771:
            value = self._registers.get('r3')
            logging.info('  R3: %d', value)
        elif value == 32772:
            value = self._registers.get('r4')
            logging.info('  R4: %d', value)
        elif value == 32773:
            value = self._registers.get('r5')
            logging.info('  R5: %d', value)
        elif value == 32774:
            value = self._registers.get('r6')
            logging.info('  R6: %d', value)
        elif value == 32775:
            value = self._registers.get('r7')
            logging.info('  R7: %d', value)
        else:
            raise InvalidValueError('Invalid value: %d' % (value))

        return value

    def readMemory(self, address, words):
        if words == 0 or words > 2**15:
            raise InvalidReadError('Attempt to read %d words from %d' % (words, address))
        logging.debug('readMemory: %d (%d)' % (address, words))
        return struct.unpack('<%dH' % (words), self._memory[address * 2:(address * 2) + (2 * words)])

    def writeMemory(self, address, data):
        self._memory = b''.join((
            self._memory[:address * 2],
            struct.pack('<H', data),
            self._memory[address * 2 + 2:],
        ))

    def run(self):
        while self.running:
            instruction = Instruction.decode(self)
            instruction.exec()
            instruction.incpc()

def main(args):

    program = args.file.read()
    vm = VirtualMachine(program)
    vm.run()

    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog=sys.argv[0])

    # Optional arguments
    parser.add_argument('-v', '--verbose', help='Show verbose messages', action='count', default=0)

    # Positional arguments
    parser.add_argument('file', help='Input file', type=argparse.FileType('rb'))

    args = parser.parse_args()
    if args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose > 1:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        sys.exit(main(args))
    except Exception as exc:
        logging.exception('ERROR in main: %s' % (exc))
        sys.exit(-1)
