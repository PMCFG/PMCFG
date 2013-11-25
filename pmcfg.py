
"""
Reference implementation for the standard PMCFG exchange format.

Two functions are defined: 
- read_grammar(input-files or -lines) reads a grammar into a Python dict
- write_grammar(**grammar) writes a grammar to standard output
"""

from __future__ import print_function

import re
import warnings
import fileinput

# Keywords:
PRAGMA = ":"
RULE = ":"
RULEARROW = "<-"
LINEARIZATION = "="
SEQUENCE = "->"
COMMENT = "#%/-;"

# Regular expression to recognize strings in linearization sequences:
SEQ_REGEXP = re.compile(r'''(?:
( " [^"\\]* (?: \\. [^"\\]* )* "  # - double-quoted string
| ' [^'\\]* (?: \\. [^'\\]* )* '  # - single-quoted string
) 
| (\d+) : (\d+)                   # - arg:ref
) (?: \s+ | $)''', re.VERBOSE)


def is_identifier(s):
    """
    An identifier starts with an alphanumeric character (or "_"), and does not
    contain any whitespace characters.
    """
    return (s and (s[0].isalnum() or s[0] == '_') and 
            not any(c.isspace() for c in s[1:]))


def whitespace_split(s, nrsplits=-1):
    """
    Splits a string on whitespace. Very similar to Python's built-in 
    s.split(None, nrsplits), but pads the result with empty strings 
    so that it always returns (nrsplits+1) strings.
    """
    splits = s.split(None, nrsplits)
    if nrsplits >= 0 and len(splits) <= nrsplits:
        splits += [''] * (nrsplits + 1 - len(splits))
    return splits


def read_sequence(seqstr):
    """
    Splits a string consisting of a linearization sequence
    ... "token" ARG:REF "another token" ...
    into a list of terminal strings and (arg,ref) tuples. 
    """
    tokens = []
    pos = 0
    while pos < len(seqstr):
        m = SEQ_REGEXP.match(seqstr, pos)
        if not m:
            raise SyntaxError("Not a sequence token: %r" % (seqstr[pos:],))
        tok = m.group(1)
        if tok is None:
            tok = tuple(map(int, m.group(2, 3)))
        else:
            tok = eval(tok)
        tokens.append(tok)
        pos = m.end()
    return tokens


def read_rule(rulestr):
    """
    Splits a string consisting of a phrase-structure rule A <- B C ... X
    into a pair (lhs, rhs), where lhs is a string and rhs is a list of strings.
    """
    nonterms = whitespace_split(rulestr)
    if len(nonterms) <= 1 or nonterms[1] != RULEARROW:
        raise SyntaxError("Missing %r after left-hand side in rule" % (RULEARROW,))
    nonterms.pop(1)
    for nt in nonterms:
        if not is_identifier(nt):
            raise SyntaxError("Not an identifier: %r" % (nt,))
    lhs = nonterms.pop(0)
    return (lhs, nonterms)


def read_linearization(linstr):
    """
    Splits a string for a linearization into a list of sequence identifiers.
    """
    sequences = whitespace_split(linstr)
    for seq in sequences:
        if not is_identifier(seq):
            raise SyntaxError("Not an identifier: %r" % (seq,))
    return sequences


def str_token(token):
    if isinstance(token, tuple):
        return "%s:%s" % token
    else:
        return repr(token)


def collect_max_arities(arities, argrefs):
    """
    Collect the maximal arity for each of the arg's
    for each tuple (arg,ref) in the argrefs list.
    """
    for t in argrefs:
        if isinstance(t, tuple):
            arities[t[0]] = max(arities.get(t[0], -1), t[1])


