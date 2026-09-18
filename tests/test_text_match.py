"""
Regression tests for src.text_match -- the whole-word keyword matcher that
replaced plain `keyword in text` substring matching after that substring
bug was found to misclassify real postings (see src/config.py and
src/collectors/board_apis.py docstrings).
"""

from src.text_match import any_keyword_present, keyword_present, matched_keywords


def test_intern_does_not_match_internal():
    assert not keyword_present("intern", "internal tools engineer")


def test_intern_does_not_match_international():
    assert not keyword_present("intern", "director, international tax")


def test_intern_does_not_match_internals():
    assert not keyword_present("intern", "database internals engineer")


def test_intern_does_not_match_interned_past_tense():
    assert not keyword_present("intern", "previously interned at a fintech startup")


def test_intern_matches_standalone_word():
    assert keyword_present("intern", "software engineering intern - summer 2027")


def test_internship_matches_standalone_word():
    assert keyword_present("internship", "summer internship program")


def test_ai_does_not_match_substring_of_maintain_or_domain():
    assert not keyword_present("ai", "you'll maintain services in this domain")


def test_ai_matches_standalone_word():
    assert keyword_present("ai", "ai engineering intern")


def test_java_does_not_match_javascript():
    assert not keyword_present("java", "javascript developer")


def test_java_matches_standalone_word():
    assert keyword_present("java", "backend engineer with java experience")


def test_symbol_containing_keyword_matches():
    assert keyword_present("c++", "c++ software engineer")
    assert keyword_present("c#", "c# developer")


def test_multi_word_phrase_matches():
    assert keyword_present("machine learning", "machine learning engineer intern")


def test_any_keyword_present():
    assert any_keyword_present(["sales", "marketing", "engineer"], "software engineer intern")
    assert not any_keyword_present(["sales", "marketing"], "software engineer intern")


def test_matched_keywords_preserves_order_and_excludes_substrings():
    keywords = ["python", "java", "ai"]
    text = "python and java backend intern, maintain domain services"
    assert matched_keywords(keywords, text) == ["python", "java"]
