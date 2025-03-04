import pytest

from parsita import (
    Failure,
    GeneralParsers,
    ParseError,
    RecursionError,
    SequenceReader,
    Success,
    any1,
    eof,
    failure,
    first,
    fwd,
    lit,
    opt,
    pred,
    reg,
    rep,
    rep1,
    rep1sep,
    repsep,
    success,
    until,
)


def test_literals():
    class TestParsers(GeneralParsers):
        a = lit("a")
        ab = lit("ab")

    assert TestParsers.a.parse("a") == Success("a")
    assert TestParsers.ab.parse("ab") == Success("ab")
    assert TestParsers.ab.parse("abb") == Failure(ParseError(SequenceReader("abb", 2), ["end of source"]))
    assert TestParsers.ab.parse("ca") == Failure(ParseError(SequenceReader("ca", 0), ["a"]))
    assert TestParsers.ab.parse("ac") == Failure(ParseError(SequenceReader("ac", 1), ["b"]))
    assert str(TestParsers.a) == "a = 'a'"
    assert str(TestParsers.ab) == "ab = 'ab'"


def test_regex():
    class TestParsers(GeneralParsers):
        status_code = reg(b"\d+")
        status = reg(b"[^\n]*")
        http_response = status_code << lit(b" ") & status

    assert TestParsers.http_response.parse(b"404 Not Found") == Success([b"404", b"Not Found"])


def test_multiple_literals():
    class TestParsers(GeneralParsers):
        ab = lit("a", "b")

    assert TestParsers.ab.parse("a") == Success("a")
    assert TestParsers.ab.parse("b") == Success("b")


def test_predicate():
    class TestParsers(GeneralParsers):
        a = pred(any1, lambda x: x in ("A", "a"), "letter A")
        d = pred(any1, str.isdigit, "digit")

    assert TestParsers.a.parse("a") == Success("a")
    assert TestParsers.a.parse("A") == Success("A")
    assert TestParsers.d.parse("2") == Success("2")
    assert TestParsers.d.parse("23") == Failure(ParseError(SequenceReader("23", 1), ["end of source"]))
    assert TestParsers.d.parse("a") == Failure(ParseError(SequenceReader("a", 0), ["digit"]))
    assert str(TestParsers.a) == "a = pred(any1, letter A)"


def test_forward_declaration():
    class TestParsers(GeneralParsers):
        a = b
        b = lit("b")

    assert TestParsers.a.parse("b") == Success("b")
    assert TestParsers.a.parse("ab") == Failure(ParseError(SequenceReader("ab", 0), ["b"]))


def test_forward_expression():
    class TestParsers(GeneralParsers):
        a = lit("a")
        ca = c | a
        da = d & a
        c = lit("c")
        d = lit("d")

    assert TestParsers.ca.parse("c") == Success("c")
    assert TestParsers.ca.parse("a") == Success("a")
    assert TestParsers.da.parse("da") == Success(["d", "a"])
    assert str(TestParsers.ca) == "ca = c | a"
    assert str(TestParsers.da) == "da = d & a"


def test_manual_forward():
    class TestParsers(GeneralParsers):
        b = fwd()
        a = "a" & b
        b.define("b" & opt(a))

    assert TestParsers.a.parse("ab") == Success(["a", ["b", []]])
    assert TestParsers.a.parse("abab") == Success(["a", ["b", [["a", ["b", []]]]]])


def test_manual_forward_mutual():
    class TestParsers(GeneralParsers):
        a = fwd()
        b = fwd()
        a.define("a" & b)
        b.define("b" & opt(a))

    assert TestParsers.a.parse("ab") == Success(["a", ["b", []]])
    assert TestParsers.a.parse("abab") == Success(["a", ["b", [["a", ["b", []]]]]])


def test_multiple_references():
    class TestParsers(GeneralParsers):
        a = lit("a")
        cora = c | a
        canda = c & a
        c = "c"

    assert TestParsers.cora.parse("c") == Success("c")
    assert TestParsers.cora.parse("a") == Success("a")
    assert TestParsers.canda.parse("ca") == Success(["c", "a"])
    assert str(TestParsers.cora) == "cora = 'c' | a"
    assert str(TestParsers.canda) == "canda = 'c' & a"


