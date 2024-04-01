

class EvaluatorBase:
    
    def __init__(self, golds, preds, db_ids, db_dir, tables_json):
        self.golds = golds
        self.preds = preds
        self.db_ids = db_ids
        self.db_dir = db_dir
        self.tables_json = tables_json
    
    def evaluate(self):
        """Evaluate
        
        Return dict(metric_name=list(), ...)
        """
        pass
