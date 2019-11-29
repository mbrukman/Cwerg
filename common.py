from pycparser import c_ast
from typing import List

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
    ("void",): (-1, c_ast.IdentifierType(["void"])),
}

ALLOWED_IDENTIFIER_TYPES = {t[1] for t in CANONICAL_BASE_TYPE.values()}

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


def CanonicalizeIdentifierType(names: List[str]):
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


def GetCanonicalIdentifierType(names):
    return CANONICAL_BASE_TYPE[CanonicalizeIdentifierType(names)][1]


def TypeCompare(t1: c_ast.IdentifierType, t2: c_ast.IdentifierType):
    i1 = CANONICAL_BASE_TYPE[tuple(t1.names)][0]
    i2 = CANONICAL_BASE_TYPE[tuple(t2.names)][0]
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
        else:
            assert False, parent
    elif isinstance(parent, c_ast.Compound):
        for n, e in enumerate(parent.block_items):
            if e is old_node:
                parent.block_items[n] = new_node
                return
        else:
            assert False, parent
    elif isinstance(parent, c_ast.For):
        if parent.next is old_node:
            parent.next = new_node
        elif parent.stmt is old_node:
            parent.stmt = new_node
        elif parent.cond is old_node:
            parent.cond = new_node
        elif parent.init is old_node:
            parent.init = new_node
        else:
            assert False, parent
    elif isinstance(parent, c_ast.If):
        if parent.cond is old_node:
            parent.cond = new_node
        elif parent.iftrue is old_node:
            parent.iftrue = new_node
        elif parent.iffalse is old_node:
            parent.iffalse = new_node
        else:
            assert False, parent
    else:
        assert False, parent


def ReplaceBreakAndContinue(node, parent, test_label, exit_label):
    if isinstance(node, c_ast.Continue):
        ReplaceNode(parent, node, c_ast.Goto(test_label))
        return
    if exit_label and isinstance(node, c_ast.Break):
        ReplaceNode(parent, node, c_ast.Goto(exit_label))
        return

    if isinstance(node, (c_ast.While, c_ast.DoWhile, c_ast.For)):
        return

    if isinstance(node, c_ast.Switch):
        # breaks inside switches have their own meaning
        exit_label = None

    for c in node:
        ReplaceBreakAndContinue(c, node, test_label, exit_label)
