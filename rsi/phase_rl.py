"""Opt-in phase observations and train-only off-policy weighted regression."""
import math
import numpy as np
import torch

from .ppo import ActorCritic, STATE_DIM, ACTION_DIM, OMIT, encode, hashed, padded

ENCODER='e140-phase-context-v1'
STATE_SIZE,ACTION_SIZE=STATE_DIM+264,ACTION_DIM+128


def semantics(value):
    if isinstance(value,dict):
        return {('effect_text' if k=='description' else 'upgrade_effect' if k=='after_upgrade' else k):semantics(v)
                for k,v in value.items() if k not in OMIT or k in ('description','after_upgrade')}
    if isinstance(value,list):return [semantics(v) for v in value]
    return value


def phase_encode(state,choices,previous=None,**kwargs):
    s,a=encode(state,choices,previous,**kwargs)
    c=state.get('context') or {};p=state.get('player') or {};d=state.get('decision')
    numeric=np.asarray([c.get('act',0)/3,c.get('floor',0)/17,p.get('gold',0)/300,
        d=='rest_site',d=='shop',d=='card_reward',state.get('can_skip',False),
        (state.get('card_removal_cost') or 0)/200],dtype=np.float32)
    context={k:state[k] for k in ('context','options','bundles','cards','selection_type','prompt','can_skip') if k in state}
    context['menu']=[c.get('details') for c in choices]
    s=np.concatenate((s,numeric,hashed(semantics(context),256)))
    extras=[]
    for choice in choices:
        args=choice['action']['args'];card=next((x for x in state.get('hand',[]) if x['index']==args.get('card_index')),None)
        extra=dict(details=choice.get('details'),card=card,action=choice['action']['action'])
        extras.append(hashed(semantics(extra),128))
    return s,np.concatenate((a,np.stack(extras)),axis=1)


def extend_model(source):
    model=ActorCritic(state_width=source.config['state_width'],action_width=source.config['action_width'],
                      state_dim=STATE_SIZE,action_dim=ACTION_SIZE)
    old=source.state_dict();new=model.state_dict()
    for key in new:
        if key in ('state.0.weight','action.0.weight'):
            new[key].zero_();new[key][:,:old[key].shape[1]]=old[key]
        else:new[key].copy_(old[key])
    model.load_state_dict(new)
    return model


def controller(model, sample_seed=None, trajectory=None):
    if trajectory is not None and sample_seed is None:
        raise ValueError('On-policy collection requires a stochastic behavior policy')
    rng = np.random.default_rng(sample_seed)
    def choose(state,choices,previous):
        encoded=phase_encode(state,choices,previous,max_actions=4096)
        with torch.inference_mode():
            dist,v=model(*padded([encoded]));probs=dist.probs[0].numpy()
            if sample_seed is None:index=int(np.argmax(probs))
            else:
                probs=probs.astype(np.float64);probs/=probs.sum()
                index=int(rng.choice(len(choices),p=probs))
        extra=dict(probabilities=probs.tolist(),value=float(v[0]),old_logprob=float(dist.logits[0,index]))
        if sample_seed is not None:
            extra.update(sample_seed=sample_seed,sampling_logprob=float(np.log(probs[index])))
        if trajectory is not None:
            trajectory.append(dict(encoded=encoded,index=index,phase=state['decision'],
                                   value=extra['value'],logprob=extra['sampling_logprob']))
        return choices[index],extra
    return choose


def bc_step(model,optimizer,rows,coefficient=1.):
    dist,_=model(*padded([r['encoded'] for r in rows]));index=torch.tensor([r['index'] for r in rows])
    loss=-coefficient*dist.log_prob(index).mean()
    optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),.5,error_if_nonfinite=True);optimizer.step()
    return float(loss.detach())


def awr_weights(returns,values,beta=.5,cap=20.):
    weights=((returns-values.detach())/beta).clamp(max=math.log(cap)).exp()
    return weights/weights.mean().clamp_min(1e-8)


def offline_fit(model,optimizer,rows,macros,rng):
    """Monte Carlo critic followed by AWR-style actor and explicit macro BC."""
    metrics=[]
    for phase in ('critic','actor'):
        for epoch in range(4):
            losses=[]
            indices=rng.permutation(len(rows))
            for start in range(0,len(rows),128):
                batch=[rows[i] for i in indices[start:start+128]]
                dist,value=model(*padded([r['encoded'] for r in batch]))
                targets=torch.tensor([r['return'] for r in batch],dtype=torch.float32)
                if phase=='critic':loss=.5*(value-targets).square().mean()
                else:
                    ix=torch.tensor([r['index'] for r in batch])
                    weight=awr_weights(targets,value)
                    loss=-(weight*dist.log_prob(ix)).mean()
                    aux=[macros[int(i)] for i in rng.integers(len(macros),size=64)]
                    aux_dist,_=model(*padded([r['encoded'] for r in aux]))
                    loss-=.25*aux_dist.log_prob(torch.tensor([r['index'] for r in aux])).mean()
                if not torch.isfinite(loss):raise ValueError('Nonfinite off-policy loss')
                optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),.5,error_if_nonfinite=True);optimizer.step()
                losses.append(float(loss.detach()))
            metrics.append(dict(phase=phase,epoch=epoch,loss=float(np.mean(losses))))
    return metrics
