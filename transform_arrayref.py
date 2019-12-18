from pycparser import c_ast

"""
This code eliminates ArrayRef nodes and replaces them  with pointer arithmetic.
It also collapses ArrayDecl of multi-dimensional arrays.
TODO: fix array initializers for multi-dimensional arrays.

This is probably the most subtle code in the project

Note the ArrayRefs, e.g.
board[i][j])
are parsed left to right
 ArrayRef:             --> type is char
     ArrayRef:         --> type is ArrayDecl(char))
         ID: board     --> type is ArrayDecl(ArrayDecl(char))
         ID: i
     ID: j
But the ArrayDecls, e.g.
char board[10][20];
are parsed right to left
  ArrayDecl: []
      ArrayDecl: []
          TypeDecl: board, []
              IdentifierType: ['char']
          Constant: int, 20
      Constant: int, 10
"""

import common
import meta

__all__ = ["ConvertArrayIndexToPointerDereference",
           "ConvertConvertAddressTakenScalarsToArray"]


def GetStride(node):
    stride = 1
    while node and isinstance(node, c_ast.ArrayDecl):
        assert isinstance(node.dim, c_ast.Constant), node.dim
        assert node.dim.type == "int"
        stride *= int(node.dim.value)
        node = node.type
    return stride


def GetArrayRefMultiplier(node, type):
    if isinstance(type, c_ast.ArrayDecl):
        return GetStride(type)
    elif isinstance(type, c_ast.IdentifierType):
        return 1
    elif isinstance(type, c_ast.PtrDecl):
        return 1
    else:
        assert False, type


def MakeCombinedSubscript(chain_head, meta_info):
    """
    Return the node reflecting the name computation  and the combined offset

    """
    # print ("INPUT", chain_head)
    assert isinstance(chain_head, c_ast.ArrayRef)
    subscripts = []
    node = chain_head
    while isinstance(node, c_ast.ArrayRef):
        old_subscript = node.subscript
        assert meta_info.type_links[old_subscript] in common.ALLOWED_IDENTIFIER_TYPES
        multiplier = GetArrayRefMultiplier(node, meta_info.type_links[node])
        if common.IsZeroConstant(old_subscript):
            pass
        elif multiplier == 1:
            subscripts.append(old_subscript)
        else:
            new_subscript = c_ast.BinaryOp("*", old_subscript, c_ast.Constant("int", str(multiplier)))
            subscripts.append(new_subscript)
            meta_info.type_links[new_subscript] = meta_info.type_links[old_subscript]
            meta_info.type_links[new_subscript.right] = common.GetCanonicalIdentifierType(["int"])

        node = node.name
        if not isinstance(meta_info.type_links[node], c_ast.ArrayDecl):
            break
    if not subscripts:
        return node, None
    s = subscripts[0]
    for x in subscripts[1:]:
        s = c_ast.BinaryOp("+", s, x)
        # TODO: compute the max type
        meta_info.type_links[s] = meta_info.type_links[x]
    # print ("OUTPUT-NAME", node)
    # print ("OUTPUT-SUBS", s)

    return node, s


def CollapseArrayDeclChain(head):
    assert isinstance(head, c_ast.ArrayDecl)
    dim = 1
    node = head
    while isinstance(node, c_ast.ArrayDecl):
        if node.dim:
            assert isinstance(node.dim, c_ast.Constant), node.dim
            assert node.dim.type == "int"
            dim *= int(node.dim.value)
        else:
            dim = 0
        node = node.type
    head.type = node
    if dim == 0:
        head.dim = None
    else:
        head.dim.value = str(dim)


def ConvertArrayIndexToPointerDereference(ast, meta_info):
    """
    Phase 1:  a[1][2] = b; -> *(a + 1 * 10 + 2) = b;

    Phase 2:  int a[5][10]; -> int a[50];
    """
    def IsArrayRefChainHead(node, parent):
        if not isinstance(node, c_ast.ArrayRef): return False
        name_type = meta_info.type_links[node.name]
        if not isinstance(name_type, c_ast.ArrayDecl): return True
        if not isinstance(parent, c_ast.ArrayRef): return True
        return False

    ref_chains = common.FindMatchingNodesPostOrder(ast, ast, IsArrayRefChainHead)
    for chain_head, parent in ref_chains:
        name, s = MakeCombinedSubscript(chain_head, meta_info)
        if s is None:
            addr = name
        else:
            addr = c_ast.BinaryOp("+", name, s)
        head_type = meta_info.type_links[chain_head]
        # TODO:  low confidence - double check this
        meta_info.type_links[addr] = meta_info.type_links[name]
        if isinstance(head_type, c_ast.ArrayDecl):
            # the array ref sequence only partially indexes the array, so the result is just an address
            common.ReplaceNode(parent, chain_head, addr)
        else:
            deref = c_ast.UnaryOp("*", addr)
            meta_info.type_links[deref] = meta_info.type_links[chain_head]  # expression has not changed
            common.ReplaceNode(parent, chain_head, deref)

    def IsArrayDeclChainHead(node, parent):
        if not isinstance(node, c_ast.ArrayDecl): return False
        return not isinstance(parent, c_ast.ArrayDecl)

    decl_chains = common.FindMatchingNodesPreOrder(ast, ast, IsArrayDeclChainHead)
    for chain_head, parent in decl_chains:
        CollapseArrayDeclChain(chain_head)


def IsScalarType(type):
    if isinstance(type, c_ast.TypeDecl):
        return IsScalarType(type.type)

    return isinstance(type, c_ast.IdentifierType)


def ConvertConvertAddressTakenScalarsToArray(ast, meta_info: meta.MetaInfo):
    def IsAddressTakenScalar(node, _):
        if not isinstance(node, c_ast.UnaryOp): return False
        if node.op != "&": return False
        if not isinstance(node.expr, c_ast.ID): return False
        type = meta_info.type_links[node.expr]
        return IsScalarType(type)

    candidates = common.FindMatchingNodesPreOrder(ast, ast, IsAddressTakenScalar)
    ids = {}
    for node, _ in candidates:
        ids[meta_info.sym_links[node.expr]] = None

    one = c_ast.Constant("int", "1")
    meta_info.type_links[one] = meta.INT_IDENTIFIER_TYPE

    for node in ids:
        assert isinstance(node, c_ast.Decl)
        node.type = c_ast.ArrayDecl(node.type, one, [])
        if node.init:
            node.init = c_ast.InitList([node.init])

    def IsAddressTakenScalarId(node, _):
        return isinstance(node, c_ast.ID) and meta_info.sym_links[node] in ids

    candidates = common.FindMatchingNodesPreOrder(ast, ast, IsAddressTakenScalarId)

    zero = c_ast.Constant("int", "0")
    meta_info.type_links[zero] = meta.INT_IDENTIFIER_TYPE
    for node, parent in candidates:
        array_ref = c_ast.ArrayRef(node, zero)
        meta_info.type_links[array_ref] = meta_info.type_links[node]
        common.ReplaceNode(parent, node, array_ref)
