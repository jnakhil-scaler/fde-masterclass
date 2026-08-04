from app.product_matching import match_product_hint


class FakeProduct:
    def __init__(self, id, name):
        self.id = id
        self.name = name


def test_matches_exact_name():
    products = [FakeProduct(1, "TMT Sariya 10mm"), FakeProduct(2, "Ambuja Cement")]
    result = match_product_hint("TMT Sariya 10mm", products)
    assert result.id == 1


def test_matches_case_insensitive_substring():
    products = [FakeProduct(1, "TMT Sariya 10mm"), FakeProduct(2, "Ambuja Cement")]
    result = match_product_hint("tmt sariya", products)
    assert result.id == 1


def test_fuzzy_matches_close_spelling():
    products = [FakeProduct(1, "TMT Sariya 10mm"), FakeProduct(2, "Ambuja Cement")]
    result = match_product_hint("TMT Saria 10 mm", products)
    assert result.id == 1


def test_returns_none_for_no_match():
    products = [FakeProduct(1, "TMT Sariya 10mm")]
    result = match_product_hint("Completely Unrelated Widget", products)
    assert result is None


def test_returns_none_for_empty_hint():
    products = [FakeProduct(1, "TMT Sariya 10mm")]
    assert match_product_hint("", products) is None
