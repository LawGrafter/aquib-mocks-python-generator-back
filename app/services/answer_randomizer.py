import random
from typing import Optional

def generate_answer_key(n: int, seed: Optional[int] = None) -> str:
    """
    Generates a random answer key string of length n using 'a', 'b', 'c', 'd'.
    
    Rules:
    - Balanced distribution as much as possible
    - Avoid >2 same letters in a row
    - Avoid repeating patterns like "abcdabcd" (simplified check: no immediate repeat of len 4 sequence)
    """
    if n <= 0:
        return ""
        
    if seed is not None:
        random.seed(seed)
        
    options = ['a', 'b', 'c', 'd']
    
    # Calculate target counts for perfect balance
    base_count = n // 4
    remainder = n % 4
    
    # Create a pool of options ensuring balance
    pool = []
    for opt in options:
        pool.extend([opt] * base_count)
        
    # Distribute remainder randomly
    remainder_opts = random.sample(options, remainder)
    pool.extend(remainder_opts)
    
    # Shuffle initially
    random.shuffle(pool)
    
    result = []
    
    # We will build the result one by one, picking from the pool
    # If the picked option violates a rule, we try to swap with another option in the pool
    # Since we need to consume exactly the pool, we treat 'pool' as a list we consume.
    # But simple consumption might lead to a corner case at the end.
    # Approach:
    # 1. Shuffle pool.
    # 2. Iterate through positions 0 to n-1.
    # 3. Swap current candidate with a future one if it violates rules.
    
    # To make swapping easier, let's work with the pool list directly as the result array,
    # then fix violations.
    
    # Max attempts to fix to prevent infinite loops
    max_attempts = 1000
    attempts = 0
    
    def count_consecutive(arr, idx):
        if idx < 0: return 0
        count = 1
        char = arr[idx]
        for i in range(idx-1, -1, -1):
            if arr[i] == char:
                count += 1
            else:
                break
        return count

    # Try to construct a valid sequence
    while attempts < max_attempts:
        random.shuffle(pool)
        valid = True
        
        for i in range(len(pool)):
            # Rule 1: Avoid > 2 same letters in a row
            # Check i-1 and i-2
            if i >= 2 and pool[i] == pool[i-1] == pool[i-2]:
                # Try to swap with a future element that breaks this
                swapped = False
                for j in range(i + 1, len(pool)):
                    if pool[j] != pool[i]:
                        # Check if swapping introduces issue at j (simple check)
                        # We only care about fixing i right now. 
                        # Complex constraint satisfaction is hard, so we use restart/shuffle approach for global check
                        # But let's try a local swap first.
                        pool[i], pool[j] = pool[j], pool[i]
                        swapped = True
                        break
                if not swapped:
                    valid = False
                    break
        
        if valid:
            # Rule 2: Avoid repeating patterns like "abcdabcd"
            # We check for immediate repetition of patterns of length 2, 3, 4
            # e.g. abab, abcabc, abcdabcd
            result_str = "".join(pool)
            has_pattern = False
            for pat_len in range(2, 5): # 2, 3, 4
                if 2 * pat_len > len(result_str):
                    break
                for i in range(len(result_str) - 2 * pat_len + 1):
                    chunk1 = result_str[i : i+pat_len]
                    chunk2 = result_str[i+pat_len : i+2*pat_len]
                    if chunk1 == chunk2:
                        has_pattern = True
                        break
                if has_pattern:
                    break
            
            if not has_pattern:
                return "".join(pool)
        
        attempts += 1

    # If we fail to find perfect one, return the shuffled pool anyway
    # or a fallback random string (but that violates balance).
    # Return best effort.
    return "".join(pool)
