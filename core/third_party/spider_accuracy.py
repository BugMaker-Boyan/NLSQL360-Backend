from core.third_party.evaluator_base import EvaluatorBase
from core.third_party.test_suite_sql_eval.evaluation import evaluate, build_foreign_key_map_from_json


class SpiderAccraucyEvaluator(EvaluatorBase):
    
    def __init__(self, golds, preds, db_ids, db_dir, tables_json=None, **kwargs):
        super().__init__(golds, preds, db_ids, db_dir, tables_json)
    
    async def evaluate(self):
        golds = [f"{gold}\t{db_id}" for gold, db_id in zip(self.golds, self.db_ids)]
        entries = await evaluate(
            golds=golds,
            preds=self.preds,
            db_dir=self.db_dir,
            etype="all" if self.tables_json else "exec",
            kmaps=build_foreign_key_map_from_json(self.tables_json) if self.tables_json else None,
            plug_value=False,
            keep_distinct=False,
            progress_bar_for_each_datapoint=False
        )
        return {
            "execution_accuracy": [entry["exec"] for entry in entries],
            "exact_match_accuracy": [entry["exact"] for entry in entries] if self.tables_json else [0 for _ in entries]
        }
