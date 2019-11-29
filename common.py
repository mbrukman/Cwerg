from pycparser import c_ast

EXPRESSION_NODES = (c_ast.ArrayRef,
                    c_ast.Assignment,
                    c_ast.BinaryOp,
                    c_ast.Cast,
                    c_ast.Constant,
                    c_ast.ExprList,
                    c_ast.FuncCall,
                    c_ast.ID,
                    c_ast.Return,
                    c_ast.StructRef,
                    c_ast.TernaryOp,
                    c_ast.UnaryOp)

POST_INC_DEC_OPS = {
    "p--",
    "p++",
}

PRE_INC_DEC_OPS = {
    "++",
    "--",
}

SAME_TYPE_UNARY_OPS = {
    "++",
    "--",
    "p--",
    "p++",
    "-",
    "~",
}

BOOL_INT_TYPE_UNARY_OPS = {
    "!",
}

SAME_TYPE_BINARY_OPS = {
    "+",
    "-",
    "^",
    "*",
    "/",
    "|",
    "&",
    "%",
    "<<",
    ">>",
}

# Note: this would be bool in C++
BOOL_INT_TYPE_BINARY_OPS = {
    "==",
    "!=",
    "<=",
    "<",
    ">=",
    ">",
    "&&",
    "||",
}

SHORT_CIRCUIT_OPS = {
    "&&",
    "||",
}

OPS_REQUIRING_BOOL_INT = {
    "&&",
    "||",
    "!",  # unary
}

# Note that the standard dictates: signed x unsigned -> unsigned
# (citation needed)
CANONICAL_BASE_TYPE = {
    ("char",): (1, c_ast.IdentifierType(["char"])),
    ("char", "unsigned",): (2, c_ast.IdentifierType(["char", "unsigned"])),
    ("short",): (3, c_ast.IdentifierType(["short"])),
    ("short", "unsigned",): (4, c_ast.IdentifierType(["short", "unsigned"])),
    ("int",): (5, c_ast.IdentifierType(["int"])),
    ("int", "unsigned",): (6, c_ast.IdentifierType(["int", "unsigned"])),
    ("long",): (7, c_ast.IdentifierType(["long"])),
    ("long", "unsigned",): (8, c_ast.IdentifierType(["long", "unsigned"])),
    ("long", "long",): (9, c_ast.IdentifierType(["long", "long"])),
    ("long", "long", "unsigned",): (10, c_ast.IdentifierType(["long", "long", "unsigned"])),
    ("float",): (11, c_ast.IdentifierType(["float"])),
    ("double",): (12, c_ast.IdentifierType(["double"])),
    # unrelated
    ("string",): (-1, c_ast.IdentifierType(["string"])),
}

_CANONICAL_IDENTIFIER_TYPE_MAP = {
    ("char", "signed"): ("char",),
    ("short", "signed"): ("short",),
    ("int", "signed"): ("int",),
    ("long", "signed"): ("long",),
    ("int", "short"): ("short",),
    ("int", "long"): ("long",),
    ("signed",): ("int",),
    ("unsigned",): ("int", "unsigned"),
}


def CanonicalizeIdentifierType(names):
    """Return a sorted and simplified string tuple"""
    n = sorted(names)
    if len(names) <= 2:
        x = _CANONICAL_IDENTIFIER_TYPE_MAP.get(tuple(n))
        return x if x else tuple(n)
    if "int" in n:
        n.remove("int")
    if "signed" in n:
        n.remove("signed")
    return tuple(n)


def TypeCompare(t1: c_ast.IdentifierType, t2: c_ast.IdentifierType):
    n1 = CanonicalizeIdentifierType(t1.names)
    n2 = CanonicalizeIdentifierType(t2.names)
    i1 = CANONICAL_BASE_TYPE[n1][0]
    i2 = CANONICAL_BASE_TYPE[n2][0]
    if i1 == i2:
        return "="
    elif i1 < i2:
        return "<"
    else:
        return ">"


def MaxType(t1, t2):
    if isinstance(t1, c_ast.PtrDecl) and isinstance(t2, c_ast.PtrDecl):
        # maybe do some more checks
        return t1

    assert isinstance(t1, c_ast.IdentifierType) and isinstance(t2, c_ast.IdentifierType)
    cmp = TypeCompare(t1, t2)
    if cmp == "=" or cmp == ">":
        return t1
    else:
        return t2


def NodePrettyPrint(node: c_ast):
    if node is None:
        return "none"
    elif isinstance(node, c_ast.ID):
        return "id[%s]" % node.name
    elif isinstance(node, c_ast.BinaryOp):
        return "op[%s]" % node.op
    elif isinstance(node, c_ast.UnaryOp):
        return "op[%s]" % node.op
    else:
        return node.__class__.__name__


def ReplaceNode(parent, old_node, new_node):
    # TODO: add nodes as needed
    if isinstance(parent, c_ast.ExprList):
        for n, e in enumerate(parent.exprs):
            if e is old_node:
                parent.exprs[n] = new_node
                return
    if isinstance(parent, c_ast.Compound):
        for n, e in enumerate(parent.block_items):
            if e is old_node:
                parent.block_items[n] = new_node
                return
    elif isinstance(parent, c_ast.For):
        if parent.next is old_node:
            parent.next = new_node
            return
        if parent.stmt is old_node:
            parent.stmt = new_node
            return
        if parent.cond is old_node:
            parent.cond = new_node
            return
        if parent.init is old_node:
            parent.init = new_node
            return
    assert False, parent