def test_optional():
    class TestParsers(GeneralParsers):
        a = lit("a")
        b = opt(a)

    assert TestParsers.b.parse("a") == Success(["a"])
    assert TestParsers.b.parse("c") == Failure(ParseError(SequenceReader("c", 0), ["a", "end of source"]))
    assert str(TestParsers.b) == "b = opt(a)"


def test_optional_longer():
    class TestParsers(GeneralParsers):
        a = lit("ab")
        b = opt(a)

    assert TestParsers.b.parse("ab") == Success(["ab"])
    assert TestParsers.b.parse("ac") == Failure(ParseError(SequenceReader("ac", 1), ["b"]))
    assert str(TestParsers.b) == "b = opt(a)"


def test_optional_literal():
    class TestParsers(GeneralParsers):
        b = opt("ab")

    assert TestParsers.b.parse("ab") == Success(["ab"])
    assert TestParsers.b.parse("ac") == Failure(ParseError(SequenceReader("ac", 1), ["b"]))
    assert str(TestParsers.b) == "b = opt('ab')"


def test_alternative():
    class TestParsers(GeneralParsers):
        a = lit("a")
        b = lit("b")
        c = lit("cd")
        ab = a | b
        bc = b | c

    assert TestParsers.ab.parse("a") == Success("a")
    assert TestParsers.ab.parse("b") == Success("b")
    assert TestParsers.ab.parse("c") == Failure(ParseError(SequenceReader("c", 0), ["a", "b"]))
    assert TestParsers.bc.parse("cd") == Success("cd")
    assert TestParsers.bc.parse("ce") == Failure(ParseError(SequenceReader("ce", 1), ["d"]))
    assert str(TestParsers.bc) == "bc = b | c"


def test_multiple():
    class TestParsers(GeneralParsers):
        a = lit("aaaa")
        b = lit("bbb")
        c = lit("cc")
        d = lit("d")
        back = a | (b | c | d)
        front = (a | b | c) | d
        both = (a | b) | c | d

    for parser in [TestParsers.back, TestParsers.front, TestParsers.both]:
        assert parser.parse("aaaa") == Success("aaaa")
        assert parser.parse("cc") == Success("cc")
        assert parser.parse("bbc") == Failure(ParseError(SequenceReader("bbc", 2), ["b"]))
        assert parser.parse("bbba") == Failure(ParseError(SequenceReader("bbba", 3), ["end of source"]))

    str(TestParsers.back), "back = a | b | c | d"
    str(TestParsers.front), "front = a | b | c | d"
    str(TestParsers.both), "both = a | b | c | d"


def test_right_or():
    class TestParsers(GeneralParsers):
        ab = "a" | lit("b")

    assert TestParsers.ab.parse("a") == Success("a")


def test_multiple_messages_duplicate():
    class TestParsers(GeneralParsers):
        a = lit("a")
        ab = a & "b"
        ac = a & "c"
        either = ab | ac

    assert TestParsers.either.parse("cc") == Failure(ParseError(SequenceReader("cc", 0), ["a"]))


def test_first():
    class TestParsers(GeneralParsers):
        a = lit("a")
        either = first(a, "b")

    assert str(TestParsers.either) == "either = first(a, 'b')"


def test_sequential():
    class TestParsers(GeneralParsers):
        a = lit("a")
        b = lit("b")
        c = lit("cd")
        ab = a & b
        bc = b & c
        abc = a & b & c

    assert TestParsers.ab.parse("ab") == Success(["a", "b"])
    assert TestParsers.bc.parse("bcd") == Success(["b", "cd"])
    assert TestParsers.abc.parse("abcd") == Success(["a", "b", "cd"])
    assert TestParsers.abc.parse("abc") == Failure(ParseError(SequenceReader("abc", 3), ["d"]))
    assert TestParsers.abc.parse("abf") == Failure(ParseError(SequenceReader("abf", 2), ["c"]))
    assert str(TestParsers.abc) == "abc = a & b & c"