def read_grammar(lines, validate=True):
    """
    Read a PMCFG grammar and return it as a Python dict.
    """
    pragmas = {}
    functions = {}
    linearizations = {}
    sequences = {}
    scores = {}
    nonterms = {}
    fun_arities = {}
    seq_arities = {}
    for line in lines:
        try:
            rest = line.lstrip()
            if not rest or rest[0] in COMMENT:
                continue

            if rest[0] == PRAGMA:
                if rest[1:2].isspace():
                    pragma, info = None, rest[1:]
                else:
                    pragma, info = whitespace_split(rest[1:], 1)
                info = info.strip()
                pragmas.setdefault(pragma, []).append(info)
                continue

            ident, keyword, rest = whitespace_split(rest, 2)
            if not is_identifier(ident):
                raise SyntaxError("Not an identifier: %r" % (ident,))

            if keyword == RULE:
                (lhs, rhs) = read_rule(rest)
                functions.setdefault(ident, []).append((lhs, rhs))
                lhs_arity = nonterms.get(lhs)
                fun_arity = fun_arities.get(ident)
                if fun_arity is not None:
                    if lhs_arity is None:
                        nonterms[lhs] = fun_arity
                    elif lhs_arity != fun_arity:
                        raise ValueError("Nonterminal %r/%s does not match function %r/%s" % (lhs, lhs_arity, ident, fun_arity))
                for r in rhs:
                    nonterms.setdefault(r, None)
                    if (r in linearizations or r in functions or r in sequences):
                        raise ValueError("Nonterminal %r already occurs as a function or a sequence identifier" % (r,))
                if (lhs in linearizations or lhs in functions or lhs in sequences):
                    raise ValueError("Nonterminal %r already occurs as a function or a sequence identifier" % (lhs,))
                if (ident in nonterms or ident in sequences):
                    raise ValueError("Function %r already occurs as a nonterminal or a sequence identifier" % (ident,))

            elif keyword == LINEARIZATION:
                lin = read_linearization(rest)
                if linearizations.get(ident) is not None:
                    raise ValueError("Duplicate linearization for %r" (ident,))
                linearizations[ident] = lin
                fun_arities[ident] = fun_arity = len(lin)
                for lhs, _rhs in functions.get(ident, []):
                    lhs_arity = nonterms.get(lhs)
                    if lhs_arity is None:
                        nonterms[lhs] = fun_arity
                    elif lhs_arity != fun_arity:
                        raise ValueError("Nonterminal %r/%s does not match function %r/%s" % (lhs, lhs_arity, ident, fun_arity))
                for seq in lin:
                    sequences.setdefault(seq, None)
                if (ident in nonterms or ident in sequences):
                    raise ValueError("Function %r already occurs as a nonterminal or a sequence identifier" % (ident,))

            elif keyword == SEQUENCE:
                tokens = read_sequence(rest)
                if sequences.get(ident) is not None:
                    raise ValueError("Duplicate sequence for %r" % (ident,))
                sequences[ident] = tokens
                seq_arities[ident] = {}
                collect_max_arities(seq_arities[ident], tokens)
                if (ident in nonterms or ident in linearizations or ident in functions):
                    raise ValueError("Sequence %r already occurs as a nonterminal or a function" % (ident,))

            else:
                try:
                    score = int(keyword)
                except ValueError:
                    try:
                        score = float(keyword)
                    except ValueError:
                        raise SyntaxError("Not a correct score: %r" % (keyword,))
                if rest:
                    raise SyntaxError("Extra information in score declaration: %r" % (rest,))
                if ident in scores:
                    raise ValueError("Duplicate score for %r" (ident,))
                scores[ident] = score

        except (SyntaxError, ValueError) as err:
            filename = fileinput.filename()
            if filename is None:
                arg = "[happened on input line: %r]" % (line,)
            else:
                lineno = fileinput.lineno()
                arg = "[happened in input file %r, line %s: %r]" % (filename, lineno, line)
            raise type(err)(err.args[0] + ' ' + arg)
            # raise type(err)(arg) from err

    if validate:
        undefined_nonterms = set(nt for nt, arity in nonterms.items() if arity is None)
        if undefined_nonterms:
            warnings.warn("Undefined nonterminals: %s" % (" ".join(undefined_nonterms),), SyntaxWarning)

        undefined_sequences = set(seq for seq, tokens in sequences.items() if tokens is None)
        if undefined_sequences:
            warnings.warn("Undefined sequences: %s" % (" ".join(undefined_sequences),), SyntaxWarning)

        for fun, rules in functions.items():
            lin = linearizations.get(fun)
            if lin is None:
                warnings.warn("Missing linearization for function %r" % (fun,), SyntaxWarning)
                continue
            arities = {}
            for seq in lin:
                collect_max_arities(arities, seq_arities[seq].items())
            fun_arity = fun_arities[fun]
            for lhs, rhs in rules:
                lhs_arity = nonterms[lhs]
                if fun_arity != lhs_arity:
                    warnings.warn("Nonterminal %r/%s does not match function %r/%s" % (lhs, lhs_arity, ident, fun_arity), SyntaxWarning)
                for arg, maxref in arities.items():
                    if arg >= len(rhs):
                        warnings.warn("Linearization for %r refers to argument #%s, but must be <%s" % (fun, arg, len(rhs)), SyntaxWarning)
                    rhs_arity = nonterms.get(rhs[arg])
                    if rhs_arity is None:
                        warnings.warn("Missing definition for nonterminal %r" % (rhs[arg],), SyntaxWarning)
                    elif rhs_arity <= maxref:
                        warnings.warn("Reference #%s.%s in linearization for %r does not match arity %r/%s" % (arg, maxref, fun, rhs[arg], rhs_arity), SyntaxWarning)

    return dict(pragmas = pragmas,
                functions = functions,
                linearizations = linearizations,
                sequences = sequences,
                scores = scores,
                nonterms = nonterms,
                )


