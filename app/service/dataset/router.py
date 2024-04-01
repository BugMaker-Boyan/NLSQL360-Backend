from fastapi import APIRouter, UploadFile, status, HTTPException
from pydantic import BaseModel
from app.service.auth.auth_token import get_password_hash, UserObject, UserInDBObject, Depends, get_current_user
from typing import List
from app.model.models import Dataset, Sample, DatasetAttr, User, DatasetMetric
from tortoise.functions import Count
from tortoise.expressions import Q
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
from core.sql_parse.parser import Parser


dataset_router = APIRouter()


@dataset_router.get("/")
async def get_all_datasets_info(current_user: UserObject = Depends(get_current_user)):
    datasets = await Dataset.filter(user__username=current_user.username).prefetch_related(
        "metrics", "attrs"
    ).annotate(sample_count=Count("samples"))
    details = []
    for dataset in datasets:
        dataset_detail = {
            "name": dataset.name,
            "attrs": [attr.attr_name for attr in dataset.attrs],
            "count": dataset.sample_count,
            "metrics": [{"name": metric.name, "rule_definition": metric.rule_definition, "description": metric.description} for metric in dataset.metrics]
        }
        details.append(dataset_detail)
        
    return details


@dataset_router.get("/{dataset_name}")
async def get_dataset_info(dataset_name: str, current_user: UserObject = Depends(get_current_user)):
    try:
        dataset = await Dataset.get(name=dataset_name, user__username=current_user.username).prefetch_related(
            "metrics", "attrs"
        ).annotate(sample_count=Count("samples"))
        dataset_detail = {
            "name": dataset.name,
            "attrs": [attr.attr_name for attr in dataset.attrs],
            "count": dataset.sample_count,
            "metrics": [{"name": metric.name, "rule_definition": metric.rule_definition, "description": metric.description} for metric in dataset.metrics]
        }   
        return dataset_detail
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {e}"
        ) from e


async def save_and_extract_zip_file(zip_file_path: Path, content: bytes, extract_dir_name: str):
    extract_dir_path = zip_file_path.parent / extract_dir_name
    extract_dir_path.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(zip_file_path, 'wb') as file:
        await file.write(content)

    def extract_zip():
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir_path)

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, extract_zip)
    except Exception as e:
        print(f"Error extracting ZIP file: {e}")
        raise e


@dataset_router.post("/{dataset_name}")
async def create_dataset(dataset_name: str, 
                         samples_json_file: UploadFile,
                         db_zip_file: UploadFile,
                         tables_json_file: UploadFile = None,
                         current_user: UserObject = Depends(get_current_user)):
    # NOTE: To check dataset in db
    dataset = await Dataset.filter(user__username=current_user.username, name=dataset_name)
    if dataset:
        raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=f"Dataset {dataset_name} already exists"
            ) from cleanup_error
    
    base_path = Path(f"data/{current_user.username}/{dataset_name}")
    samples_file_path = base_path / samples_json_file.filename
    db_zip_file_path = base_path / db_zip_file.filename
    if tables_json_file:
        tables_file_path = base_path / tables_json_file.filename

    try:
        # Saving files to server
        base_path.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(samples_file_path, "wb") as buffer:
            content = await samples_json_file.read()
            await buffer.write(content)

        content = await db_zip_file.read()
        await save_and_extract_zip_file(db_zip_file_path, content, "databases")
        
        if tables_json_file:
            async with aiofiles.open(tables_file_path, "wb") as buffer:
                content = await tables_json_file.read()
                await buffer.write(content)
                
        # Insert into related tables
        async with aiofiles.open(samples_file_path, "r", encoding="utf-8") as fp:
            content = await fp.read()
            samples_json = json.loads(content)
            if not samples_json:
                raise HTTPException(
                        status_code=status.HTTP_406_NOT_ACCEPTABLE,
                        detail=f"Samples JSON is empty"
                    )
            
            dataset_attr_names = set(samples_json[0].keys())
            #NOTE: Add more basic keys checking here, for necessary keys.
            for default_attr_name in global_enums.DEFAULT_DATASET_ATTR_NAMES:
                if default_attr_name not in dataset_attr_names:
                    raise HTTPException(
                            status_code=status.HTTP_406_NOT_ACCEPTABLE,
                            detail=f"Dataset attrs must include {global_enums.DEFAULT_DATASET_ATTR_NAMES} at least"
                        )
            # NOTE: dataset_attr_names may include user-defined attrs,
            # we also need auto parse the sample sql, to get auto-parsed attrs
            for sample in samples_json:
                parser = Parser(sample["gold"])
                auto_parsed_attrs = {attr: getattr(parser, attr) for attr in dir(parser) if attr.startswith("count_")}
                sample.update(auto_parsed_attrs)
                dataset_attr_names.update(auto_parsed_attrs.keys())
                
            async with in_transaction():
                user = await User.get(username=current_user.username)
                
                dataset = await Dataset.create(
                    name=dataset_name,
                    user=user,
                    samples_json_filename=samples_json_file.filename,
                    db_dirname="databases",
                    tables_json_filename=tables_json_file.filename if tables_json_file else None
                )
                samples = await Sample.bulk_create(
                    [Sample(attributes=sample_item, dataset=dataset) for sample_item in samples_json]
                )
                dataset_attrs = await DatasetAttr.bulk_create(
                    [DatasetAttr(dataset=dataset, user=user, attr_name=attr_name) for attr_name in dataset_attr_names]
                )
                dataset_metrics = await DatasetMetric.bulk_create(
                    [DatasetMetric(
                        dataset=dataset,
                        user=user,
                        name=default_metric["name"],
                        description=default_metric["description"],
                        rule_definition=default_metric["rule_definition"]) for default_metric in global_enums.DEFAULT_METRICS]
                )
        
    except Exception as e:
        try:
            if samples_file_path.exists():
                samples_file_path.unlink() 
            if db_zip_file_path.exists():
                db_zip_file_path.unlink() 
            if tables_json_file and tables_file_path.exists():
                tables_file_path.unlink()
            if base_path.exists():
                shutil.rmtree(base_path)
        except Exception as cleanup_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to clean up after error: {cleanup_error}"
            ) from cleanup_error

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal OS error: {e}"
        ) from e
    
    return global_enums.SUCCESS_COMPLETE