def test_discard_left():
    class TestParsers(GeneralParsers):
        a = lit("a")
        b = lit("b")
        ab = a >> b
        ac = a >> c
        c = lit("c")

    assert TestParsers.ab.parse("ab") == Success("b")
    assert TestParsers.ac.parse("ac") == Success("c")
    assert str(TestParsers.ac) == "ac = a >> c"


def test_discard_right():
    class TestParsers(GeneralParsers):
        a = lit("a")
        b = lit("b")
        ab = a << b
        ac = a << c
        c = lit("c")

    assert TestParsers.ab.parse("ab") == Success("a")
    assert TestParsers.ac.parse("ac") == Success("a")
    assert TestParsers.ac.parse("aa") == Failure(ParseError(SequenceReader("aa", 1), ["c"]))
    assert str(TestParsers.ac) == "ac = a << c"


def test_discard_bare_literals():
    class TestParsers(GeneralParsers):
        a = lit("a")
        b = "b"
        rshift = a >> b
        rrshift = b >> a
        lshift = a << b
        rlshift = b << a

    assert TestParsers.rshift.parse("ab") == Success("b")
    assert TestParsers.rrshift.parse("ba") == Success("a")
    assert TestParsers.lshift.parse("ab") == Success("a")
    assert TestParsers.rlshift.parse("ba") == Success("b")


def test_repeated():
    class TestParsers(GeneralParsers):
        bs = rep1("b")
        cs = rep("c")

    assert TestParsers.bs.parse("bbbb") == Success(["b", "b", "b", "b"])
    assert TestParsers.bs.parse("b") == Success(["b"])
    assert TestParsers.bs.parse("") == Failure(ParseError(SequenceReader("", 0), ["b"]))
    assert TestParsers.bs.parse("bbbc") == Failure(ParseError(SequenceReader("bbbc", 3), ["b", "end of source"]))
    assert TestParsers.cs.parse("ccc") == Success(["c", "c", "c"])
    assert TestParsers.cs.parse("c") == Success(["c"])
    assert TestParsers.cs.parse("") == Success([])
    assert TestParsers.cs.parse("cccb") == Failure(ParseError(SequenceReader("cccb", 3), ["c", "end of source"]))
    assert str(TestParsers.bs) == "bs = rep1('b')"
    assert str(TestParsers.cs) == "cs = rep('c')"


def test_repeated_with_bounds():
    assert rep("b", min=2).parse("bbbb") == Success(["b", "b", "b", "b"])
    assert rep("b", max=5).parse("bbbb") == Success(["b", "b", "b", "b"])
    assert rep("b", min=3, max=5).parse("bbbb") == Success(["b", "b", "b", "b"])
    assert rep("b", min=4, max=4).parse("bbbb") == Success(["b", "b", "b", "b"])
    assert isinstance(rep("b", min=5).parse("bbbb"), Failure)
    assert isinstance(rep("b", max=3).parse("bbbb"), Failure)


def test_repeated_longer():
    class TestParsers(GeneralParsers):
        bf = rep1("bf")
        cf = rep("cf")

    assert TestParsers.bf.parse("bfbf") == Success(["bf", "bf"])
    assert TestParsers.bf.parse("bf") == Success(["bf"])
    assert TestParsers.bf.parse("") == Failure(ParseError(SequenceReader("", 0), ["b"]))
    assert TestParsers.bf.parse("bfbc") == Failure(ParseError(SequenceReader("bfbc", 3), ["f"]))
    assert TestParsers.cf.parse("cfcfcf") == Success(["cf", "cf", "cf"])
    assert TestParsers.cf.parse("cf") == Success(["cf"])
    assert TestParsers.cf.parse("") == Success([])
    assert TestParsers.cf.parse("cfcb") == Failure(ParseError(SequenceReader("cfcb", 3), ["f"]))
    assert str(TestParsers.bf) == "bf = rep1('bf')"
    assert str(TestParsers.cf) == "cf = rep('cf')"


