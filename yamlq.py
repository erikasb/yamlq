#!/usr/bin/env python

import sys
import yaml
from pyparsing import Optional, CaselessLiteral, Literal, ZeroOrMore, Word, Forward, QuotedString, alphas, nums, alphanums

DOCUMENT_START = "---"

exprStack = []


class Expression(object):

    def eval(self, context):
        pass

    def __repr__(self):
        return self.__str__()


class Field(Expression):

    def __init__(self, path):
        self.path = path

    def eval(self, context):
        def get_something(key, obj):
            if len(key) == 0: return obj
            if isinstance(obj, dict):
                return get_something(key[1:], obj.get(key[0]))
            elif isinstance(obj, list):
                return get_something(key[1:], int(obj[key[0]]))
            else:
                return obj

        return get_something(self.path.split('.'), context)

    def __str__(self):
        return "Field(%s)" % self.path


class Constant(Expression):

    def __init__(self, value):
        self.value = value

    def eval(self, context):
        return self.value

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.value)


class StringConstant(Constant):
    pass


class NumberConstant(Constant):

    def __init__(self, value):
        self.value = long(value)

    def eval(self, context):
        return self.value


class BinaryOperation(object):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def get_values(self, context):
        return (self.left.eval(context), self.right.eval(context))

    def __repr__(self):
        return self.__str__()


class EqualsOperation(BinaryOperation):

    def __init__(self, left, right):
        super(self.__class__, self).__init__(left, right)

    def eval(self, context):
        l, r = self.get_values(context)
        # print "%s == %s: %s" % (l, r, l==r)
        return l == r

    def __str__(self):
        return str(self.left) + " == " + str(self.right)


class NotEqualsOperation(BinaryOperation):

    def __init__(self, left, right):
        super(self.__class__, self).__init__(left, right)

    def eval(self, context):
        l, r = self.get_values(context)
        return l != r

    def __str__(self):
        return str(self.left) + " != " + str(self.right)


class AndOperation(BinaryOperation):

    def __init__(self, left, right):
        super(self.__class__, self).__init__(left, right)

    def eval(self, context):
        l, r = self.get_values(context)
        # print "%s == %s: %s" % (l, r, l==r)
        return l and r

    def __str__(self):
        return str(self.left) + " AND " + str(self.right)


class OrOperation(BinaryOperation):

    def __init__(self, left, right):
        super(self.__class__, self).__init__(left, right)

    def eval(self, context):
        l, r = self.get_values(context)
        # print "%s == %s: %s" % (l, r, l==r)
        return l or r

    def __str__(self):
        return str(self.left) + " OR " + str(self.right)


def pushField(str, loc, toks):
    exprStack.append(Field(toks[0]))
    # pushFirst(str, loc, toks)


def pushString(str, loc, toks):
    exprStack.append(StringConstant(toks[0]))
    # pushFirst(str, loc, toks)


def pushNum(str, loc, toks):
    exprStack.append(NumberConstant(toks[0]))
    # pushFirst(str, loc, toks)

ops = {
    "==": EqualsOperation,
    "!=": NotEqualsOperation,
    "and": AndOperation,
    "or": OrOperation
}

def pushOp(str, loc, toks):
    right, left = (exprStack.pop(), exprStack.pop())
    exprStack.append(ops[toks[1].lower()](left, right))
    print "exprStack:", exprStack
    print "toks:", toks


def pushFirst(str, loc, toks):
    exprStack.append(toks[0])


def defineQueryGrammar():
    fieldSeparator = Literal(".")
    field = Word(alphas, alphanums + ".").setParseAction(pushField)

    string = QuotedString("'").setParseAction(pushString)
    number = (Optional("-") + Word(nums)).setParseAction(pushNum)
    const = number  | string

    eq = Literal("==")
    neq = Literal("!=")
    relation = eq | neq

    lpar = Literal("(").suppress()
    rpar = Literal(")").suppress()

    boolOp = CaselessLiteral("and") | CaselessLiteral("or")

    op = (field + relation + (const | field)).setParseAction(pushOp)
    opInParens = lpar + op + rpar

    fullOp = op | (opInParens + boolOp + opInParens).setParseAction(pushOp)

    return fullOp


def readToFirst():
    while sys.stdin.readline().strip() != DOCUMENT_START:
        pass


def readObject():
    lines = []
    line = sys.stdin.readline()
    while line.strip() != DOCUMENT_START and line != '':
        lines.append(line)
        line = sys.stdin.readline()
    record_string = ''.join(lines)
    return (yaml.safe_load(record_string), record_string)


def getValue(t, p, record):
    if t == "string":
        return p
    if t == "num":
        return long(p)
    if t == "field":
        return getFieldValue(p.split("."), record)


def getFieldValue(path, record):
    if len(path) == 1: return record[path[0]]
    return getFieldValue(path[1:], record[path[0]])


def execQuery(left, right, relation, record):
    leftType = exprStack[0]
    rightType = exprStack[1]
    leftVal = getValue(leftType, left, record)
    rightVal = getValue(rightType, right, record)
    if relation == '==':
        return leftVal == rightVal
    else:
        return leftVal != rightVal


def execEverything(record):
    return all([e.eval(record) for e in exprStack])


query = sys.argv[1]
print "query:", query
defineQueryGrammar().parseString(query)

readToFirst()
while True:
    record, original = readObject()
    if execEverything(record):
        print original
        print "---"
