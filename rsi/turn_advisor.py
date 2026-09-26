"""Once-per-player-turn task-mediated advice, with Jev retaining action decisions."""
import copy
import json
import time
from .engine import ROOT
from .policy import model_state
from .trace import digest
from scripts.evaluate_routing_e099 import committed_response


def validate_packet(packet, request):
    for key in ('run_id','case','round','state_hash'):
        if packet.get(key)!=request[key]:raise ValueError('Stale turn advice: '+key)
    if set(packet) != {'run_id','case','round','state_hash','goal','guidance'}:
        raise ValueError('Turn advice accepts only advisory goal/guidance, no action IDs')
    if not all(isinstance(packet[k],str) and packet[k].strip() for k in ('goal','guidance')):
        raise ValueError('Missing advisory text')
    if len(packet['goal'])+len(packet['guidance'])>1200:raise ValueError('Advice exceeds 1200 characters')


class TurnAdvisor:
    def __init__(self,case,trace,experiment,room):
        self.case=case;self.trace=trace;self.experiment=experiment;self.room=room;self.round=None
        self.plan=None;self.commit=None;self.requests=0;self.input_chars=0;self.output_chars=0;self.seconds=0
        self.last_state=None

    def update(self,state,recent,room_plan):
        if state.get('context')!=self.room:raise ValueError('Turn plan left room')
        if state.get('decision')!='combat_play':return self.plan
        if state['round']==self.round:return self.plan
        if self.requests>=30:raise RuntimeError('Turn advisor budget exhausted')
        snapshot=model_state(state)
        if self.requests:
            snapshot=copy.deepcopy(snapshot)
            snapshot['player'].pop('deck',None);snapshot['player'].pop('relics',None)
        request={'run_id':self.trace.directory.name,'case':self.case,'round':state['round'],'state_hash':digest(state),
                 'state':snapshot,'recent_actions':recent[-6:],
                 'room_plan':room_plan if not self.requests else {'reference':'unchanged E099 entry plan'},
                 'contract':'Advisory only, <=1200 chars goal+guidance. Jev selects all card/target/selection actions. Expires on next player turn. Program handles contracted potions and certified immediate lethal. No mid-turn rescue.'}
        self.trace.write('turn_advice_request',request)
        tmp=self.trace.directory/'turn_request.tmp';tmp.write_text(json.dumps(request,indent=2)+'\n');tmp.replace(self.trace.directory/'turn_request.json')
        path=ROOT/f'experiments/{self.experiment}/teacher'/self.trace.directory.name/f"{state['round']:03}.json"
        print(json.dumps({'waiting_turn':self.case,'round':state['round'],'run_id':self.trace.directory.name}),flush=True)
        started=time.monotonic();response=None
        while response is None:
            if time.monotonic()-started>1800:raise TimeoutError('Turn advisor response deadline')
            response=committed_response(path)
            if response is None:time.sleep(.25)
        packet,commit=response;validate_packet(packet,request)
        self.seconds+=time.monotonic()-started;self.requests+=1
        self.input_chars+=len(json.dumps(request,ensure_ascii=False));self.output_chars+=len(json.dumps(packet,ensure_ascii=False))
        self.round=state['round'];self.commit=commit
        self.plan={'round':self.round,'goal':packet['goal'],'guidance':packet['guidance'],
                   'expiry':'next player turn or room end; adapt locally to draw/selection within this turn'}
        self.trace.write('turn_advice_response',{'packet':packet,'commit':commit})
        return self.plan
