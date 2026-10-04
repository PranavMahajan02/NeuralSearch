from video_search import search_video

results = search_video(
    "monkey vidssave.com hanuman panchatantra _ infobells  videos 720p.mp4"
)

print(results)

if results:
    print("\nFirst Result:\n")
    print(results[0])