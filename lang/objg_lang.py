import sys
import re

class PeekableStream:
    def __init__(self, iterator):
        self.iterator = iter(iterator)
        self._fill()

    def _fill(self):
        try:
            self.next = next(self.iterator)
        except StopIteration:
            self.next = None

    def move_next(self):
        ret = self.next
        self._fill()
        return ret

def _scan_string(delim, chars):
    ret = ""
    while chars.next != delim:
        c = chars.move_next()
        if c is None:
            raise Exception("Error on string!")
        ret += c
    chars.move_next()
    return ret

def _scan(first_char, chars, allowed):
    ret = first_char
    p = chars.next
    while p is not None and re.match(allowed, p):
        ret += chars.move_next()
        p = chars.next
    return ret

def tokenize(text):
    chars = PeekableStream(text)
    while chars.next is not None:
        c = chars.move_next()
        if c in " \n": pass
        elif c in "+-*/": yield ("operation", c)
        elif c in "(){},;=@": yield (c, "")
        elif c in ("'", '"'):
            yield ("string", _scan_string(c, chars))
        elif re.match("[.0-9]", c):
            yield ("number", _scan(c, chars, "[.0-9]"))
        elif re.match("[_a-zA-Z0-9]", c):
            yield ("symbol", _scan(c, chars, "[_a-zA-Z0-9]"))
        else: raise Exception("Unknown character '%s'" % c)

class Parser():
    def __init__(self, tokens, stop_at):
        self.tokens = tokens
        self.stop_at = stop_at

    def fail_if_at_end(self, end):
        pass

    def multi_exprs(self, sep, end):
        ret = []
        self.fail_if_at_end(end)
        typ = self.tokens.next[0]
        if typ == end:
            self.tokens.move_next()
        else:
            arg_parser = Parser(self.tokens, (sep, end))
            while typ != end:
                p = arg_parser.next_expr(None)
                if p is not None:
                    ret.append(p)
                typ = self.tokens.next[0]
                self.tokens.move_next()
                self.fail_if_at_end(end)
        return ret

    def next_expr(self, prev):
        self.fail_if_at_end(";")
        typ, value = self.tokens.next
        if typ in self.stop_at:
            return prev
        self.tokens.move_next()

        if prev is None and typ in ("number", "string", "symbol"):
            return self.next_expr((typ, value))
        elif typ == "operation":
            nxt = self.next_expr(None)
            return self.next_expr(("operation", value, prev, nxt))
        elif typ == "(":
            args = self.multi_exprs(",", ")")
            return self.next_expr(("call", prev, args))
        elif typ == "{":
            params = self.parameter_list()
            body = self.multi_exprs(";", "}")
            return self.next_expr(("function", params, body))
        elif typ == "=":
            if prev[0] != "symbol":
                raise Exception("Can only assign to a symbol")
            nxt = self.next_expr(None)
            return self.next_expr(("assignment", prev, nxt))
        else:
            raise Exception("Unexpected token '%s'" % typ)

def parse(tokens):
    parser = Parser(PeekableStream(tokens), ";")
    while parser.tokens.next is not None:
        p = parser.next_expr(None)
        if p is not None:
            yield p
        parser.tokens.move_next()

def execute(tree, env):
    print(list(tree))

if __name__ == '__main__':
    env = {}

    if len(sys.argv) > 1:
        if sys.argv[1] == '--run':
            f = open(sys.argv[2], 'r')
            text = f.read()
            lines = text.splitlines()
            f.close()

            for line in lines:
                tree = parse(tokenize(line))
                execute(tree, env)
            exit()
    
    while True:
        try:
            text = input('>>> ')
        except EOFError:
            break
        if text:
            tree = parse(tokenize(text))
            execute(tree, env)