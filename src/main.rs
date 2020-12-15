extern crate anyhow;

mod utils;
mod virt;

use anyhow::Result;
#[allow(unused_imports)]
use log::{debug, error, info, trace, warn};

fn main() -> Result<()> {
    let opts = vec![clap::Arg::with_name("infile")
        .help("Input filename")
        .required(true)];

    let args = utils::init(Some(opts))?;

    let bytes = std::fs::read(args.value_of("infile").unwrap())?;
    let data: Vec<u16> = bytes
        .chunks_exact(2)
        .into_iter()
        .map(|b| u16::from_ne_bytes([b[0], b[1]]))
        .collect();

    let mut vm = virt::VirtualMachine::new(data);
    match vm.run() {
        Ok(_) => {}
        Err(e) => {
            error!("{}", e);
        }
    }

    debug!("STDOUT: {}", std::str::from_utf8(&vm.stdout()).unwrap());

    Ok(())
}
