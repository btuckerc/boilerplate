#!/usr/bin/env python3
"""Grade the small, reviewed two-function fixture; not a general code sandbox."""
import ast
import copy
import json
import random
import sys
from pathlib import Path


def grade(code):
    tree = ast.parse(code)
    allowed_methods = {"get", "append", "extend", "sort", "copy", "items", "keys", "values"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.While)):
            raise ValueError("Fixture needs only bounded pure functions")
        if isinstance(node, ast.Name) and node.id.startswith("_"):
            raise ValueError("Private identifiers excluded")
        if isinstance(node, ast.Attribute) and node.attr not in allowed_methods:
            raise ValueError("Unexpected attribute: " + node.attr)
    scope = {"__builtins__": {name: getattr(__import__("builtins"), name) for name in
             ["min","max","sorted","len","list","tuple","dict","set","range","enumerate","zip","any","all","bool","int","str","float","isinstance"]}}
    exec(compile(tree, "fixture", "exec"), scope)
    rng = random.Random(20260919)
    failures = []
    count = 0
    windows_cases = [[], [[1,2],[2,3]], [[8,12],[11,14]], [[4,1],[2,2]], [[1,9],[3,4],[1,9]]]
    windows_cases += [[[rng.randrange(-10,11),rng.randrange(-10,11)] for _ in range(rng.randrange(16))] for _ in range(200)]
    for windows in windows_cases:
        # Independent oracle: union of integer unit segments, then connected components.
        units = sorted({i for start,end in windows for i in range(start,end)})
        expected = []
        for value in units:
            if expected and expected[-1][1] == value:
                expected[-1][1] += 1
            else:
                expected.append([value,value+1])
        original = copy.deepcopy(windows)
        actual = scope["merge_windows"](windows)
        count += 1
        if actual != expected or windows != original:
            failures.append({"function":"merge_windows","input":original,"expected":expected,"actual":actual,"mutated":windows!=original})
    for _ in range(205):
        seq = rng.randrange(3)
        budget = rng.randrange(9)
        candidates = [{"id":chr(97+i),"cost":rng.randrange(10),"legal":bool(rng.randrange(2)),"observation_seq":rng.randrange(3)} for i in range(rng.randrange(12))]
        rng.shuffle(candidates)
        admitted = sorted((c["cost"],c["id"]) for c in candidates if c["legal"] and c["observation_seq"]==seq and c["cost"]<=budget)
        expected = admitted[0][1] if admitted else None
        original = copy.deepcopy(candidates)
        actual = scope["choose_action"](candidates,seq,budget)
        count += 1
        if actual != expected or candidates != original:
            failures.append({"function":"choose_action","input":original,"expected":expected,"actual":actual,"mutated":candidates!=original})
    return {"checks":count,"passed":count-len(failures),"failures":failures[:10]}


if __name__ == "__main__":
    path = Path(sys.argv[1])
    result = json.loads(path.read_text())
    try:
        result["grade"] = grade(result["code"])
    except Exception as error:
        result["grade"] = {"error":str(error)}
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(path.name, json.dumps(result["grade"]))
