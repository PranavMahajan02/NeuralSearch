from clip_utils import clip_search

results = clip_search("medical bill")

print("\nTop Match:")
print(results[0][1]["file"])
print(results[0][0])