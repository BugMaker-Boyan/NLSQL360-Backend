from core.third_party.evaluator_base import EvaluatorBase
from core.third_party.bird_eval.bird_ves import run_sqls_parallel, sort_results
import math
import os


class VesEvaluator(EvaluatorBase):
    
    """The general VES metric evaluator
    Note: For Spider evaluation, we specific the pre-eval execution accuracy list into VES calculate
    """
    
    def __init__(self, golds, preds, db_ids, db_dir, tables_json=None, **kwargs):
        super().__init__(golds, preds, db_ids, db_dir, tables_json)
        self.num_cpu = kwargs.get("num_cpu", 8)
        self.meta_time_out = kwargs.get("meta_time_out", 5)
        self.iterate_num = kwargs.get("iterate_num", 100)
    
    def evaluate(self, **kwargs):
        exec_acc_list = kwargs.get("exec_acc_list", None)
        query_pairs = list(zip(self.preds, self.golds))
        db_places = [os.path.join(self.db_dir, db_id, f'{db_id}.sqlite') for db_id in self.db_ids]
        ves_result = run_sqls_parallel(
            sqls=query_pairs,
            db_places=db_places,
            num_cpus=self.num_cpu,
            meta_time_out=self.meta_time_out,
            exec_acc_list=exec_acc_list
        )
        ves_result = sort_results(ves_result)
        
        ves_result = [math.sqrt(res['time_ratio']) * 100 for res in ves_result]
        return {
            "valid_efficiency_score": ves_result
        }
