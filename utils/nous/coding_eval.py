#!/usr/bin/env python3
"""Run one bounded OpenCode read/edit task in a disposable fixture.

Usage: coding_eval.py provider/model label [thinking-off|community]
Review generated code before grade_code.py. No shell tools are allowed.
"""
import json,os,pathlib,subprocess,sys,tempfile,time
model=sys.argv[1]; label=sys.argv[2]
root=pathlib.Path(tempfile.mkdtemp(prefix='nous-code-'+label+'-'))
(root/'worker.py').write_text('''def merge_windows(windows):
    return sorted(windows)


def choose_action(candidates, seq, budget):
    return min(candidates, key=lambda c: c["cost"])["id"]
''')
(root/'AGENTS.md').write_text('Work only in this temporary fixture. Read before editing. Change worker.py only. Do not run shell commands.\n')
config={'permission':{'*':'deny','read':'allow','edit':'allow','glob':'allow','grep':'allow','list':'allow'},'provider':{'nous':{'models':{n:{'name':n,'limit':{'context':16384,'output':4096}} for n in ['gemma-4-12B-it-Q4_0','Ornith-1.5-9B-Q5_K_M','Qwen3.5-4B-Q5_K_M']}}}}
if len(sys.argv)>3 and sys.argv[3]=='thinking-off':
 provider, model_id=model.split('/',1)
 config.setdefault('provider',{}).setdefault(provider,{}).setdefault('models',{}).setdefault(model_id,{}).update(options={'chat_template_kwargs':{'enable_thinking':False},'temperature':0.7})
if len(sys.argv)>3 and sys.argv[3]=='community':
 provider, model_id=model.split('/',1)
 config.setdefault('provider',{}).setdefault(provider,{}).setdefault('models',{}).setdefault(model_id,{}).update(name=model_id, reasoning=True, tool_call=True, limit={'context':16384,'output':4096})
 config['agent']={'build':{'temperature':0.6,'top_p':0.95},'plan':{'temperature':0.6,'top_p':0.95}}
 config['compaction']={'auto':True,'prune':True,'reserved':4096}
env=os.environ.copy()
# Freeze the original screening baseline; later live config changes must not
# silently turn the default profile into the community profile.
env['XDG_CONFIG_HOME']=str(root/'config-home')
env['OPENCODE_CONFIG']=str(pathlib.Path(__file__).resolve().parent/'opencode-screening-baseline.json')
env['OPENCODE_CONFIG_CONTENT']=json.dumps(config)
prompt='''Read worker.py and fix both functions. merge_windows(windows): input list of integer [start,end] half-open intervals; discard empty or reversed intervals; merge overlaps AND touching endpoints; output sorted list of [start,end] lists. Do not mutate input. choose_action(candidates, seq, budget): each candidate has id (string), cost (nonnegative integer), legal (bool), observation_seq (int). Admit only legal=true with observation_seq==seq and cost<=budget. Return id of minimum-cost admitted candidate, break cost ties by lexicographically smallest id. Return None if none qualify, including empty input. Do not mutate input. Use file tools to edit worker.py. No shell commands or other files. Keep your final response brief.'''
start=time.monotonic()
try:
 p=subprocess.run([os.path.expanduser('~/.local/bin/opencode-baseline'),'run','--pure','--dir',str(root),'--format','json','--title','Nous coding evaluation '+label,'-m',model,prompt],env=env,capture_output=True,text=True,timeout=150)
 result={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
except subprocess.TimeoutExpired as e:
 result={'timeout':True,'stdout':(e.stdout or b'').decode() if isinstance(e.stdout,bytes) else e.stdout,'stderr':str(e.stderr)}
result.update(profile=sys.argv[3] if len(sys.argv)>3 else 'default',config_overlay=config,model=model,seconds=time.monotonic()-start,fixture=str(root),code=(root/'worker.py').read_text())
out=(pathlib.Path(__file__).resolve().parent/'results')/(label+'-coding.json');out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['stdout','stderr']},indent=2))
