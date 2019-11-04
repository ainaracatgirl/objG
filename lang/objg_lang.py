import sys
import re
import inspect

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

    def fail_if_at_end(self, expected):
        if self.tokens.next is None:
            raise Exception("Hit end of file - expected '%s'." % expected)

    def parameters_list(self):
        if self.tokens.next[0] != "@":
            return []
        self.tokens.move_next()
        typ = self.tokens.next[0]
        if typ != "(":
            raise Exception("'@' must be followed by '(' in a function.")
        self.tokens.move_next()
        ret = self.multi_exprs(",", ")")
        for param in ret:
            if param[0] != "symbol":
                raise Exception(
                    "Only symbols are allowed in function parameter lists."
                    + " Found: " + str(param) + "."
                )
        return ret

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

class Env:
    def __init__(self, parent=None):
        self.parent = parent
        self.items = {}

    def get(self, name):
        if name in self.items:
            return self.items[name]
        elif self.parent is not None:
            return self.parent.get(name)
        else:
            return None
    
    def set(self, name, value):
        if name in self.items:
            self.items[name] = value
        elif self.parent is not None and name in self.parent.items:
            self.parent.items[name] = value
        else:
            self.items[name] = value

def fail_if_wrong_number_of_args(fn_name, params, args):
    if len(params) != len(args):
        raise Exception((
            "%d arguments passed to function %s, but %d required."
        ) % (len(args), fn_name, len(params)))

def _function_call(expr, env):
    fn = eval_expr(expr[1], env)
    args = list((eval_expr(a, env) for a in expr[2]))
    if fn[0] == "function":
        params = fn[1]
        fail_if_wrong_number_of_args(expr[1], params, args)
        body = fn[2]
        fn_env = fn[3]
        new_env = Env(fn_env)
        for p, a in zip(params, args):
            new_env.set(p[1], a)
        return eval_list(body, new_env)
    elif fn[0] == "native":
        py_fn = fn[1]
        params = inspect.getargspec(py_fn).args
        fail_if_wrong_number_of_args(expr[1], params, args)
        return fn[1](env, *args)
    else:
        raise Exception("Tried to call something that was not a function")

def eval_expr(expr, env):
    typ = expr[0]
    if typ == "number": return ("number", float(expr[1]))
    elif typ == "string": return ("string", str(expr[1]))
    elif typ == "none": return ("none",)
    elif typ == "operation":
        arg1 = eval_expr(expr[2], env)
        arg2 = eval_expr(expr[3], env)
        if expr[1] == "+":
            return ("number", arg1[1] + arg2[1])
        elif expr[1] == "-":
            return ("number", arg1[1] - arg2[1])
        elif expr[1] == "*":
            return ("number", arg1[1] * arg2[1])
        elif expr[1] == "/":
            return ("number", arg1[1] / arg2[1])
        else:
            raise Exception("Unknown operator '%s'" % expr[1])
    elif typ == "symbol":
        name = expr[1]
        ret = env.get(name)
        if ret is None:
            raise Exception("Undefined symbol '%s'" % name)
        else:
            return ret
    elif typ == "assignment":
        var_name = expr[1][1]
        val = eval_expr(expr[2], env)
        env.set(var_name, val)
        return val
    elif typ == "call":
        return _function_call(expr, env)
    elif typ == "function":
        return ("function", expr[1], expr[2], Env(env))
    else:
        raise Exception("Unknown expression type: %s" % typ)

def eval_iter(exprs, env):
    for expr in exprs:
        yield eval_expr(expr, env)


def eval_list(exprs, env):
    ret = ("none",)
    for expr in eval_iter(exprs, env):
        ret = expr
    return ret

def evaluate(tree, env):
    print(list(eval_list(tree, env)))

if __name__ == '__main__':
    env = Env()

    if len(sys.argv) > 1:
        if sys.argv[1] == '--run':
            f = open(sys.argv[2], 'r')
            text = f.read()
            f.close()

            toks = tokenize(text)
            tree = parse(toks)
            evaluate(tree, env)