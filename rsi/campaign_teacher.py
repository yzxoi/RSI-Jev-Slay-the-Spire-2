"""E160 task-mediated campaign ownership; the program owns every battle action."""
from collections import Counter
import copy
import json
from pathlib import Path
import resource
import threading
import time
import uuid

from .battle_search import boundary, finish
from .continuation import FrozenProgram
from .engine import ROOT, Headless
from .resources import require_resource_interface
from .run_env import legal_choices, run_outcome
from .trace import Trace, digest
from scripts.evaluate_routing_e099 import committed_response


class Ownership:
    def __init__(self):
        self.active=False

    def observe(self,state):
        clear=False
        if self.active:
            end=boundary(state)
            if end:
                self.active=False;clear=end=='clear'
        if state['decision']=='combat_play':self.active=True
        return self.active,clear


def validate(packet,request):
    expected={'case','run_id','seq','state_hash','choice_id','campaign_plan','potion_reservations'}
    if set(packet)!=expected:raise ValueError('Unexpected campaign packet fields')
    for key in ('case','run_id','seq','state_hash'):
        if packet[key]!=request[key]:raise ValueError('Stale campaign packet: '+key)
    if not isinstance(packet['campaign_plan'],str) or not 1<=len(packet['campaign_plan'])<=1200:
        raise ValueError('Campaign plan must have 1..1200 characters')
    chosen=next((c for c in request['choices'] if c['id']==packet['choice_id']),None)
    if chosen is None:raise ValueError('Choice outside current menu')
    ids={p.get('id') for p in request['state'].get('player',{}).get('potions',[])}
    seen=set()
    for rule in packet['potion_reservations']:
        if set(rule)!={'potion_id','until','release_hp_fraction'}:raise ValueError('Invalid potion reservation')
        if rule['potion_id'] not in ids or rule['potion_id'] in seen:raise ValueError('Unknown/duplicate potion ID')
        if rule['until'] not in ('Elite','Boss'):raise ValueError('Unknown reservation boundary')
        if type(rule['release_hp_fraction']) not in (int,float) or not 0<=rule['release_hp_fraction']<=.5:
            raise ValueError('Invalid emergency HP threshold')
        seen.add(rule['potion_id'])
    return chosen


def permitted_state(state,reservations):
    p=state.get('player') or {};room=(state.get('context') or {}).get('room_type')
    rules={r['potion_id']:r for r in reservations};blocked=[]
    for potion in p.get('potions',[]):
        rule=rules.get(potion.get('id'))
        if rule is None:continue
        due=room=='Boss' or (rule['until']=='Elite' and room=='Elite')
        emergency=p.get('hp',0)/max(1,p.get('max_hp',1))<=rule['release_hp_fraction']
        if not due and not emergency:blocked.append(potion['index'])
    if not blocked:return state,blocked
    masked=copy.deepcopy(state)
    masked['player']['potions']=[p for p in masked['player']['potions'] if p['index'] not in blocked]
    return masked,blocked


class TeacherBudget:
    def __init__(self,limit):
        self.limit=limit;self.count=0;self.lock=threading.Lock();self.cpu_start=self.cpu()
    @staticmethod
    def cpu():
        return sum(r.ru_utime+r.ru_stime for r in
                   (resource.getrusage(resource.RUSAGE_SELF),resource.getrusage(resource.RUSAGE_CHILDREN)))
    def check_cpu(self):
        if self.cpu()-self.cpu_start>=1200:raise TimeoutError('Global CPU cap')
    def acquire(self):
        self.check_cpu()
        with self.lock:
            if self.count>=self.limit:raise TimeoutError('Global expert packet cap')
            self.count+=1


