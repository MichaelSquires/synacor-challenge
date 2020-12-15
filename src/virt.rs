extern crate anyhow;

use anyhow::{bail, Result};
#[allow(unused_imports)]
use log::{debug, error, info, trace, warn};

#[derive(Debug)]
enum Address {
    Literal(u16),
    Register(u16),
}

impl Address {
    fn from(val: u16) -> Result<Address> {
        let addr = match val {
            0..=32767 => Address::Literal(val),
            32768..=32775 => Address::Register(val - 32768),
            _ => {
                bail!("Invalid address: {}", val);
            }
        };

        Ok(addr)
    }
}

#[derive(Debug)]
enum Instruction {
    Halt,
    Set {
        op1: Address,
        op2: Address,
    },
    Push {
        op1: Address,
    },
    Pop {
        op1: Address,
    },
    Eq {
        op1: Address,
        op2: Address,
        op3: Address,
    },
    Gt {
        op1: Address,
        op2: Address,
        op3: Address,
    },
    Jmp {
        op1: Address,
    },
    Jt {
        op1: Address,
        op2: Address,
    },
    Jf {
        op1: Address,
        op2: Address,
    },
    Add {
        op1: Address,
        op2: Address,
        op3: Address,
    },
    Mult {
        op1: Address,
        op2: Address,
        op3: Address,
    },
    Mod {
        op1: Address,
        op2: Address,
        op3: Address,
    },
    And {
        op1: Address,
        op2: Address,
        op3: Address,
    },
    Or {
        op1: Address,
        op2: Address,
        op3: Address,
    },
    Not {
        op1: Address,
        op2: Address,
    },
    Rmem {
        op1: Address,
        op2: Address,
    },
    Wmem {
        op1: Address,
        op2: Address,
    },
    Call {
        op1: Address,
    },
    Ret,
    Out {
        op1: Address,
    },
    In {
        op1: Address,
    },
    Noop,
}

