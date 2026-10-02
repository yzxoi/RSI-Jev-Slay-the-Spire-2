"""Recovery invariants and exact synthetic optimizer continuation, not win evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch

from rsi.checkpoints import file_hash
from rsi.ppo import ActorCritic, STATE_DIM, ACTION_DIM, HP, padded, update
from rsi.ppo_resume import retry_eligible, shuffle_rng, training_episode


class ResumeTests(unittest.TestCase):
    def failure(self, directory):
        p=Path(directory); cp={'path':str(p/'save.json')}
        (p/'decisions.jsonl').write_text('{}\n')
        (p/'engine.stderr.log').write_text('loading\n')
        (p/'wire.jsonl').write_text('\n'.join(json.dumps(x) for x in [
            {'kind':'state','data':{'type':'ready'}},
            {'kind':'command','data':{'cmd':'load_save','path':cp['path']}}])+'\n')
        r=dict(status='timeout',steps=0,entry_verified=False,decisions={},restore_mode='research_checkpoint',
               error='Headless response deadline exceeded',seconds=10.,replay_seconds=0.,run_id='failed',
               trace_path=str(p/'decisions.jsonl'),trace_sha256=file_hash(p/'decisions.jsonl'),
               **{name+'_sha256':file_hash(p/name) for name in ('wire.jsonl','engine.stderr.log')})
        return r,cp

    def test_only_audited_predecision_load_is_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            r,cp=self.failure(directory)
            self.assertTrue(retry_eligible(r,[],cp))
            for changed in ({'status':'defeat','reward':-1.},{'entry_verified':True},{'steps':1},
                            {'decisions':{'combat_play':1}},{'status':'error'}, {'error':'Entry mismatch'}):
                self.assertFalse(retry_eligible({**r,**changed},[],cp))
            self.assertFalse(retry_eligible(r,[{'value':0.}],cp))
            Path(directory,'wire.jsonl').write_text('edited')
            self.assertFalse(retry_eligible(r,[],cp))

    def test_exactly_one_retry_keeps_rng_and_shared_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            first,cp=self.failure(directory)
            second={**first,'run_id':'second','seconds':5.}
            with patch('rsi.ppo_resume.episode',side_effect=[(first,[]),(second,[])]) as run, \
                 patch('rsi.ppo_resume.time.monotonic',side_effect=[0.,10.,15.]):
                result,_=training_episode({}, {}, 'test',seconds=30,checkpoint=cp,sample_seed=17)
            self.assertEqual(run.call_count,2)
            self.assertEqual(run.call_args.kwargs['seconds'],20.)
            self.assertEqual(run.call_args.kwargs['sample_seed'],17)
            self.assertEqual(result['seconds'],15.)
            self.assertEqual(result['reset_retry_attempts'][0]['run_id'],'failed')
            self.assertEqual(result['status'],'timeout')

    def test_expired_budget_never_starts_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            first,cp=self.failure(directory)
            with patch('rsi.ppo_resume.episode',return_value=(first,[])) as run, \
                 patch('rsi.ppo_resume.time.monotonic',side_effect=[0.,30.]):
                training_episode({}, {}, 'test',seconds=30,checkpoint=cp)
            self.assertEqual(run.call_count,1)

    def test_shuffle_consumes_kl_stop_epoch_even_at_boundary(self):
        rng=np.random.default_rng(17)
        for _ in range(2):rng.permutation(384)
        reconstructed=shuffle_rng(17,[dict(update=1,optimization=dict(transitions=384,minibatches=3,kl_early_stop=True))])
        self.assertEqual(rng.bit_generator.state,reconstructed.bit_generator.state)

    def test_checkpoint_resume_matches_uninterrupted_optimizer_exactly(self):
        torch.set_num_threads(1); torch.manual_seed(17)
        model=ActorCritic(); opt=torch.optim.Adam(model.parameters(),lr=HP['lr'],eps=1e-5)
        rng=np.random.default_rng(17)
        s=np.ones(STATE_DIM,np.float32);a=np.zeros((2,ACTION_DIM),np.float32);a[0,0]=1;a[1,0]=-1
        def batch(m):
            with torch.no_grad():dist,values=m(*padded([(s,a)]*192))
            return [([dict(encoded=(s,a),index=i%2,logprob=dist.logits[i,i%2].item(),value=values[i].item())],
                     1. if i%2==0 else -1.) for i in range(192)]
        first=update(model,opt,batch(model),rng)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'checkpoint.pt'
            torch.save({'model':model.state_dict(),'optimizer':opt.state_dict()},path)
            saved=torch.load(path,weights_only=True)
        restored=ActorCritic();restored.load_state_dict(saved['model'])
        restored_opt=torch.optim.Adam(restored.parameters(),lr=HP['lr'],eps=1e-5)
        restored_opt.load_state_dict(saved['optimizer'])
        restored_rng=shuffle_rng(17,[dict(update=1,optimization=first)])
        self.assertEqual(rng.bit_generator.state,restored_rng.bit_generator.state)
        a_metrics=update(model,opt,batch(model),rng)
        b_metrics=update(restored,restored_opt,batch(restored),restored_rng)
        self.assertEqual(a_metrics,b_metrics)
        for a_value,b_value in zip(model.parameters(),restored.parameters()):
            torch.testing.assert_close(a_value,b_value,rtol=0,atol=0)
        def equal(a,b):
            if isinstance(a,torch.Tensor):torch.testing.assert_close(a,b,rtol=0,atol=0)
            elif isinstance(a,dict):
                self.assertEqual(a.keys(),b.keys())
                for key in a:equal(a[key],b[key])
            elif isinstance(a,list):
                self.assertEqual(len(a),len(b))
                for aa,bb in zip(a,b):equal(aa,bb)
            else:self.assertEqual(a,b)
        equal(opt.state_dict(),restored_opt.state_dict())
        self.assertEqual(rng.bit_generator.state,restored_rng.bit_generator.state)


if __name__=='__main__':unittest.main()
