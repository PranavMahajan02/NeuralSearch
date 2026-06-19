import os

while True:

    print("\n======================")
    print("1. Document Search")
    print("2. Image Search")
    print("3. Exit")
    print("======================")

    choice = input("\nChoose mode: ").strip()

    if choice == "1":

        os.system(
            "python document_search_v2.py"
        )

    elif choice == "2":

        os.system(
            "python image_search.py"
        )

    elif choice == "3":

        break

    else:

        print("Invalid option")