class CampaignTeacher:
    def __init__(self,trace,case,budget,pending,deadline):
        self.trace=trace;self.case=case;self.budget=budget;self.pending=pending;self.deadline=deadline
        self.count=0;self.wait=0.;self.input_chars=0;self.output_chars=0;self.last_fields={}
        self.plan='';self.reservations=[];self.packets=[]

    def choose(self,state,choices,previous,map_state):
        if self.count>=90:raise TimeoutError('Per-run expert packet cap')
        self.budget.acquire();self.count+=1
        seq=self.count;run_id=self.trace.directory.name
        snapshot=copy.deepcopy(state);unchanged={}
        for name in ('deck','relics'):
            value=snapshot.get('player',{}).get(name);h=digest(value)
            if self.last_fields.get(name)==h:
                snapshot['player'].pop(name,None);unchanged[name]=h
            self.last_fields[name]=h
        if self.last_fields.get('map')==digest(map_state):visible_map={'unchanged_hash':digest(map_state)}
        else:visible_map=map_state
        self.last_fields['map']=digest(map_state)
        path=ROOT/f'experiments/E160/teacher/{self.case}/{run_id}/{seq:03}.json'
        request=dict(case=self.case,run_id=run_id,seq=seq,state_hash=digest(state),state=snapshot,
            unchanged_player_fields=unchanged,choices=choices,previous=previous,map=visible_map,
            previous_plan=self.plan,potion_reservations=self.reservations,response_path=str(path.relative_to(ROOT)),
            contract='Choose one campaign action. No battle actions or tactical guidance. <=1200char campaign_plan. Reservations apply to all current copies of a potion ID until Elite/Boss, released at specified HP fraction<=.5; next packet replaces them. Battle executor is fixed legacy trigger/retaliation planner with early available potions. Preserve future resources/deck quality; objective full-run victory, not next-fight reward. Token/USD usage unknown.')
        self.trace.write('campaign_request',request)
        self.pending.mkdir(parents=True,exist_ok=True);target=self.pending/(self.case+'.json')
        tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n');tmp.replace(target)
        started=time.monotonic();response=None
        print(json.dumps(dict(waiting=self.case,seq=seq,phase=state['decision'],context=state.get('context'))),flush=True)
        try:
            while response is None:
                if time.monotonic()-started>600 or time.monotonic()>self.deadline:raise TimeoutError('Campaign reply deadline')
                response=committed_response(path)
                if response is None:time.sleep(.25)
        finally:self.wait+=time.monotonic()-started
        packet,commit=response;chosen=validate(packet,request)
        self.plan=packet['campaign_plan'];self.reservations=packet['potion_reservations']
        self.input_chars+=len(json.dumps(request,ensure_ascii=False));self.output_chars+=len(json.dumps(packet,ensure_ascii=False))
        binding=dict(seq=seq,path=str(path.relative_to(ROOT)),commit=commit,packet_hash=digest(packet),
            request_hash=digest(request),state_hash=request['state_hash'],decision=state['decision'],choice=chosen['action'])
        self.packets.append(binding);self.trace.write('campaign_response',dict(packet=packet,**binding))
        target.unlink()
        return chosen,binding


