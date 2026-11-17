import json, sys

def main(argv):
    path = "todos.json"
    todos = json.load(open(path)) if __import__("os").path.exists(path) else []
    if argv[:1] == ["add"]:
        todos.append({"text": " ".join(argv[1:]), "done": False})
    elif argv[:1] == ["list"]:
        for i, t in enumerate(todos, 1):
            print(f"{i}. [{'x' if t['done'] else ' '}] {t['text']}")
    json.dump(todos, open(path, "w"))

if __name__ == "__main__":
    main(sys.argv[1:])