def iteritems(kvlist):
    """
    Iterate over (key, value) pairs in a sequence. 
    The sequence can be a list/tuple/iterator over (key, value) tuples,
    or a dict over values. 
    """
    if isinstance(kvlist, dict):
        return kvlist.items()
    else:
        return kvlist


def write_grammar(pragmas, functions, linearizations, sequences, scores=None, **unused):
    """
    Write a PMCFG to standard output.

    All arguments should be mappings from identifiers to values.
    For pragmas and functions, the mapping can be one-to-many, i.e., it can be a 
    dict from identifiers to lists of values. But for linearizations, sequences 
    and scores, the mapping must be one-to-one.
    """
    print()
    if pragmas:
        print("%s Pragmas" % (COMMENT[0],))
        for pid, prgms in iteritems(pragmas):
            if pid is None: 
                pid = ""
            if not isinstance(prgms, (list, tuple, set)):
                prgms = [prgms]
            for prg in prgms:
                print("%s%s %s" % (PRAGMA, pid, prg))
        print()
    print("%s Functions/rules" % (COMMENT[0],))
    for fid, rules in iteritems(functions):
        if isinstance(rules, tuple) and len(rules) == 2:
            rules = [rules]
        for lhs, rhs in rules:
            print("%s %s %s %s %s" % (fid, RULE, lhs, RULEARROW, " ".join(rhs)))
    print()
    print("%s Linearizations" % (COMMENT[0],))
    for fid, lin in iteritems(linearizations):
        print("%s %s %s" % (fid, LINEARIZATION, " ".join(lin)))
    print()
    print("%s Sequences" % (COMMENT[0],))
    for sid, seq in iteritems(sequences):
        print("%s %s %s" % (sid, SEQUENCE, " ".join(map(str_token, seq))))
    print()
    print("%s Sequences" % (COMMENT[0],))
    for sid, seq in iteritems(sequences):
        print("%s %s %s" % (sid, SEQUENCE, " ".join(map(str_token, seq))))
    print()
    if scores:
        print("%s Scores" % (COMMENT[0],))
        for fid, score in iteritems(scores):
            print("%s %s" % (fid, score))
        print()


if __name__ == '__main__':
    grammar = read_grammar(fileinput.input())
    write_grammar(**grammar)

