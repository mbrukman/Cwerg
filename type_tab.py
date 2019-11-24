#!/usr/bin/python3

"""
Just like the sym_tab module links symbols with their definition,
type_tab links expressons wirh the corresponding TypeDecl.
Alongt the way also fill in the missing symbol links we could
not resolve in sym_tab


By far the biggest complication results from struct/union dereference
which require both symbol and type links to be available.
"""


from pycparser import c_parser, c_ast, parse_file
import sym_tab


class TypeTab:

    def __init__(self):
        self.links = {}

    def link_expr(self, node, type):
        # TODO: add missing classes as needed
        assert isinstance(type,
                          (str, list, c_ast.TypeDecl,
                           c_ast.ArrayDecl, c_ast.PtrDecl)
                          ), "unexpected type %s" % type
        self.links[node] = type


_EXPRESSION_CLASSES = (c_ast.ArrayRef,
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


def IsExpression(node):
    return isinstance(node, _EXPRESSION_CLASSES)


def GetTypeForID(decl):
    if isinstance(decl, c_ast.TypeDecl):
        return decl
    elif isinstance(decl, c_ast.PtrDecl):
        return decl
    elif isinstance(decl, c_ast.FuncDecl):
        decl = decl.type
        assert isinstance(decl, (c_ast.TypeDecl, c_ast.PtrDecl))
        return decl
    elif isinstance(decl, c_ast.ArrayDecl):
        return decl
    else:
        assert False, decl


def GetArgType(arg):
    if isinstance(arg, c_ast.Decl):
        return arg.type
    elif isinstance(arg, c_ast.Typename):
        return arg.type
    elif isinstance(arg, c_ast.EllipsisParam):
        return arg
    else:
        assert False, arg


def TypePrettyPrint(decl):
    if isinstance(decl, str):
        return decl
    elif isinstance(decl, c_ast.TypeDecl):
        if isinstance(decl.type, c_ast.Struct):
            return "struct " + decl.type.name
        elif isinstance(decl.type, c_ast.IdentifierType):
            return "-".join(decl.type.names)
        else:
            assert False, decl.type

    elif isinstance(decl, c_ast.EllipsisParam):
        return "..."
    elif isinstance(decl, list):
        return [TypePrettyPrint(x) for x in decl]
    else:
        return decl.__class__.__name__


# This needs a lot more work and may be too simplistic
# But note that the standard dictates: signed x unsigned -> unsigned
# (citation needed)
_NUM_TYPE_ORDER = [
    "signed-char", "char", "unsigned-char",
    "signed-short", "short", "unsigned-short",
    "signed-int", "signed", "int", "unsigned-int", "unsigned",
    "long",
    "float", "double"
]


def GetBinopType(t1, t2):
    if isinstance(t1, c_ast.TypeDecl):
        t1 = t1.type.names[0]
    if isinstance(t2, c_ast.TypeDecl):
        t2 = t2.type.names[0]
    if t1 == t2:
        return t1
    if t1 in _NUM_TYPE_ORDER and t2 in _NUM_TYPE_ORDER:
        m = max(_NUM_TYPE_ORDER.index(t1), _NUM_TYPE_ORDER.index(t2))
        return _NUM_TYPE_ORDER[m]
    return "UNKWON"


def _GetStructUnion(decl, sym_links):
    if isinstance(decl, c_ast.TypeDecl):
        struct = decl.type
        assert isinstance(struct, c_ast.Struct)
        return sym_links[struct]
    else:
        assert False, decl


def _FindStructMember(struct, field):
    for member in struct.decls:
        if member.name == field.name:
            return member
    assert False, "cannot field %s in struct %s" % (field, struct)


def _GetFieldRefTypeAndUpdateSymbolLink(node, parent, sym_links, type_tab):
    assert isinstance(parent,  c_ast.StructRef)
    # Note: we assume here that the name side of the AST has already been processed
    base = type_tab.links[parent.name]
    field = parent.field
    struct = _GetStructUnion(type_tab.links[parent.name], sym_links)
    # print ("@@ STRUCT BASE @@", base)
    # print ("@@ STRUCT FIELD @@", field)
    assert isinstance(field, c_ast.ID)
    assert sym_links[field] == sym_tab.UNRESOLVED_STRUCT_UNION_MEMBER
    # print ("@@ STRUCT DECL @@", struct)
    member = _FindStructMember(struct, field)
    sym_links[field] = member
    return member.type


def TypeForNode(node, parent, sym_links, type_tab, child_types, fundef):

    if isinstance(node, (c_ast.Constant)):
        return node.type
    elif isinstance(node, (c_ast.ID)):
        if isinstance(parent, c_ast.StructRef) and parent.field == node:
            return _GetFieldRefTypeAndUpdateSymbolLink(node, parent, sym_links, type_tab)
        else:
            decl = sym_links[node].type
            return GetTypeForID(decl)
    elif isinstance(node, (c_ast.BinaryOp)):
        return GetBinopType(child_types[0], child_types[1])
    elif isinstance(node, (c_ast.UnaryOp)):
        if node.op == "sizeof":
            # really size_t
            return "unsigned"
        return child_types[0]
    elif isinstance(node, (c_ast.FuncCall)):
        return child_types[0]
    elif isinstance(node, (c_ast.ArrayRef)):
        a = child_types[0]
        assert isinstance(a, (c_ast.ArrayDecl, c_ast.PtrDecl)
                          ), a.__class__.__name__
        # TODO: check that child_types[1] is integer
        return a.type
    elif isinstance(node, (c_ast.Return)):
        return fundef.decl.type.type
    elif isinstance(node, (c_ast.Assignment)):
        return child_types[0]
    elif isinstance(node, (c_ast.ExprList)):
        # unfortunately ExprList have mutliple uses which we need to disambiguate
        if isinstance(parent, c_ast.FuncCall):
            args = sym_links[parent.name].type.args
            assert isinstance(args, c_ast.ParamList)
            return [GetArgType(x) for x in args.params]
        else:
            return child_types[-1]
    elif isinstance(node, c_ast.TernaryOp):
        return GetBinopType(child_types[1], child_types[2])
    elif isinstance(node, c_ast.StructRef):
        # This was computed by _GetFieldRefTypeAndUpdateSymbolLink
        return child_types[1]
    elif isinstance(node, c_ast.Cast):
        return node.to_type.type
    else:
        assert False, "unsupported expression node %s" % node


def Typify(node, parent, type_tab, sym_links, fundef):
    """Determine the type of all expression  nodes and record it in type_tab"""
    if isinstance(node, c_ast.FuncDef):
        print("\nFUNCTION [%s]" % node.decl.name)
        fundef = node

    child_types = [Typify(c, node, type_tab, sym_links, fundef) for c in node]

    if not IsExpression(node):
        return None

    t = TypeForNode(node, parent, sym_links, type_tab, child_types, fundef)

    print (node.__class__.__name__, TypePrettyPrint(t),
           [TypePrettyPrint(x) for x in child_types])
    type_tab.link_expr(node, t)
    return t


if __name__ == "__main__":
    import sys

    def main(filename):
        ast = parse_file(filename, use_cpp=True)
        stab = sym_tab.ExtractSymTab(ast)
        su_tab = sym_tab.ExtractStructUnionTab(ast)
        sym_links = {}
        sym_links.update(stab.links)
        sym_links.update(su_tab.links)

        # sym_tab.VerifySymtab(stab, ast)
        type_tab = TypeTab()
        Typify(ast, None, type_tab, sym_links, None)

    for filename in sys.argv[1:]:
        main(filename)