def episode(config,manifest,budget,pending,deadline):
    trace=Trace(ROOT/'artifacts/runs'/str(uuid.uuid4()),{**manifest,'scope':'E160_full_run','config':config})
    start=time.monotonic();engine=None;state={};previous=None;history={};trans=[];map_state=None;query_count=0
    owner=Ownership();program=FrozenProgram(None);teacher=None
    r={**config,'run_id':trace.directory.name,'status':'error','steps':0,'entries':[],
        'completed_battles':0,'completed_acts':0,'max_act':1,'scenes':Counter(),'owners':Counter(),
        'potion_blocks':0,'illegal_actions':0}
    if config['arm']=='astra_campaign':teacher=CampaignTeacher(trace,config['case'],budget,pending,deadline)
    def send(c):
        budget.check_cpu()
        wait=teacher.wait if teacher else 0
        left=min(120-(time.monotonic()-start-wait),deadline-time.monotonic())
        if left<=0:raise TimeoutError('Compute/global wall cap')
        engine.timeout=min(15,left);return engine.send(c)
    try:
        engine=Headless(trace.directory,timeout=15,resource_decisions=True)
        state=send(dict(cmd='start_run',**{k:config[k] for k in ('seed','character','ascension')}))
        require_resource_interface(state)
        last=None;repeated=0
        for step in range(2401):
            c=state.get('context') or {};p=state.get('player') or {};r['max_act']=max(r['max_act'],c.get('act',1))
            terminal=run_outcome(state)
            if terminal:
                r['status']=terminal
                r['completed_battles']+=int(terminal=='victory' and owner.active)
                break
            was_active=owner.active;active,clear=owner.observe(state);r['completed_battles']+=int(clear)
            if state['decision']=='map_select' and c.get('room_type')=='Map' and p.get('hp',0)>0:
                r['completed_acts']=max(r['completed_acts'],c.get('act',1)-1)
                map_state=send(dict(cmd='get_map'));query_count+=1
            if active and not was_active:
                r['entries'].append(dict(act=c.get('act'),floor=c.get('floor'),room_type=c.get('room_type'),
                    hp=p.get('hp'),max_hp=p.get('max_hp'),enemies=[e.get('name') for e in state.get('enemies',[])],
                    deck_hash=digest(p.get('deck')),potions=len(p.get('potions',[]))))
            if step==2400:r['status']='action_cap';break
            before=digest(state);repeated=repeated+1 if before==last else 0;last=before
            if repeated>=5:raise ValueError('Six repeated states')
            choices=legal_choices(state,history);extra={}
            if len(choices)==1:selected=choices[0];source='only_legal'
            elif active:
                masked,blocked=permitted_state(state,teacher.reservations if teacher else [])
                selected,extra=program.choose(masked,choices,previous);source='program_combat'
                extra['reserved_potion_indexes']=blocked;r['potion_blocks']+=bool(blocked)
                if selected['action']['action']=='use_potion' and selected['action']['args']['potion_index'] in blocked:
                    raise ValueError('Program violated potion reservation')
            elif teacher:
                selected,binding=teacher.choose(state,choices,previous,map_state);source='astra_campaign'
                extra['expert_binding']=binding
            else:selected,extra=program.choose(state,choices,previous);source='program_campaign'
            if selected['action'] not in [x['action'] for x in choices]:
                r['illegal_actions']+=1;raise ValueError('Illegal current action')
            trace.write('decision',dict(before=before,state=state,candidates=choices,chosen=selected,owner=source,
                                       combat_active=active,**extra))
            program.remember(state,selected)
            if state['decision']=='map_select':history['removed_here']=False
            if selected['action']['action']=='remove_card':history['removed_here']=True
            r['owners'][source]+=1;r['scenes'][state['decision']]+=1
            state=send(selected['action']);r['steps']+=1
            trans.append(dict(before=before,action=selected['action'],after=digest(state)));previous=selected
        if r['status']=='victory':r['completed_acts']=3
    except TimeoutError as exc:r.update(status='timeout',error=str(exc))
    except Exception as exc:r.update(status='error',error=f'{type(exc).__name__}: {exc}')
    r.update(final_context=state.get('context'),final_hp=state.get('player',{}).get('hp'),
        final_hash=digest(state),transition_hash=digest(trans),readonly_map_queries=query_count,
        expert_packets=teacher.count if teacher else 0,expert_wait_seconds=teacher.wait if teacher else 0,
        expert_input_chars=teacher.input_chars if teacher else 0,expert_output_chars=teacher.output_chars if teacher else 0,
        teacher_packets=teacher.packets if teacher else [],expert_tokens=None,expert_cost_usd=None,
        final_campaign_plan=teacher.plan if teacher else None)
    finish(trace,r,engine,start)
    r['compute_seconds']=r['seconds']-r['expert_wait_seconds']
    return r
