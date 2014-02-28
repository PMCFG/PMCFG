
Specification of the PMCFG grammar format
===========================================

The PMCFG grammar format is line-based -- a grammar consists of a number of declarations, each on a separate line. A declaration consists of a sequence of tokens separated by whitespace. There are currently six different types of declarations (including comments):

    # This is a comment
    / This is also a comment
    * So is this...
    - ...and this

This is a pragma (or flag) with name `prg` and value `some sort of value`:

    :prg some sort of value

This is a rule definition, with name `f`, lefthand side `A` and righthand side `B`, `C`, `D`:

     f : A <- B C D

This is a linearization definition, for function `f`, consisting of sequences `s1`, `s2`, `s3`:

     f = s1 s2 s3

This is a sequence definition, for sequence `s1`, consisting of two terminal strings `"t1"` and `"t2"`, and one argument reference `2:3`:

     s1 => "t1" 2:3 't2'

This is definition of a probabilistic ranking of 3.4 for function `f`:

     f 3.4

In order to give different names to a single rule, there is a shorthand notation which is as follows.

     f : A <- B C D
     g : A <- B C D

is equivalent to writing

     f g : A <- B C D

The same shorthand notation can be used for linearization definitions:

     f = s1 s2 s3
     g = s1 s2 s3

is equivalent to

     f g = s1 s2 s3

All pragma names, function names, rule nonterminals and sequence names are *identifiers*. An identifier must start with an alphanumeric character, followed by any number of non-whitespace characters.

In sequence definitions, the strings can contain whitespace or any other character until the end-quote. Strings are delimited either by double-quote (") or by single-quote ('). The interpretation of a string is the same as string literals in Python or Javascript.

The encoding is assumed to be UTF-8. But in order to simplify implementations, the grammar format does not make use of the Unicode character classes, instead it assumes that:

- An alphanumeric character is an ASCII letter, digit or underscore, i.e., `[a-zA-Z0-9_]`. This is equivalent to the `\w` character class in Python regular expressions (without the flags LOCALE or UNICODE).
- A whitespace character is any of `[ \t\n\r\f\v]`. This is equivalent to the `\s` character class in Python regular expressions (without the flags LOCALE or UNICODE). 
- Only spaces and tabs `[ \t]` are allowed as whitespace delimiters within a line, the other whitespace characters `[\n\r\f\v]` are line separators.
- Using Python regexps, identifiers are defined by `\w\S*`. This means that identifiers are allowed to contain Unicode whitespace such as NON-BREAKING-SPACE, but this is of course deprecated.
- String literals can contain spaces and tabs, but not line-breaking characters.

EBNF for the PMCFG grammar format
------------------------------------

The following is a EBNF definition of the grammat format:

    PMCFG ::= (WS|NL)* Decl (Linesep Decl)+ (WS|NL)*
    Linesep ::= (WS|NL)* NL (WS|NL)*

    Decl    ::= Comment | Pragma | Score | Rule | Lin | Linseq

    Comment ::= Cmnt NonNL* 
    Pragma  ::= ":" Ident? (WS+ NonNL*)?
    Rule    ::= (Ident WS+)+ ":" WS+ Ident "<-" (WS+ Ident)*
    Lin     ::= (Ident WS+)+ "=" (WS+ Ident)*
    Linseq  ::= Ident WS+ "=>" (WS+ Symbol)*
    Score   ::= Ident WS+ (Int|Float)

    Symbol  ::= Argref | Token
    Argref  ::= Int ":" Int

Lexikal tokens, defined using Python/Perl regular expressions:

    Int     ::= [0-9]+
    Float   ::= [0-9]+ \. [0-9]+
    Ident   ::= [a-zA-Z0-9_] [^ \t\n\r\f\v]*
    Token   ::= " ([^"\n\r\f\v] | \\ ")* "
             |  ' ([^'\n\r\f\v] | \\ ')* '

    WS    ::= [ \t]
    NL    ::= [\n\r\f\v]
    NonNL ::= [^\n\r\f\v]
    Cmnt  ::= [#/*-]

It is not adviced to implement this EBNF directly in a parser. Instead it is probably easier to first split the grammar into a list of lines and then parse each line. 

