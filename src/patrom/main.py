#!/usr/bin/env python3
from sys import exit, stderr
from os import EX_OK, EX_DATAERR, EX_IOERR, EX_USAGE
from argparse import ArgumentParser, BooleanOptionalAction, FileType
from Cheetah.Template import Template
from traceback import print_exc
from patrom import Compiler

def cli():
    parser = ArgumentParser(description='Cheetah template compiler to C')
    parser.add_argument('TMPL', type=FileType('r'),
            help='Input template file')
    parser.add_argument('OUTPUT', type=FileType('w'),
            help='Output file')
    parser.add_argument('--method', type=str, default='respond',
            help='Method name')
    args = parser.parse_args()
    try:
        source = args.TMPL.read()
        compiled = Template.compile(source=source,
                compilerClass=Compiler.CCompiler,
                mainMethodName=args.method,
                returnAClass=False)
        args.OUTPUT.write(compiled.decode())
    except Exception:
        print_exc()
        return EX_IOERR
    return EX_OK

if __name__ == "__main__":
    exit(cli())

