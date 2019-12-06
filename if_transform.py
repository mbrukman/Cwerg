#!/usr/bin/python3
"""
Ensures that if statements only have gotos in iftrue/iffalse and that
cond only consists of a simple expression.

"""
from pycparser import c_ast

import common
import meta

__all__ = ["IfTransform"]

branch_counter = 0


def GetLabel(prefix="branch"):
    global branch_counter
    branch_counter += 1
    return "%s_%s" % (prefix, branch_counter)


def ConvertToGotos(if_stmt: c_ast.If, parent, meta):
    if (isinstance(if_stmt.iftrue, c_ast.Goto) and
            isinstance(if_stmt.iffalse, c_ast.Goto) and
            not isinstance(if_stmt.cond, c_ast.ExprList)):
        return

    labeltrue = GetLabel()
    labelfalse = GetLabel()
    labelend = GetLabel()
    emptytrue  = common.IsEmpty(if_stmt.iftrue) or isinstance(if_stmt.iftrue, c_ast.Goto)
    emptyfalse =  common.IsEmpty(if_stmt.iffalse) or isinstance(if_stmt.iffalse, c_ast.Goto)


    seq = []
    # TODO: this should be done in  EliminateExpressionLists(
    if isinstance(if_stmt.cond, c_ast.ExprList):
        exprs = if_stmt.cond.exprs
        if_stmt.cond = exprs.pop(-1)
        seq += exprs
    seq.append(if_stmt)
    if not emptytrue:
        seq += [c_ast.Label(labeltrue, c_ast.EmptyStatement()), if_stmt.iftrue]
        if not emptyfalse:
            seq.append(c_ast.Goto(labelend))
    if not emptyfalse:
        seq += [c_ast.Label(labelfalse, c_ast.EmptyStatement()), if_stmt.iffalse]
    seq.append(c_ast.Label(labelend, c_ast.EmptyStatement()))

    if not isinstance(if_stmt.iftrue, c_ast.Goto):
         if_stmt.iftrue = c_ast.Goto(labelend if emptytrue else labeltrue)
    if not isinstance(if_stmt.iffalse, c_ast.Goto):
         if_stmt.iffalse = c_ast.Goto(labelend if emptyfalse else labelfalse)

    stmts = common.GetStatementList(parent)
    if not stmts:
        stmts = [if_stmt]
        parent = common.ReplaceNode(parent, if_stmt, c_ast.Compound(stmts))

    pos = stmts.index(if_stmt)
    stmts[pos: pos+1]  = seq


def IfTransform(ast: c_ast.Node, meta: meta.MetaInfo):
    """ make sure that there is not expression list inside the condition and that the
     true and false consist of at most a goto.
     This should be run after the loop conversions"""
    candidates = common.FindMatchingNodesPostOrder(ast, ast, lambda n, _: isinstance(n, c_ast.If))

    for if_stmt, parent in candidates:
        ConvertToGotos(if_stmt, parent, meta)
