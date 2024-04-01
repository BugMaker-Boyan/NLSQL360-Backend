from fastapi import APIRouter, UploadFile, status, HTTPException
from pydantic import BaseModel
from app.service.auth.auth_token import get_password_hash, UserObject, UserInDBObject, Depends, get_current_user
from typing import List
from app.model.models import Dataset, Sample, DatasetAttr, User, DatasetMetric, Evaluation
from tortoise.functions import Count
from tortoise.expressions import Q, F
from tortoise.query_utils import Prefetch
from tortoise.transactions import in_transaction
from pathlib import Path
import zipfile
import asyncio
import shutil
import app.global_enums as global_enums
import aiofiles
import os
import json
from core.third_party.general_accuracy import AccraucyEvaluator
from core.third_party.spider_accuracy import SpiderAccraucyEvaluator
from core.third_party.ves import VesEvaluator
from collections import defaultdict
import pandas as pd


evaluation_router = APIRouter()


@evaluation_router.get("/")
async def get_available_evaluations_info(current_user: UserObject = Depends(get_current_user)):
    evaluations = await Evaluation.filter(user__username=current_user.username)
    if evaluations:
        evaluations = await evaluations.annotate(dataset_name=F("dataset__name")).values("dataset_name", "evaluation_identifier")
    return evaluations


@evaluation_router.get("/{dataset_name}")
async def get_evaluation_detail_data(dataset_name: str,
                                     evaluation_identifier: str,
                                     current_user: UserObject = Depends(get_current_user)):
    
    evaluations = await Evaluation.filter(
        user__username=current_user.username, 
        evaluation_identifier=evaluation_identifier, 
        dataset__name=dataset_name
    ).prefetch_related('sample')
    if evaluations:
        all_records = [
            {
                "gold": eval_record.sample.attributes["gold"],
                "prediction": eval_record.prediction,
                "metric_values": eval_record.metric_values
            } for eval_record in evaluations]
    else:
        all_records = []
    return all_records


@evaluation_router.get("/filter/{dataset_name}")
async def get_evaluation_after_filter(dataset_name: str,
                                      evaluation_identifier: str,
                                      filter_str: str,
                                      current_user: UserObject = Depends(get_current_user)):
     
    evaluations = await Evaluation.filter(
        user__username=current_user.username, 
        evaluation_identifier=evaluation_identifier, 
        dataset__name=dataset_name
    ).prefetch_related("sample")

    records_data = []
    for eval_record in evaluations:
        record = eval_record.metric_values.copy()
        record.update(eval_record.sample.attributes)
        records_data.append(record)

    filter = [sub_filter.strip() for sub_filter in filter_str.split("|")]
    
    columns_to_aggregate = {key: "mean" for key in eval_record.metric_values.keys()}
    
    df = pd.DataFrame(records_data)
    
    computed_df = df.groupby(filter).agg(columns_to_aggregate).reset_index().sort_values(by=filter)
    json_result = computed_df.to_dict(orient='records')
    
    return json_result


