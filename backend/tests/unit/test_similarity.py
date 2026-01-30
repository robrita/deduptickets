"""
Unit tests for text similarity utilities.

Tests TF-IDF vectorization, cosine similarity, and text matching.
"""

from __future__ import annotations

import pytest

from deduptickets.lib.similarity import (
    TextSimilarityCalculator,
    compute_idf,
    compute_tf,
    compute_tfidf,
    cosine_similarity,
    jaccard_similarity,
    quick_similarity,
    tokenize,
)


class TestTokenize:
    """Tests for tokenize function."""

    def test_tokenize_basic(self) -> None:
        """Should tokenize basic text into words."""
        result = tokenize("Hello World")
        assert result == ["hello", "world"]

    def test_tokenize_removes_punctuation(self) -> None:
        """Should remove punctuation from tokens."""
        result = tokenize("Hello, World! How are you?")
        assert "hello" in result
        assert "world" in result
        assert "," not in "".join(result)
        assert "!" not in "".join(result)

    def test_tokenize_empty_string(self) -> None:
        """Should return empty list for empty string."""
        result = tokenize("")
        assert result == []

    def test_tokenize_single_char_words_removed(self) -> None:
        """Should remove single-character words."""
        result = tokenize("I am a test")
        assert "i" not in result
        assert "a" not in result
        assert "am" in result
        assert "test" in result

    def test_tokenize_lowercase(self) -> None:
        """Should convert all tokens to lowercase."""
        result = tokenize("HELLO World HeLLo")
        assert all(word.islower() for word in result)


class TestComputeTf:
    """Tests for term frequency computation."""

    def test_compute_tf_basic(self) -> None:
        """Should compute correct term frequencies."""
        tokens = ["apple", "banana", "apple"]
        tf = compute_tf(tokens)
        assert tf["apple"] == pytest.approx(2 / 3)
        assert tf["banana"] == pytest.approx(1 / 3)

    def test_compute_tf_empty(self) -> None:
        """Should return empty dict for empty tokens."""
        tf = compute_tf([])
        assert tf == {}

    def test_compute_tf_single_token(self) -> None:
        """Should compute TF for single token."""
        tf = compute_tf(["word"])
        assert tf["word"] == 1.0


class TestComputeIdf:
    """Tests for inverse document frequency computation."""

    def test_compute_idf_basic(self) -> None:
        """Should compute correct IDF values with smoothed formula."""
        docs = [
            ["apple", "banana"],
            ["banana", "cherry"],
            ["apple", "cherry"],
        ]
        idf = compute_idf(docs)
        # banana appears in 2 docs, cherry in 2, apple in 2
        # Smoothed IDF: log(1 + 3/2) = log(2.5) ≈ 0.916
        assert idf["apple"] == pytest.approx(0.916, abs=0.01)
        assert idf["banana"] == pytest.approx(0.916, abs=0.01)
        assert idf["cherry"] == pytest.approx(0.916, abs=0.01)

    def test_compute_idf_empty(self) -> None:
        """Should return empty dict for empty corpus."""
        idf = compute_idf([])
        assert idf == {}

    def test_compute_idf_unique_terms(self) -> None:
        """Should give higher IDF to rare terms."""
        docs = [
            ["common", "rare"],
            ["common"],
            ["common"],
        ]
        idf = compute_idf(docs)
        # rare appears in 1 doc, common in 3
        assert idf["rare"] > idf["common"]


class TestComputeTfidf:
    """Tests for TF-IDF vector computation."""

    def test_compute_tfidf_basic(self) -> None:
        """Should compute correct TF-IDF values."""
        tokens = ["apple", "apple", "banana"]
        idf = {"apple": 0.5, "banana": 1.0}
        tfidf = compute_tfidf(tokens, idf)
        # TF(apple) = 2/3, TF(banana) = 1/3
        # TF-IDF = TF * IDF
        assert tfidf["apple"] == pytest.approx((2 / 3) * 0.5)
        assert tfidf["banana"] == pytest.approx((1 / 3) * 1.0)


