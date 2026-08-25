nums = [1, 2, 3, 4, 5,9,6, 7, 8, 10]
target = 9
def two_sum(nums, target):
    hashmap = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in hashmap:
            return [hashmap[diff], i]
        hashmap[num] = i
result = two_sum(nums, target)
print(result)