impl Instruction {
    fn decoder(data: &Vec<u16>, index: usize) -> Result<(Instruction, usize)> {
        let mut idx = index;

        let opcode = &data[idx];
        idx += 1;

        let instruction = match opcode {
            // One-byte instructions
            0 => Instruction::Halt,
            18 => Instruction::Ret,
            21 => Instruction::Noop,
            _ => {
                // Two-byte instructions
                let op1 = Address::from(data[idx])?;
                idx += 1;

                match opcode {
                    2 => Instruction::Push { op1 },
                    3 => Instruction::Pop { op1 },
                    6 => Instruction::Jmp { op1 },
                    17 => Instruction::Call { op1 },
                    19 => Instruction::Out { op1 },
                    20 => Instruction::In { op1 },
                    _ => {
                        // Three-byte instructions
                        let op2 = Address::from(data[idx])?;
                        idx += 1;

                        match opcode {
                            1 => Instruction::Set { op1, op2 },
                            7 => Instruction::Jt { op1, op2 },
                            8 => Instruction::Jf { op1, op2 },
                            14 => Instruction::Not { op1, op2 },
                            15 => Instruction::Rmem { op1, op2 },
                            16 => Instruction::Wmem { op1, op2 },
                            _ => {
                                // Four-byte instructions
                                let op3 = Address::from(data[idx])?;
                                idx += 1;

                                match opcode {
                                    4 => Instruction::Eq { op1, op2, op3 },
                                    5 => Instruction::Gt { op1, op2, op3 },
                                    9 => Instruction::Add { op1, op2, op3 },
                                    10 => Instruction::Mult { op1, op2, op3 },
                                    11 => Instruction::Mod { op1, op2, op3 },
                                    12 => Instruction::And { op1, op2, op3 },
                                    13 => Instruction::Or { op1, op2, op3 },
                                    _ => {
                                        bail!("Invalid opcode: {} [{}]", opcode, idx);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        };

        trace!(
            "Opcode {}, instruction {:?}, length {}",
            opcode,
            instruction,
            idx - index
        );

        Ok((instruction, idx - index))
    }
}

#[derive(Debug)]
pub struct VirtualMachine {
    memory: Vec<u16>,
    registers: Vec<u16>,
    stack: Vec<u16>,
    stdin: Vec<u8>,
    stdout: Vec<u8>,
    pc: usize,
}

impl VirtualMachine {
    pub fn new(data: Vec<u16>) -> Self {
        Self {
            memory: data,
            registers: vec![0; 8],
            stack: Vec::new(),
            stdin: Vec::new(),
            stdout: Vec::new(),
            pc: 0,
        }
    }

    fn out(&mut self, val: u16) {
        self.stdout.push(val as u8);
        print!("{}", std::str::from_utf8(&[val as u8]).unwrap());
    }

    pub fn stdout(&self) -> Vec<u8> {
        self.stdout.clone()
    }

    fn get(&self, addr: Address) -> u16 {
        match addr {
            Address::Register(idx) => self.registers[idx as usize],
            Address::Literal(mem) => mem,
        }
    }

    fn getreg(&self, addr: Address) -> Result<usize> {
        let idx = match addr {
            Address::Register(idx) => idx as usize,
            _ => {
                bail!("Invalid register: {:?}", addr);
            }
        };

        Ok(idx)
    }

    fn set(&mut self, addr: Address, val: u16) {
        match addr {
            Address::Register(idx) => {
                trace!("REG {} <- {}", idx, val);
                self.registers[idx as usize] = val;
            }

            Address::Literal(mem) => {
                trace!("MEM {} <- {}", mem, val);
                self.memory[mem as usize] = val;
            }
        }
    }

    pub fn run(&mut self) -> Result<()> {
        loop {
            let (instruction, length) = Instruction::decoder(&self.memory, self.pc)?;
            self.pc += length;

            match instruction {
                Instruction::Halt => {
                    break;
                }

                Instruction::Set { op1, op2 } => {
                    let idx = self.getreg(op1)?;
                    let val = self.get(op2);
                    self.registers[idx] = val;
                }

                Instruction::Push { op1 } => {
                    let val = self.get(op1);
                    self.stack.push(val);
                }

                Instruction::Pop { op1 } => {
                    if let Some(val) = self.stack.pop() {
                        self.set(op1, val);
                    } else {
                        bail!("Invalid stack pop");
                    }
                }

                Instruction::Eq { op1, op2, op3 } => {
                    let val1 = self.get(op2);
                    let val2 = self.get(op3);
                    if val1 == val2 {
                        self.set(op1, 1);
                    } else {
                        self.set(op1, 0);
                    }
                }

                Instruction::Gt { op1, op2, op3 } => {
                    let val1 = self.get(op2);
                    let val2 = self.get(op3);
                    if val1 > val2 {
                        self.set(op1, 1);
                    } else {
                        self.set(op1, 0);
                    }
                }

                Instruction::Jmp { op1 } => {
                    let addr = self.get(op1);
                    self.pc = addr as usize;
                }

                Instruction::Jt { op1, op2 } => {
                    let val = self.get(op1);
                    let addr = self.get(op2);
                    if val != 0 {
                        self.pc = addr as usize;
                    }
                }

                Instruction::Jf { op1, op2 } => {
                    let val = self.get(op1);
                    let addr = self.get(op2);
                    if val == 0 {
                        self.pc = addr as usize;
                    }
                }

                Instruction::Add { op1, op2, op3 } => {
                    let val1 = self.get(op2);
                    let val2 = self.get(op3);
                    self.set(op1, (val1 + val2) & 0x7fff);
                }

                Instruction::Mult { op1, op2, op3 } => {
                    let val1 = self.get(op2) as u32;
                    let val2 = self.get(op3) as u32;
                    let product: u32 = (val1 * val2) & 0x7fff;
                    self.set(op1, product as u16);
                }

                Instruction::Mod { op1, op2, op3 } => {
                    let val1 = self.get(op2);
                    let val2 = self.get(op3);
                    self.set(op1, val1 % val2);
                }

                Instruction::And { op1, op2, op3 } => {
                    let val1 = self.get(op2);
                    let val2 = self.get(op3);
                    self.set(op1, val1 & val2);
                }

                Instruction::Or { op1, op2, op3 } => {
                    let val1 = self.get(op2);
                    let val2 = self.get(op3);
                    self.set(op1, val1 | val2);
                }

                Instruction::Not { op1, op2 } => {
                    let val1 = self.get(op2);
                    self.set(op1, (!val1) & 0x7fff);
                }

                Instruction::Rmem { op1, op2 } => {
                    let addr = self.get(op2);
                    self.set(op1, self.memory[addr as usize]);
                }

                Instruction::Wmem { op1, op2 } => {
                    let addr = self.get(op1);
                    let val = self.get(op2);
                    self.memory[addr as usize] = val;
                }

                Instruction::Call { op1 } => {
                    let addr = self.get(op1);
                    self.stack.push(self.pc as u16);
                    self.pc = addr as usize;
                }

                Instruction::Ret => {
                    let addr = self.stack.pop().unwrap();
                    self.pc = addr as usize;
                }

                Instruction::Out { op1 } => {
                    let val = self.get(op1);
                    self.out(val);
                }

                Instruction::In { op1 } => {
                    if self.stdin.len() == 0 {
                        let mut input = String::new();
                        std::io::stdin().read_line(&mut input)?;
                        self.stdin.extend_from_slice(&input.as_bytes());
                    }

                    let val = self.stdin.remove(0) as u16;
                    self.set(op1, val);
                }

                Instruction::Noop => {}
            }
        }

        Ok(())
    }
}
