"""HackerRank: Making Anagrams / Sherlock and Anagrams

Determine if two strings are anagrams and count minimum
character deletions to make them anagrams.
"""

from collections import Counter
from typing import Tuple


def is_anagram(s1: str, s2: str) -> bool:
    """Check whether two strings are anagrams (case-insensitive)."""
    return Counter(s1.lower()) == Counter(s2.lower())


def min_deletions_to_anagram(s1: str, s2: str) -> int:
    """Return the minimum number of character deletions to make s1 and s2 anagrams."""
    c1 = Counter(s1.lower())
    c2 = Counter(s2.lower())
    diff = (c1 - c2) + (c2 - c1)
    return sum(diff.values())


def count_anagram_substrings(s: str) -> int:
    """Count pairs of substrings of s that are anagrams of each other.

    This is the Sherlock and Anagrams problem on HackerRank.
    """
    n = len(s)
    count = 0
    for length in range(1, n):
        freq: dict[tuple, int] = {}
        for i in range(n - length + 1):
            key = tuple(sorted(s[i:i + length]))
            freq[key] = freq.get(key, 0) + 1
        for v in freq.values():
            count += v * (v - 1) // 2
    return count


def run_tests() -> None:
    """Basic assertions."""
    assert is_anagram('listen', 'silent')
    assert not is_anagram('hello', 'world')
    assert min_deletions_to_anagram('abc', 'cde') == 4
    assert count_anagram_substrings('abba') == 4
    print('All tests passed.')


if __name__ == '__main__':
    run_tests()