@evaluation_router.post("/{dataset_name}")
async def run_evaluation(dataset_name: str,
                         evaluation_identifier: str,
                         eval_json_file: UploadFile,
                         special_spider_accuracy: bool = False,
                         current_user: UserObject = Depends(get_current_user)):
    evaluation = await Evaluation.filter(user__username=current_user.username, 
                                         dataset__name=dataset_name,
                                         evaluation_identifier=evaluation_identifier)
    if evaluation:
        raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=f"Evaluation with name {evaluation_identifier} on dataset {dataset_name} already exists"
            )
    try:
        dataset = await Dataset.get(name=dataset_name, user__username=current_user.username).prefetch_related(
            "metrics", "attrs", "samples"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {e}"
        ) from e
    
    content = await eval_json_file.read()
    eval_json = json.loads(content)
    
    # check eval json - keys:
    for eval_sample in eval_json:
        if set(eval_sample.keys()) != set(global_enums.EVAL_JSON_KEYS):
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=f"Evaluation file format error, each object must only have keys [id, prediction]"
            )
    # check eval json - sample ids
    dataset_sample_ids = sorted([sample.id for sample in dataset.samples])
    eval_json_ids = sorted([sample["id"] for sample in eval_json])
    if dataset_sample_ids != eval_json_ids:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f"Evaluation file with error sample ids, please check"
        )
    
    
    # NOTE: Sort both, to ensure (gold, pred) pair consistency
    sorted_gold_samples = sorted(dataset.samples, key=lambda item: item.id)
    sorted_eval_samples = sorted(eval_json, key=lambda item: item["id"])
    if dataset.tables_json_filename:
        tables_json_path = Path(f"user_data/{current_user.username}/{dataset_name}/{dataset.tables_json_filename}")
        async with aiofiles.open(tables_json_path, "r", encoding="utf-8") as fp:
            content = await fp.read()
            tables_json = json.loads(content)
    else:
        tables_json = None
    db_dir = Path(f"user_data/{current_user.username}/{dataset_name}/{dataset.db_dirname}").as_posix()
    
    eval_results = dict()
    
    # evaluation basic metrics:
    # EX and EM
    if special_spider_accuracy:
        accuracy_evaluator = SpiderAccraucyEvaluator(
            golds=[sample.attributes["gold"] for sample in sorted_gold_samples],
            preds=[sample["prediction"] for sample in sorted_eval_samples],
            db_ids=[sample.attributes["db_id"] for sample in sorted_gold_samples],
            db_dir=db_dir,
            tables_json=tables_json
        )
    else:
        accuracy_evaluator = AccraucyEvaluator(
            golds=[sample.attributes["gold"] for sample in sorted_gold_samples],
            preds=[sample["prediction"] for sample in sorted_eval_samples],
            db_ids=[sample.attributes["db_id"] for sample in sorted_gold_samples],
            db_dir=db_dir,
            tables_json=tables_json
        )
    res = await accuracy_evaluator.evaluate()
    eval_results.update(res)
    
    # VES
    ves_evaluator = VesEvaluator(
        golds=[sample.attributes["gold"] for sample in sorted_gold_samples],
        preds=[sample["prediction"] for sample in sorted_eval_samples],
        db_ids=[sample.attributes["db_id"] for sample in sorted_gold_samples],
        db_dir=db_dir,
        tables_json=tables_json
    )
    eval_results.update(ves_evaluator.evaluate(exec_acc_list=eval_results.get("execution_accuracy", None)))
    
    # Other user-defined metrics
    user_defined_metrics = [metric for metric in dataset.metrics if metric.name not in set(eval_results.keys())]
    all_samples_attrs = [sample.attributes for sample in sorted_gold_samples]
    for user_metric in user_defined_metrics:
        calc_fn = lambda samples_attrs, execution_accuracy, exact_match_accuracy, valid_efficiency_score: eval(user_metric.rule_definition)
        eval_results[user_metric.name] = calc_fn(samples_attrs=all_samples_attrs, **eval_results)
        
    # NOTE: Insert all eval results into database
    all_samples_metric_values = []
    metric_names = eval_results.keys()
    for idx in range(len(sorted_gold_samples)):
        metric_values = {}
        for name in metric_names:
            metric_values[name] = eval_results[name][idx]
        all_samples_metric_values.append(metric_values)
    
    user = await User.get(username=current_user.username)
    
    new_records = []
    for db_sample, eval_sample, metric_values in zip(sorted_gold_samples, sorted_eval_samples, all_samples_metric_values):
        new_records.append(Evaluation(
            dataset=dataset,
            sample=db_sample,
            prediction=eval_sample["prediction"],
            metric_values=metric_values,
            user=user,
            evaluation_identifier=evaluation_identifier
        ))
        
    async with in_transaction():
        evaluation_records = await Evaluation.bulk_create(new_records)
    
    return global_enums.SUCCESS_COMPLETE