SUCCESS_COMPLETE = {
    "status": "success"
}

FAIL_COMPLETE = {
    "status": "fail"
}

DEFAULT_DATASET_ATTR_NAMES = [
    "nlq",
    "gold",
    "db_id"
]

DEFAULT_METRICS = [
    {
        "name": "execution_accuracy",
        "description": "The execution accuracy (EX)",
        "rule_definition": "execution_accuracy"
    },
    {
        "name": "exact_match_accuracy",
        "description": "The exact match accuracy (EM)",
        "rule_definition": "exact_match_accuracy"
    },
    {
        "name": "valid_efficiency_score",
        "description": "The valid efficiency score (VES)",
        "rule_definition": "valid_efficiency_score"
    }
]

EVAL_JSON_KEYS = [
    "id",
    "prediction"
]