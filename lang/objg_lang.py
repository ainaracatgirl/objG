import sys, os, re, inspect, json, base64

COMPILER_INPUT = None

# BUILT-IN FUNCTIONS
def builtin_print(env, value):
    print(eval_expr(value, env)[1])
    return eval_expr(value, env)

def builtin_str(env, value):
    return str(eval_expr(value, env)[1])

def builtin_import(env, value):
    f = open(str(eval_expr(value, env)[1]))
    ff = f.read()
    f.close()
    toks = tokenize(ff)
    tree = parse(toks)
    evaluate(tree, env)
    return ("none",)

def builtin_if(env, condition, when_true, when_false):
    condition = eval_expr(condition, env)[1]
    if condition == 1:
        eval_expr(("call", when_true, ()), env)
    else:
        eval_expr(("call", when_false, ()), env)
    return ("none",)

def builtin_while(env, condition, statement):
    while eval_expr(condition, env)[1] == 1:
        eval_expr(("call", statement, ()), env)
    return ("none",)

def builtin_equals(env, value1, value2):
    value1 = eval_expr(value1, env)[1]
    value2 = eval_expr(value2, env)[1]
    if value1 == value2:
        return ("number", 1)
    return ("number", 0)

# CODE
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
        elif c in "#":
            _scan_string("\n", chars)
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
            params = self.parameters_list()
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
        
        self.set("print",   ("native", builtin_print))
        self.set("str",     ("native", builtin_str))
        self.set("import",  ("native", builtin_import))
        self.set("if",      ("native", builtin_if))
        self.set("while",   ("native", builtin_while))
        self.set("equals",  ("native", builtin_equals))
        self.set("true",    ("number", 1.0))
        self.set("false",   ("number", 0.0))
        self.set("None",    ("none",))

    def has(self, name):
        if name in self.items:
            return True
        elif self.parent is not None:
            return self.parent.has(name)
        else:
            return False

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
        elif self.parent is not None and self.parent.has(name):
            self.parent.set(name, value)
        else:
            self.items[name] = value
    
    def merge(self, other, replace=False):
        if replace:
            for item in other.items:
                set(item, other.items[item])
        else:
            for item in other.items:
                if item not in self.items:
                    set(item, other.items[item])

def fail_if_wrong_number_of_args(fn_name, params, args, diff=0):
    if diff == 1:
        if len(params) - len(args) == -1:
            raise Exception((
                "%d arguments passed to function %s, but %d required."
            ) % (len(args), fn_name, len(params) - 1))
    else:
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
        new_env = Env(parent=fn_env)
        for p, a in zip(params, args):
            new_env.set(p[1], a)
        return eval_list(body, new_env)
    elif fn[0] == "native":
        py_fn = fn[1]
        params = inspect.getfullargspec(py_fn).args
        fail_if_wrong_number_of_args(expr[1], params, args, diff=1)
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
        return ("function", expr[1], expr[2], Env(parent=env))
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
    eval_list(tree, env)

if __name__ == '__main__':
    env = Env()

    if len(sys.argv) > 1:
        if sys.argv[1] == '--run':
            if sys.argv[2].endswith(".bin"):
                f = open(sys.argv[2], 'rb')
                text = f.read()
                f.close()

                decoded = base64.b85decode(text).decode('utf-8')
                tree = json.loads(decoded)
                evaluate(tree, env)
            else:
                f = open(sys.argv[2], 'r')
                text = f.read()
                f.close()

                toks = tokenize(text)
                tree = parse(toks)
                evaluate(tree, env)
        elif sys.argv[1] == '--compile':
            print("Reading source code...")
            f = open(sys.argv[2], 'r')
            text = f.read()
            f.close()

            print("Extracting tokens...")
            toks = tokenize(text)
            print("Generatring AST...")
            tree = parse(toks)
            print("Converting to bytes...")
            _json = json.dumps(list(tree))
            encoded = base64.b85encode(_json.encode('utf-8'))
            print("Writing bytes...")
            f = open(sys.argv[2].split('.')[0] + '.bin', 'wb')
            f.write(encoded)
            f.close()
            print("Finished!")
    else:
        if COMPILER_INPUT is not None:
            toks = tokenize(COMPILER_INPUT)
            tree = parse(toks)
            evaluate(tree, env)