class TestCosineSimilarity:
    """Tests for cosine similarity computation."""

    def test_cosine_similarity_identical(self) -> None:
        """Should return 1.0 for identical vectors."""
        vec = {"a": 1.0, "b": 2.0}
        similarity = cosine_similarity(vec, vec)
        assert similarity == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self) -> None:
        """Should return 0.0 for orthogonal vectors."""
        vec1 = {"a": 1.0}
        vec2 = {"b": 1.0}
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0)

    def test_cosine_similarity_partial_overlap(self) -> None:
        """Should compute correct similarity for partial overlap."""
        vec1 = {"a": 1.0, "b": 1.0}
        vec2 = {"a": 1.0, "c": 1.0}
        similarity = cosine_similarity(vec1, vec2)
        # Only 'a' overlaps
        assert 0.0 < similarity < 1.0

    def test_cosine_similarity_empty(self) -> None:
        """Should return 0.0 for empty vectors."""
        assert cosine_similarity({}, {"a": 1.0}) == 0.0
        assert cosine_similarity({"a": 1.0}, {}) == 0.0
        assert cosine_similarity({}, {}) == 0.0


class TestJaccardSimilarity:
    """Tests for Jaccard similarity computation."""

    def test_jaccard_identical(self) -> None:
        """Should return 1.0 for identical texts."""
        similarity = jaccard_similarity("hello world", "hello world")
        assert similarity == pytest.approx(1.0)

    def test_jaccard_different(self) -> None:
        """Should return 0.0 for completely different texts."""
        similarity = jaccard_similarity("apple banana", "cherry orange")
        assert similarity == pytest.approx(0.0)

    def test_jaccard_partial(self) -> None:
        """Should compute correct similarity for overlapping texts."""
        similarity = jaccard_similarity("hello world", "hello there")
        # Intersection = {hello}, Union = {hello, world, there}
        assert similarity == pytest.approx(1 / 3)

    def test_jaccard_empty(self) -> None:
        """Should handle empty strings."""
        assert jaccard_similarity("", "") == 1.0  # Both empty = identical
        assert jaccard_similarity("hello", "") == 0.0


class TestQuickSimilarity:
    """Tests for quick similarity function."""

    def test_quick_similarity_identical(self) -> None:
        """Should return high similarity for identical texts."""
        similarity = quick_similarity(
            "Payment failed for order 12345",
            "Payment failed for order 12345",
        )
        assert similarity > 0.99

    def test_quick_similarity_similar(self) -> None:
        """Should return moderate similarity for similar texts."""
        similarity = quick_similarity(
            "Payment failed for order 12345",
            "Payment error on order 12345",
        )
        # Similar texts should have positive similarity
        assert 0.2 < similarity < 1.0

    def test_quick_similarity_different(self) -> None:
        """Should return low similarity for different texts."""
        similarity = quick_similarity(
            "Payment failed for order 12345",
            "Login issue with username incorrect",
        )
        assert similarity < 0.3


class TestTextSimilarityCalculator:
    """Tests for TextSimilarityCalculator class."""

    def test_calculator_similarity(self) -> None:
        """Should compute similarity between two texts."""
        calc = TextSimilarityCalculator()
        similarity = calc.similarity(
            "Payment failed error message",
            "Payment error with failure",
        )
        assert 0.0 <= similarity <= 1.0

    def test_calculator_find_similar(self) -> None:
        """Should find similar documents above threshold."""
        calc = TextSimilarityCalculator()

        query = "Payment failed for order"
        candidates = [
            "Payment error for order",  # Similar
            "Login failed for user",  # Somewhat similar
            "Account settings updated",  # Different
        ]

        results = calc.find_similar(query, candidates, threshold=0.3)

        # Should find at least the first candidate
        assert len(results) >= 1
        # Results should be sorted by score descending
        if len(results) > 1:
            assert results[0][1] >= results[1][1]

    def test_calculator_find_similar_empty_candidates(self) -> None:
        """Should return empty list for no candidates."""
        calc = TextSimilarityCalculator()
        results = calc.find_similar("query", [], threshold=0.5)
        assert results == []

    def test_calculator_fit(self) -> None:
        """Should fit calculator on corpus."""
        calc = TextSimilarityCalculator()
        corpus = [
            "Payment failed",
            "Login error",
            "Account issue",
        ]
        calc.fit(corpus)
        # After fitting, calculator should have IDF values
        assert len(calc._idf) > 0

    def test_calculator_add_document(self) -> None:
        """Should add documents incrementally."""
        calc = TextSimilarityCalculator()
        calc.add_document("First document")
        calc.add_document("Second document")
        assert len(calc._corpus_tokens) == 2
