from core.third_party.evaluator_base import EvaluatorBase
from core.third_party.bird_eval.bird_accuracy import run_sqls_parallel, sort_results
import os


class AccraucyEvaluator(EvaluatorBase):
    
    def __init__(self, golds, preds, db_ids, db_dir, tables_json=None, **kwargs):
        super().__init__(golds, preds, db_ids, db_dir, tables_json)
        self.num_cpu = kwargs.get("num_cpu", 8)
        self.meta_time_out = kwargs.get("meta_time_out", 30)
    
    def evaluate(self):
        query_pairs = list(zip(self.preds, self.golds))
        db_places = [os.path.join(self.db_dir, db_id, f'{db_id}.sqlite') for db_id in self.db_ids]
        exec_result = run_sqls_parallel(
            sqls=query_pairs,
            db_places=db_places,
            num_cpus=self.num_cpu,
            meta_time_out=self.meta_time_out
        )
        exec_result = sort_results(exec_result)
        exec_result = [res['res'] for res in exec_result]
        # NOTE: Not support general EM evaluation now
        exact_result = [0 for _ in exec_result]
        return {
            "execution_accuracy": exec_result,
            "exact_match_accuracy": exact_result
        }