def test_repeated_separated():
    class TestParsers(GeneralParsers):
        bs = rep1sep("b", ",")
        cs = repsep("c", ",")

    assert TestParsers.bs.parse("b,b,b") == Success(["b", "b", "b"])
    assert TestParsers.bs.parse("b") == Success(["b"])
    assert TestParsers.bs.parse("") == Failure(ParseError(SequenceReader("", 0), ["b"]))
    assert TestParsers.cs.parse("c,c,c") == Success(["c", "c", "c"])
    assert TestParsers.cs.parse("c") == Success(["c"])
    assert TestParsers.cs.parse("") == Success([])
    assert str(TestParsers.bs) == "bs = rep1sep('b', ',')"
    assert str(TestParsers.cs) == "cs = repsep('c', ',')"


def test_repeated_separated_nonliteral():
    class TestParsers(GeneralParsers):
        bs = rep1sep("b", opt(","))
        cs = repsep("c", opt(","))

    assert TestParsers.bs.parse("b,bb") == Success(["b", "b", "b"])
    assert TestParsers.bs.parse("b") == Success(["b"])
    assert TestParsers.bs.parse("") == Failure(ParseError(SequenceReader("", 0), ["b"]))
    assert TestParsers.cs.parse("cc,c") == Success(["c", "c", "c"])
    assert TestParsers.cs.parse("c") == Success(["c"])
    assert TestParsers.cs.parse("") == Success([])
    assert str(TestParsers.bs) == "bs = rep1sep('b', opt(','))"
    assert str(TestParsers.cs) == "cs = repsep('c', opt(','))"


def test_repeated_separated_with_bounds():
    assert repsep("b", ",", min=2).parse("b,b,b,b") == Success(["b", "b", "b", "b"])
    assert repsep("b", ",", max=5).parse("b,b,b,b") == Success(["b", "b", "b", "b"])
    assert repsep("b", ",", min=3, max=5).parse("b,b,b,b") == Success(["b", "b", "b", "b"])
    assert repsep("b", ",", min=4, max=4).parse("b,b,b,b") == Success(["b", "b", "b", "b"])
    assert isinstance(repsep("b", ",", min=4, max=4).parse("b,b,b,b,"), Failure)
    assert isinstance(repsep("b", ",", min=5).parse("b,b,b,b"), Failure)
    assert isinstance(repsep("b", ",", max=3).parse("b,b,b,b"), Failure)
    assert isinstance(repsep("b", ",", min=5).parse("b,b,b,b,"), Failure)


@pytest.mark.timeout(2)
def test_infinite_recursion_protection():
    class TestParsers(GeneralParsers):
        bad_rep = rep(opt("a"))
        bad_rep1 = rep1(opt("a"))
        bad_repsep = repsep(opt("a"), opt(":"))
        bad_rep1sep = rep1sep(opt("a"), opt(":"))

    # Recursion happens in middle of stream
    for parser in (TestParsers.bad_rep, TestParsers.bad_rep1, TestParsers.bad_repsep, TestParsers.bad_rep1sep):
        with pytest.raises(RecursionError) as actual:
            parser.parse("aab")
        assert actual.value == RecursionError(parser, SequenceReader("aab", 2))
        assert str(actual.value) == (
            f"Infinite recursion detected in {parser!r}; "
            f"empty string was matched and will be matched forever at index 2 before b"
        )

    # Recursion happens at end of stream
    for parser in (TestParsers.bad_rep, TestParsers.bad_rep1, TestParsers.bad_repsep, TestParsers.bad_rep1sep):
        with pytest.raises(RecursionError) as actual:
            parser.parse("aa")
        assert actual.value == RecursionError(parser, SequenceReader("aa", 2))
        assert str(actual.value) == (
            f"Infinite recursion detected in {parser!r}; "
            f"empty string was matched and will be matched forever at end of source"
        )


def test_conversion():
    class TestParsers(GeneralParsers):
        one = lit("1") > int
        two = lit("2") > int
        twelve = one & two > (lambda x: x[0] * 10 + x[1])

        def make_twentyone(x):
            return x[0] * 10 + x[1]

        twentyone = two & one > make_twentyone

    assert TestParsers.one.parse("1") == Success(1)
    assert TestParsers.twelve.parse("12") == Success(12)
    assert TestParsers.twentyone.parse("21") == Success(21)
    assert str(TestParsers.twelve) == "twelve = one & two"
    assert str(TestParsers.twentyone) == "twentyone = two & one"


