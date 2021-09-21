from cklib.args import get_arg_parser, ArgumentParser
from cksh.__main__ import add_args


def test_args():
    arg_parser = get_arg_parser()
    add_args(arg_parser)
    arg_parser.parse_args()
    assert ArgumentParser.args.keepercore_uri == "http://localhost:8080"
