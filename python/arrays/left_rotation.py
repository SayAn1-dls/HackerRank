"""
HackerRank: Arrays - Left Rotation
https://www.hackerrank.com/challenges/ctci-array-left-rotation/problem

Problem:
  A left rotation operation on an array shifts each of the array's elements
  1 unit to the left. Given an integer d, rotate the array's elements to the
  left d times and return the resulting array.

Example:
  arr = [1, 2, 3, 4, 5], d = 2
  After 2 left rotations: [3, 4, 5, 1, 2]

Approach:
  Instead of rotating one position at a time (O(n*d)), we use slicing.
  The key insight is that rotating left by d positions is equivalent to:
    result = arr[d:] + arr[:d]
  This gives us O(n) time complexity.

  We also handle the edge case where d >= n by using d % n,
  since rotating by n positions returns the original array.

Complexity:
  Time:  O(n) — single pass to construct the rotated array
  Space: O(n) — we create a new list for the result
"""


def left_rotate(arr: list, d: int) -> list:
    """
    Rotate array to the left by d positions.

    Args:
        arr: List of integers to rotate
        d: Number of left rotations to perform

    Returns:
        New list with elements rotated left by d positions
    """
    if not arr or d == 0:
        return arr[:]

    n = len(arr)
    # Normalize d in case it's larger than array length
    d = d % n

    if d == 0:
        return arr[:]

    # Slice and concatenate: take elements from index d onwards,
    # then append elements from 0 to d
    return arr[d:] + arr[:d]


def left_rotate_in_place(arr: list, d: int) -> None:
    """
    Rotate array to the left by d positions in-place using reversal algorithm.
    This approach uses O(1) extra space.

    Algorithm (three reversals):
      1. Reverse the first d elements
      2. Reverse the remaining n-d elements
      3. Reverse the entire array

    Example: [1, 2, 3, 4, 5], d = 2
      Step 1: [2, 1, 3, 4, 5]  (reverse first 2)
      Step 2: [2, 1, 5, 4, 3]  (reverse last 3)
      Step 3: [3, 4, 5, 1, 2]  (reverse all)
    """
    if not arr or d == 0:
        return

    n = len(arr)
    d = d % n

    if d == 0:
        return

    def reverse(start: int, end: int) -> None:
        while start < end:
            arr[start], arr[end] = arr[end], arr[start]
            start += 1
            end -= 1

    reverse(0, d - 1)
    reverse(d, n - 1)
    reverse(0, n - 1)


# --- Main execution for HackerRank ---
if __name__ == "__main__":
    # Read input
    n, d = map(int, input().split())
    arr = list(map(int, input().split()))

    # Perform left rotation
    result = left_rotate(arr, d)

    # Print space-separated result
    print(" ".join(map(str, result)))
