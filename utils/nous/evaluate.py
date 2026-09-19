#!/usr/bin/env python3
"""Bounded synthetic Nous evaluation. No generated code or tool is executed.

Scores are task checks, not a general intelligence benchmark. Tool responses
are deterministic fixtures. Store full responses for independent auditing.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path


TASKS = [
    ("intervals", "Merge overlapping or touching half-open intervals, sort by start, discard empty intervals. Input: [[8,12],[1,4],[4,6],[3,5],[15,15],[11,14],[-3,-1],[-1,1]]. Return only JSON {\"intervals\": [...]}.", {"intervals": [[-3,6],[8,14]]}),
    ("queue", "Simulate a capacity-3 FIFO queue. push on full evicts the oldest item; pop on empty returns null. Operations: push A, push B, pop, push C, push D, push E, pop, pop, pop, pop. Return only JSON with keys popped (all pop return values in order) and remaining (final queue).", {"popped": ["A","C","D","E",None],"remaining": []}),
    ("schedule", "One worker executes nonpreemptive jobs. Jobs are A(duration 4, no dependencies), B(3, none), C(2, after A), D(5, after B), E(1, after C and D). Minimize the SUM of completion times, not makespan. Return only JSON {\"order\":[...],\"sum_completion\":integer}. Ties choose lexicographically smallest order.", {"order": ["A","C","B","D","E"], "sum_completion": 48}),
    ("evidence", "A log records: seq 40 action walk target north; seq 41 receipt accepted=true; seq 42 observation position unchanged, battle_active=true. There is no later observation. Does this prove arrival north? Return only JSON {\"arrival_proven\":boolean,\"next\":string}. next must be one of inspect_battle, repeat_walk, claim_arrival. Use only observed evidence.", {"arrival_proven": False,"next":"inspect_battle"}),
]


def request(base, model, messages, tools, seed, thinking, temperature, max_tokens, recommended, gemma):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature, "seed": seed, "stream": False}
    if recommended:
        body.update(top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.5, repeat_penalty=1.0)
    if gemma:
        body.update(top_p=0.95, top_k=64)
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if thinking != "default":
        body["chat_template_kwargs"] = {"enable_thinking": thinking == "on"}
    start = time.monotonic()
    req = urllib.request.Request(base + "/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=100) as response:
        data = json.load(response)
    return data, time.monotonic() - start


def parse(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n",1)[1].rsplit("```",1)[0].strip()
    return json.loads(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--thinking", choices=["default","on","off"], default="default")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--long-only", action="store_true")
    parser.add_argument("--qwen-sampling", action="store_true",
                        help="Qwen/Ornith recommended general sampling; use temperature 1.0")
    parser.add_argument("--gemma-sampling", action="store_true",
                        help="Gemma recommended sampling; use temperature 1.0")
    args = parser.parse_args()
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Check the exact schedule answer independently before evaluating models.
    import itertools
    valid = []
    for order in itertools.permutations("ABCDE"):
        if any(order.index(a) > order.index(b) for a,b in [("A","C"),("B","D"),("C","E"),("D","E")]):
            continue
        elapsed = total = 0
        for job in order:
            elapsed += dict(A=4,B=3,C=2,D=5,E=1)[job]
            total += elapsed
        valid.append((total,order))
    score, order = min(valid)
    TASKS[2][2].update(order=list(order), sum_completion=score)
    if args.long_only:
        import random
        rng = random.Random(90471)
        records = [{"record":i,"owner":"team"+str(rng.randrange(9)),
                    "budget":rng.randrange(100),"nonce":str(rng.randrange(10000000,99999999))}
                   for i in range(350)]
        target = records[317]
        TASKS[:] = [("long_retrieval", "Read the records below. Return only JSON with owner, budget and nonce for record 317.\n" +
                     "\n".join(json.dumps(record,separators=(',',':')) for record in records),
                     {k:target[k] for k in ["owner","budget","nonce"]})]
    with dest.open("a") as out:
        for repeat in range(args.repeats):
            tasks = TASKS if args.long_only else TASKS + [("tool_roundtrip", "Read live_state using the read_state tool. Select the lowest-cost candidate whose legal flag is true and whose observation_seq equals the current seq. Return only JSON {\"id\":chosen_id,\"nonce\":the live nonce}. Never guess the state.", None)]
            for name, prompt, expected in tasks:
                row = {"model":args.model,"thinking":args.thinking,"temperature":args.temperature,"max_tokens":args.max_tokens,"qwen_sampling":args.qwen_sampling,"gemma_sampling":args.gemma_sampling,"repeat":repeat,"task":name,"expected":expected,"calls":[],"passed":False}
                messages = [{"role":"system","content":"Follow the requested output contract. Use tools when needed. Keep reasoning concise."}, {"role":"user","content":prompt}]
                tool = [{"type":"function","function":{"name":"read_state","description":"Read current live_state and candidate list.","parameters":{"type":"object","properties":{},"additionalProperties":False}}}]
                task_start = time.monotonic()
                try:
                    response, elapsed = request(args.base,args.model,messages,tool if expected is None else None,73+repeat,args.thinking,args.temperature,args.max_tokens,args.qwen_sampling,args.gemma_sampling)
                    row["calls"].append({"seconds":elapsed,"response":response})
                    msg = response["choices"][0]["message"]
                    if expected is None:
                        calls = msg.get("tool_calls",[])
                        if len(calls) != 1 or calls[0]["function"]["name"] != "read_state" or json.loads(calls[0]["function"]["arguments"]) != {}:
                            raise ValueError("Expected one real read_state({}) tool call")
                        nonce = "cobalt-731" if repeat == 0 else "jasper-284"
                        state = {"seq":52,"nonce":nonce,"candidates":[{"id":"stale","cost":0,"legal":True,"observation_seq":51},{"id":"blocked","cost":1,"legal":False,"observation_seq":52},{"id":"safe","cost":4,"legal":True,"observation_seq":52},{"id":"expensive","cost":8,"legal":True,"observation_seq":52}]}
                        messages += [msg,{"role":"tool","tool_call_id":calls[0]["id"],"content":json.dumps(state)}]
                        response, elapsed = request(args.base,args.model,messages,tool,73+repeat,args.thinking,args.temperature,args.max_tokens,args.qwen_sampling,args.gemma_sampling)
                        row["calls"].append({"seconds":elapsed,"response":response})
                        msg = response["choices"][0]["message"]
                        expected = row["expected"] = {"id":"safe","nonce":nonce}
                    row["actual"] = parse(msg.get("content"))
                    row["passed"] = row["actual"] == expected
                except Exception as error:
                    row["error"] = str(error)
                row["seconds"] = time.monotonic() - task_start
                out.write(json.dumps(row)+"\n")
                out.flush()
                print(json.dumps({k:row[k] for k in ["model","repeat","task","passed","seconds"]}),flush=True)


if __name__ == "__main__":
    main()