def test_recursion():
    class TestParsers(GeneralParsers):
        one = lit("1") > float
        six = lit("6") > float
        eleven = lit("11") > float

        numbers = eleven | one | six

        def make_expr(x):
            digits1, maybe_expr = x
            if maybe_expr:
                digits2 = maybe_expr[0]
                return digits1 + digits2
            else:
                return digits1

        expr = numbers & opt("+" >> expr) > make_expr

    assert TestParsers.expr.parse("11") == Success(11)
    assert TestParsers.expr.parse("6+11") == Success(17)
    assert TestParsers.expr.parse("1+6+6") == Success(13)


def test_protection():
    class TestParsers(GeneralParsers):
        ab = lit("a") & lit("b")
        abc = ab & "c"
        dab = "d" & ab

    assert TestParsers.abc.parse("abc") == Success([["a", "b"], "c"])
    assert TestParsers.dab.parse("dab") == Success(["d", ["a", "b"]])


def test_eof_protection():
    class TestParsers(GeneralParsers):
        end_a = "a" << eof
        b = lit("b")
        bba = rep(b | end_a)

    assert TestParsers.bba.parse("bba") == Success(["b", "b", "a"])
    assert TestParsers.bba.parse("a") == Success(["a"])
    assert TestParsers.bba.parse("ab") == Failure(ParseError(SequenceReader("ab", 1), ["end of source"]))
    assert str(TestParsers.end_a) == "end_a = 'a' << eof"


def test_success_failure_protection():
    class TestParsers(GeneralParsers):
        aaa = rep("a") & success(1) & rep("b")
        bbb = "aa" & failure("something else") & "bb"

    assert TestParsers.aaa.parse("aabb") == Success([["a", "a"], 1, ["b", "b"]])
    assert TestParsers.aaa.parse("") == Success([[], 1, []])
    assert TestParsers.bbb.parse("aabb") == Failure(ParseError(SequenceReader("aabb", 2), ["something else"]))
    assert str(TestParsers.aaa) == "aaa = rep('a') & success(1) & rep('b')"
    assert str(TestParsers.bbb) == "bbb = 'aa' & failure('something else') & 'bb'"


def test_until_parser():
    block_start = "aa"
    block_stop = "bb"

    class TestParser(GeneralParsers):
        ambiguous = block_start >> until(block_stop) << block_stop

    ambiguous_content = """ababa"""
    content = f"""{block_start}{ambiguous_content}{block_stop}"""
    result = TestParser.ambiguous.parse(content)
    assert result == Success(ambiguous_content)

    empty_content = f"""{block_start}{block_stop}"""
    result_2 = TestParser.ambiguous.parse(empty_content)
    assert result_2 == Success("")

    no_termination_content = f"""{block_start}{ambiguous_content}"""
    result_3 = TestParser.ambiguous.parse(no_termination_content)
    assert result_3 == Failure(ParseError(SequenceReader(no_termination_content, 7), ["b"]))


def test_any():
    class TestParsers(GeneralParsers):
        any2 = any1 & any1

    assert TestParsers.any2.parse("ab") == Success(["a", "b"])
    assert TestParsers.any2.parse("a") == Failure(ParseError(SequenceReader("a", 1), ["anything"]))
    assert str(TestParsers.any2) == "any2 = any1 & any1"


def test_nested_class():
    class TestOuter(GeneralParsers):
        start = "%"

        class TestInner(GeneralParsers):
            inner = '"' >> rep(lit("a", "b", "c")) << '"'

        wrapped = "(" >> TestInner.inner << ")"

        outer = start >> wrapped

    assert TestOuter.outer.parse('%("abc")') == Success(["a", "b", "c"])
    assert isinstance(TestOuter.outer.parse('%("abc ")'), Failure)
    assert isinstance(TestOuter.outer.parse(' %("abc")'), Failure)
    assert isinstance(TestOuter.outer.parse('%("abc") '), Failure)


def test_disallow_instatiation():
    class TestParsers(GeneralParsers):
        a = lit("a")
        bb = lit("bb")

    with pytest.raises(TypeError):
        _ = TestParsers()
